import { expireAuthSession } from './auth-session';
// Empty means same-origin HTTPS ingress; never call the visitor's localhost in production.
const API = process.env.NEXT_PUBLIC_API_URL || "";

export type ProposalSource = {
  kind: "lead" | "knowledge" | "customer" | "quotation";
  referenceId: string;
  title?: string | null;
};

export type ProposalItem = {
  productName: string;
  model?: string | null;
  quantity: number | null;
  unitPrice: number | null;
};

export type QuotationProposal = {
  proposalId: string;
  leadId: number;
  externalRef: string;
  customerName?: string | null;
  company?: string | null;
  title: string;
  currency: string;
  items: ProposalItem[];
  validityDate?: string | null;
  paymentTerms?: string | null;
  leadTime?: string | null;
  moq?: string | null;
  notes?: string | null;
  missingFields: string[];
  warnings: string[];
  sources: ProposalSource[];
  model: string;
  generatedAt: string;
};

export type SyncedLead = {
  id: number;
  name?: string | null;
  company?: string | null;
  email?: string | null;
  products?: string | null;
  crm?: {
    synced?: boolean;
    remote_customer_id?: string | null;
    remote_status?: string | null;
  } | null;
};

export type QuotationResult = {
  quotation: {
    quotationId: string;
    quotationNo: string;
    customerId: string;
    title: string;
    currency: string;
    totalAmount: number;
    status: string;
    version: number;
    items?: { productName: string; quantity: number; unitPrice: number; amount: number }[];
    leadTime?: string | null;
    moq?: string | null;
    paymentTerms?: string | null;
    notes?: string | null;
  };
  pdfUrl: string;
  genesisUrl?: string | null;
};

function tokenHeaders(json = true): HeadersInit {
  const headers: Record<string, string> = {
    Authorization: `Bearer ${localStorage.getItem("token") || ""}`,
  };
  if (json) headers["Content-Type"] = "application/json";
  return headers;
}

async function errorMessage(response: Response): Promise<string> {
  try {
    const payload = await response.json();
    if (typeof payload?.detail === "string") return payload.detail;
    if (Array.isArray(payload?.detail)) {
      return payload.detail.map((item: { msg?: string }) => item?.msg).filter(Boolean).join("；") || `请求失败（HTTP ${response.status}）`;
    }
    if (payload?.detail?.message) return payload.detail.message;
    return payload?.message || `请求失败（HTTP ${response.status}）`;
  } catch {
    return `请求失败（HTTP ${response.status}）`;
  }
}

async function checkedFetch(path: string, options: RequestInit = {}): Promise<Response> {
  const token = localStorage.getItem('token');
  const response = await fetch(`${API}${path}`, { ...options, headers: { ...tokenHeaders(), ...options.headers } });
  if (!response.ok) {
    if (response.status === 401) expireAuthSession(token);
    throw new Error(await errorMessage(response));
  }
  return response;
}

export type QuotationHistoryItem = { quotationId: string; quotationNo?: string; status: string; totalAmount?: number; currency?: string };

export async function listLeadQuotations(leadId: number): Promise<QuotationHistoryItem[]> {
  const response = await checkedFetch(`/api/v1/crm/quotations/leads/${leadId}`);
  return (await response.json()).items;
}

export async function getQuotation(quotationId: string): Promise<QuotationResult> {
  return (await checkedFetch(`/api/v1/crm/quotations/${encodeURIComponent(quotationId)}`)).json();
}

export async function listSyncedLeads(): Promise<SyncedLead[]> {
  const response = await checkedFetch('/api/v1/leads');
  const payload = await response.json();
  return (payload.items || []).filter((lead: SyncedLead) => lead.crm?.synced);
}

export async function generateQuotationProposal(input: {
  leadId: number;
  currency: string;
  instructions?: string;
}): Promise<QuotationProposal> {
  const response = await checkedFetch('/api/v1/crm/quotations/proposals', {
    method: "POST",
    headers: tokenHeaders(),
    body: JSON.stringify(input),
  });
  return response.json();
}

export async function confirmQuotation(proposal: QuotationProposal): Promise<QuotationResult> {
  const response = await checkedFetch('/api/v1/crm/quotations/confirm', {
    method: "POST",
    headers: tokenHeaders(),
    body: JSON.stringify({
      leadId: proposal.leadId,
      proposalId: proposal.proposalId,
      model: proposal.model,
      sources: proposal.sources,
      confirmed: true,
      quotation: {
        title: proposal.title,
        currency: proposal.currency,
        items: proposal.items.map((item) => ({
          productName: item.productName,
          ...(item.model ? { model: item.model } : {}),
          quantity: item.quantity,
          unitPrice: item.unitPrice,
        })),
        ...(proposal.validityDate ? { validityDate: proposal.validityDate } : {}),
        ...(proposal.paymentTerms ? { paymentTerms: proposal.paymentTerms } : {}),
        ...(proposal.leadTime ? { leadTime: proposal.leadTime } : {}),
        ...(proposal.moq ? { moq: proposal.moq } : {}),
        ...(proposal.notes ? { notes: proposal.notes } : {}),
      },
    }),
  });
  return response.json();
}

export async function downloadQuotationPdf(pdfUrl: string, quotationNo: string): Promise<void> {
  const response = await checkedFetch(pdfUrl);
  if (!response.headers.get('content-type')?.includes('application/pdf')) throw new Error('服务未返回有效 PDF');
  const blob = await response.blob();
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = `${quotationNo || "Quotation"}.pdf`;
  document.body.appendChild(anchor);
  anchor.click();
  anchor.remove();
  setTimeout(() => URL.revokeObjectURL(url), 60000);
}
