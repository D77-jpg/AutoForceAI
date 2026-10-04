"use client";

import React, { useEffect, useMemo, useState } from "react";
import Link from "next/link";
import {
  AlertTriangle,
  ArrowLeft,
  CheckCircle2,
  Database,
  ExternalLink,
  FileDown,
  Loader2,
  Plus,
  ShieldCheck,
  Sparkles,
  Trash2,
} from "lucide-react";
import { PageHeader } from "@/components/PageHeader";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Modal } from "@/components/ui/modal";
import {
  confirmQuotation,
  downloadQuotationPdf,
  generateQuotationProposal,
  listSyncedLeads,
  type ProposalItem,
  type QuotationProposal,
  type QuotationResult,
  type SyncedLead,
  listLeadQuotations,
  getQuotation,
  type QuotationHistoryItem,
} from "@/lib/quotation-api";

const CURRENCIES = ["USD", "EUR", "GBP", "CNY", "JPY", "HKD", "AUD", "CAD", "CHF", "SGD", "AED", "NZD"];
const QUOTATION_STATUS = { draft: '草稿', sent: '已发送', negotiating: '协商中', accepted: '已接受', rejected: '已拒绝', expired: '已过期' };

const fieldClass = "w-full rounded-md border border-transparent bg-surface-2 px-3.5 py-2 text-base text-text placeholder:text-text-tertiary focus-visible:outline-none focus-visible:ring-[3px] focus-visible:ring-accent/30 focus-visible:border-accent/50 sm:text-[15px]";
const linkButtonClass = "inline-flex h-11 items-center justify-center rounded-md border border-separator bg-transparent px-4 text-sm font-medium text-text transition-all duration-fast ease-apple hover:bg-text/5 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent/40 active:scale-[0.96]";

function liveMissing(proposal: QuotationProposal | null): string[] {
  if (!proposal) return [];
  const missing: string[] = [];
  if (!proposal.title.trim()) missing.push("报价标题");
  if (!proposal.items.length) missing.push("产品明细");
  proposal.items.forEach((item, index) => {
    if (!item.productName.trim()) missing.push(`第 ${index + 1} 行产品名称`);
    if (item.quantity === null || item.quantity <= 0) missing.push(`第 ${index + 1} 行数量`);
    if (item.unitPrice === null || item.unitPrice < 0) missing.push(`第 ${index + 1} 行单价`);
  });
  if (!proposal.sources.length) missing.push("来源依据");
  return missing;
}

export default function NewQuotationPage() {
  const [leads, setLeads] = useState<SyncedLead[]>([]);
  const [leadId, setLeadId] = useState("");
  const [currency, setCurrency] = useState("USD");
  const [instructions, setInstructions] = useState("");
  const [proposal, setProposal] = useState<QuotationProposal | null>(null);
  const [result, setResult] = useState<QuotationResult | null>(null);
  const [loadingLeads, setLoadingLeads] = useState(true);
  const [generating, setGenerating] = useState(false);
  const [confirming, setConfirming] = useState(false);
  const [downloading, setDownloading] = useState(false);
  const [confirmOpen, setConfirmOpen] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [history, setHistory] = useState<QuotationHistoryItem[]>([]);
  const [historyLoading, setHistoryLoading] = useState(false);
  const [restoring, setRestoring] = useState(false);

  const openQuotation = async (id: string) => {
    setRestoring(true); setError(null);
    try {
      setResult(await getQuotation(id));
      const url = new URL(window.location.href); url.searchParams.set('quotation', id);
      window.history.replaceState(null, '', url.toString());
    } catch (err) { setError(err instanceof Error ? err.message : '读取报价失败'); }
    finally { setRestoring(false); }
  };

  useEffect(() => {
    const savedId = new URL(window.location.href).searchParams.get('quotation');
    if (savedId) void openQuotation(savedId);
    listSyncedLeads()
      .then((items) => {
        setLeads(items);
        if (items.length === 1) setLeadId(String(items[0].id));
      })
      .catch((err) => setError(err instanceof Error ? err.message : "加载线索失败"))
      .finally(() => setLoadingLeads(false));
  }, []);

  useEffect(() => {
    let active = true;
    setHistory([]);
    if (!leadId) { setHistoryLoading(false); return; }
    setHistoryLoading(true);
    listLeadQuotations(Number(leadId)).then(items => { if (active) setHistory(items); })
      .catch(err => { if (active) setError(err instanceof Error ? err.message : '读取报价历史失败'); })
      .finally(() => { if (active) setHistoryLoading(false); });
    return () => { active = false; };
  }, [leadId]);

  const selectedLead = leads.find((lead) => String(lead.id) === leadId);
  const missing = useMemo(() => liveMissing(proposal), [proposal]);
  const canConfirm = Boolean(proposal && missing.length === 0 && !confirming);

  const generate = async () => {
    if (!leadId) {
      setError("请先选择一个已经同步到 Genesis 的客户");
      return;
    }
    setGenerating(true);
    setProposal(null);
    setError(null);
    setResult(null);
    try {
      setProposal(await generateQuotationProposal({
        leadId: Number(leadId),
        currency,
        ...(instructions.trim() ? { instructions: instructions.trim() } : {}),
      }));
    } catch (err) {
      setError(err instanceof Error ? err.message : "生成报价建议失败");
    } finally {
      setGenerating(false);
    }
  };

  const patchProposal = (patch: Partial<QuotationProposal>) => {
    setProposal((current) => current ? { ...current, ...patch } : current);
  };

  const patchItem = (index: number, patch: Partial<ProposalItem>) => {
    if (!proposal) return;
    const items = proposal.items.map((item, itemIndex) => itemIndex === index ? { ...item, ...patch } : item);
    patchProposal({ items });
  };

  const addItem = () => {
    if (!proposal) return;
    patchProposal({ items: [...proposal.items, { productName: "", model: "", quantity: null, unitPrice: null }] });
  };

  const removeItem = (index: number) => {
    if (!proposal || proposal.items.length === 1) return;
    patchProposal({ items: proposal.items.filter((_, itemIndex) => itemIndex !== index) });
  };

  const confirm = async () => {
    if (!proposal || !canConfirm) return;
    setConfirming(true);
    setError(null);
    try {
      const created = await confirmQuotation(proposal);
      setResult(created);
      const url = new URL(window.location.href); url.searchParams.set('quotation', created.quotation.quotationId);
      window.history.replaceState(null, '', url.toString());
      setConfirmOpen(false);
    } catch (err) {
      setError(err instanceof Error ? err.message : "创建 Genesis 报价草稿失败");
      setConfirmOpen(false);
    } finally {
      setConfirming(false);
    }
  };

  const download = async () => {
    if (!result) return;
    setDownloading(true);
    setError(null);
    try {
      await downloadQuotationPdf(result.pdfUrl, result.quotation.quotationNo);
    } catch (err) {
      setError(err instanceof Error ? err.message : "下载 PDF 失败");
    } finally {
      setDownloading(false);
    }
  };

  if (result) {
    return (
      <main className="min-h-dvh bg-bg p-5 text-text md:p-8">
        <PageHeader title="Genesis 报价" description="编号、金额、状态与 PDF 均读取自 Genesis CRM。" />
        <Card className="mx-auto max-w-3xl overflow-hidden">
          <div className="border-b border-separator bg-success/10 p-6 md:p-8">
            <div className="flex items-start gap-4">
              <div className="flex h-12 w-12 shrink-0 items-center justify-center rounded-full bg-success/15 text-success">
                <CheckCircle2 size={26} />
              </div>
              <div>
                  <Badge variant="outline" className="mb-3 border-success/30 text-success">{result.quotation.status.toUpperCase()} · v{result.quotation.version}</Badge>
                <h2 className="text-2xl font-semibold tracking-tight">{result.quotation.quotationNo}</h2>
                <p className="mt-1 text-sm text-text-secondary">{result.quotation.title}</p>
              </div>
            </div>
          </div>
          <CardContent className="space-y-6 p-6 md:p-8">
            <div className="grid gap-4 sm:grid-cols-3">
              <div className="rounded-xl bg-surface-2 p-4">
                <p className="text-xs text-text-secondary">权威总额</p>
                <p className="mt-1 text-xl font-semibold tabular-nums">{result.quotation.currency} {result.quotation.totalAmount.toFixed(2)}</p>
              </div>
              <div className="rounded-xl bg-surface-2 p-4">
                <p className="text-xs text-text-secondary">状态</p>
                <p className="mt-1 text-xl font-semibold">{QUOTATION_STATUS[result.quotation.status] || result.quotation.status}</p>
              </div>
              <div className="rounded-xl bg-surface-2 p-4">
                <p className="text-xs text-text-secondary">版本</p>
                <p className="mt-1 text-xl font-semibold">v{result.quotation.version}</p>
              </div>
            </div>
            <Alert>
              <ShieldCheck size={17} />
              <AlertTitle>报价已保存到 CRM</AlertTitle>
              <AlertDescription>金额按已确认的数量和单价计算。{result.quotation.status === 'draft' ? '这份草稿尚未发送给客户，可在 Genesis 中继续编辑与审核。' : '当前状态来自 Genesis 的最新记录。'}</AlertDescription>
            </Alert>
            {result.quotation.items?.length > 0 && <div className="overflow-x-auto"><table className="w-full text-left text-sm"><thead><tr className="border-b border-separator"><th className="py-2">产品</th><th className="py-2 text-right">数量</th><th className="py-2 text-right">单价</th><th className="py-2 text-right">金额</th></tr></thead><tbody>{result.quotation.items.map((item, index) => <tr key={index} className="border-b border-separator"><td className="py-3">{item.productName}</td><td className="text-right">{item.quantity}</td><td className="text-right">{item.unitPrice.toFixed(2)}</td><td className="text-right">{item.amount.toFixed(2)}</td></tr>)}</tbody></table></div>}
            <dl className="grid gap-3 text-sm sm:grid-cols-2"><div><dt className="text-text-secondary">最低起订量</dt><dd>{result.quotation.moq || '未填写'}</dd></div><div><dt className="text-text-secondary">交期</dt><dd>{result.quotation.leadTime || '未填写'}</dd></div></dl>
            {error && <Alert variant="destructive"><AlertTriangle size={17} /><AlertDescription>{error}</AlertDescription></Alert>}
            <div className="flex flex-col gap-3 sm:flex-row">
              <Button onClick={download} disabled={downloading} className="min-h-11 flex-1">
                {downloading ? <Loader2 size={17} className="mr-2 animate-spin" /> : <FileDown size={17} className="mr-2" />}
                下载 Genesis PDF
              </Button>
              {result.genesisUrl && (
                <a href={result.genesisUrl} target="_blank" rel="noreferrer" className={`${linkButtonClass} flex-1`}>
                  <ExternalLink size={17} className="mr-2" />在 Genesis 中继续
                </a>
              )}
              <Button variant="ghost" className="min-h-11" onClick={() => { setResult(null); setProposal(null); const url = new URL(window.location.href); url.searchParams.delete('quotation'); window.history.replaceState(null, '', url.toString()); if (leadId) void listLeadQuotations(Number(leadId)).then(setHistory).catch(err => setError(err.message)); }}>
                再建一份
              </Button>
            </div>
          </CardContent>
        </Card>
      </main>
    );
  }

  return (
    <main className="min-h-dvh bg-bg p-5 text-text md:p-8">
      <PageHeader
        title="AI 报价建议"
        description="AI 只准备可编辑建议；你明确确认后，Genesis 才会创建正式草稿。"
        actions={<Link href="/crm" className={linkButtonClass}><ArrowLeft size={16} className="mr-2" />返回 CRM</Link>}
      />

      {error && <Alert variant="destructive" className="mb-5"><AlertTriangle size={17} /><AlertTitle>操作未完成</AlertTitle><AlertDescription>{error}</AlertDescription></Alert>}
      {restoring && <p role="status" className="mb-4">正在读取 Genesis 报价…</p>}

      <div className="grid gap-6 xl:grid-cols-[minmax(0,1fr)_340px]">
        <div className="space-y-6">
          <Card>
            <CardHeader>
              <div className="flex items-start gap-3">
                <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-accent/10 text-accent"><Sparkles size={19} /></div>
                <div>
                  <CardTitle>1. 选择客户并生成建议</CardTitle>
                  <CardDescription>仅显示已经同步到当前 Genesis 项目的线索。</CardDescription>
                </div>
              </div>
            </CardHeader>
            <CardContent className="grid gap-4 md:grid-cols-[minmax(0,1fr)_140px]">
              <div className="space-y-2">
                <Label htmlFor="lead">已同步客户</Label>
                <select id="lead" className={`${fieldClass} min-h-11 cursor-pointer`} value={leadId} onChange={(event) => { setLeadId(event.target.value); setProposal(null); }} disabled={loadingLeads || generating || confirming || restoring}>
                  <option value="">{loadingLeads ? "正在加载…" : "请选择客户"}</option>
                  {leads.map((lead) => <option key={lead.id} value={lead.id}>{lead.company || lead.name || `线索 #${lead.id}`} · {lead.products || "未填写产品"}</option>)}
                </select>
                {!loadingLeads && leads.length === 0 && <p className="text-sm text-warning">暂无已同步客户，请先在线索池完成 CRM 交接。</p>}
                {historyLoading && <p role="status" className="text-sm text-text-secondary">读取报价历史…</p>}
                {!historyLoading && history.length > 0 && <div className="space-y-2"><p className="text-sm text-text-secondary">已创建的报价</p>{history.map(item => <Button key={item.quotationId} variant="outline" disabled={restoring} onClick={() => void openQuotation(item.quotationId)}>{item.quotationNo || item.quotationId} · {item.currency} {item.totalAmount?.toFixed(2)} · {item.status}</Button>)}</div>}
              </div>
              <div className="space-y-2">
                <Label htmlFor="currency">报价币种</Label>
                <select id="currency" className={`${fieldClass} min-h-11 cursor-pointer`} value={currency} disabled={generating || confirming || restoring} onChange={(event) => { setCurrency(event.target.value); setProposal(null); }}>
                  {CURRENCIES.map((code) => <option key={code}>{code}</option>)}
                </select>
              </div>
              <div className="space-y-2 md:col-span-2">
                <Label htmlFor="instructions">补充要求（可选）</Label>
                <textarea id="instructions" className={`${fieldClass} min-h-24 resize-y`} maxLength={1000} disabled={generating || confirming || restoring} value={instructions} onChange={(event) => { setInstructions(event.target.value); setProposal(null); }} placeholder="例如：优先使用知识库中的 FOB 厦门条款；不要估算认证费用。" />
              </div>
              <div className="md:col-span-2 flex justify-end">
                <Button onClick={generate} disabled={!leadId || generating || leads.length === 0} className="min-h-11 min-w-36">
                  {generating ? <Loader2 size={17} className="mr-2 animate-spin" /> : <Sparkles size={17} className="mr-2" />}
                  {generating ? "正在生成" : proposal ? "重新生成" : "生成报价建议"}
                </Button>
              </div>
            </CardContent>
          </Card>

          {proposal && (
            <Card>
              <CardHeader>
                <CardTitle>2. 编辑并核对报价</CardTitle>
                <CardDescription>所有数量、单价和条款都必须由你看到并确认；空缺字段会阻止提交。</CardDescription>
              </CardHeader>
              <CardContent className="space-y-6">
                <div className="space-y-2">
                  <Label htmlFor="title">报价标题</Label>
                  <Input id="title" value={proposal.title} onChange={(event) => patchProposal({ title: event.target.value })} />
                </div>

                <div className="space-y-3">
                  <div className="flex items-center justify-between">
                    <Label>产品明细</Label>
                    <Button size="sm" variant="outline" className="min-h-11" onClick={addItem}><Plus size={14} className="mr-1" />添加产品</Button>
                  </div>
                  {proposal.items.map((item, index) => (
                    <div key={index} className="grid gap-3 rounded-xl border border-separator bg-surface-2/50 p-4 md:grid-cols-[minmax(180px,1.4fr)_minmax(130px,.8fr)_120px_140px_40px]">
                      <div className="space-y-2"><Label htmlFor={`product-${index}`}>产品名称</Label><Input id={`product-${index}`} value={item.productName} onChange={(event) => patchItem(index, { productName: event.target.value })} /></div>
                      <div className="space-y-2"><Label htmlFor={`model-${index}`}>型号</Label><Input id={`model-${index}`} value={item.model || ""} onChange={(event) => patchItem(index, { model: event.target.value })} /></div>
                      <div className="space-y-2"><Label htmlFor={`quantity-${index}`}>数量</Label><Input id={`quantity-${index}`} type="number" min="0.000001" step="any" value={item.quantity ?? ""} onChange={(event) => patchItem(index, { quantity: event.target.value === "" ? null : Number(event.target.value) })} /></div>
                      <div className="space-y-2"><Label htmlFor={`price-${index}`}>单价（{proposal.currency}）</Label><Input id={`price-${index}`} type="number" min="0" step="any" value={item.unitPrice ?? ""} onChange={(event) => patchItem(index, { unitPrice: event.target.value === "" ? null : Number(event.target.value) })} /></div>
                      <div className="flex items-end"><Button type="button" variant="ghost" size="icon" className="min-h-11 min-w-11" aria-label={`删除第 ${index + 1} 行`} disabled={proposal.items.length === 1} onClick={() => removeItem(index)}><Trash2 size={16} /></Button></div>
                    </div>
                  ))}
                </div>

                <div className="grid gap-4 md:grid-cols-2">
                  <div className="space-y-2"><Label htmlFor="validity">有效期</Label><Input id="validity" type="date" value={proposal.validityDate?.slice(0, 10) || ""} onChange={(event) => patchProposal({ validityDate: event.target.value ? `${event.target.value}T00:00:00.000Z` : null })} /></div>
                  <div className="space-y-2"><Label htmlFor="moq">MOQ</Label><Input id="moq" value={proposal.moq || ""} onChange={(event) => patchProposal({ moq: event.target.value })} /></div>
                  <div className="space-y-2"><Label htmlFor="payment">付款方式</Label><Input id="payment" value={proposal.paymentTerms || ""} onChange={(event) => patchProposal({ paymentTerms: event.target.value })} /></div>
                  <div className="space-y-2"><Label htmlFor="lead-time">交期</Label><Input id="lead-time" value={proposal.leadTime || ""} onChange={(event) => patchProposal({ leadTime: event.target.value })} /></div>
                  <div className="space-y-2 md:col-span-2"><Label htmlFor="notes">备注</Label><textarea id="notes" className={`${fieldClass} min-h-24 resize-y`} maxLength={5000} value={proposal.notes || ""} onChange={(event) => patchProposal({ notes: event.target.value })} /></div>
                </div>

                <div className="flex flex-col items-start justify-between gap-4 border-t border-separator pt-5 sm:flex-row sm:items-center">
                  <div>
                    <p className="text-sm font-medium">预计小计（仅供核对）</p>
                    <p className="text-2xl font-semibold tabular-nums">{proposal.currency} {proposal.items.reduce((sum, item) => sum + ((item.quantity || 0) * (item.unitPrice || 0)), 0).toFixed(2)}</p>
                    <p className="text-xs text-text-secondary">最终金额由 Genesis 重新计算。</p>
                  </div>
                  <Button className="min-h-11 min-w-44" disabled={!canConfirm} onClick={() => setConfirmOpen(true)}><ShieldCheck size={17} className="mr-2" />创建 Genesis 草稿</Button>
                </div>
              </CardContent>
            </Card>
          )}
        </div>

        <aside className="space-y-5 xl:sticky xl:top-6 xl:self-start">
          <Card>
            <CardHeader><CardTitle className="text-base">提交检查</CardTitle><CardDescription>满足全部门槛后才能创建正式草稿。</CardDescription></CardHeader>
            <CardContent className="space-y-3">
              {proposal ? (
                <>
                  <div className="flex items-center gap-2 text-sm"><CheckCircle2 size={16} className="text-success" />客户已同步至 Genesis</div>
                  <div className="flex items-center gap-2 text-sm"><CheckCircle2 size={16} className="text-success" />来源依据 {proposal.sources.length} 条</div>
                  <div className="flex items-center gap-2 text-sm">{missing.length ? <AlertTriangle size={16} className="text-warning" /> : <CheckCircle2 size={16} className="text-success" />}{missing.length ? `仍缺 ${missing.length} 项` : "必填字段完整"}</div>
                  {missing.length > 0 && <ul className="list-disc space-y-1 pl-5 text-xs text-warning">{missing.map((item) => <li key={item}>{item}</li>)}</ul>}
                </>
              ) : <p className="text-sm text-text-secondary">生成建议后，这里会显示确认门槛。</p>}
            </CardContent>
          </Card>

          {proposal && (
            <>
              <Card>
                <CardHeader><CardTitle className="text-base">风险提示</CardTitle></CardHeader>
                <CardContent className="space-y-2">{proposal.warnings.map((warning, index) => <div key={`${warning}-${index}`} className="flex gap-2 text-sm text-text-secondary"><AlertTriangle size={15} className="mt-0.5 shrink-0 text-warning" /><span>{warning}</span></div>)}</CardContent>
              </Card>
              <Card>
                <CardHeader><CardTitle className="text-base">来源依据</CardTitle><CardDescription>只保存引用标识，不复制知识库正文。</CardDescription></CardHeader>
                <CardContent className="space-y-3">{proposal.sources.map((source) => <div key={`${source.kind}-${source.referenceId}`} className="rounded-lg bg-surface-2 p-3"><div className="flex items-center gap-2"><Database size={14} className="text-accent" /><Badge variant="secondary">{source.kind === "lead" ? "线索" : "知识库"}</Badge></div><p className="mt-2 text-sm">{source.title || source.referenceId}</p><p className="mt-1 break-all text-xs text-text-tertiary">{source.referenceId}</p></div>)}</CardContent>
              </Card>
            </>
          )}

          {!proposal && selectedLead && <Card><CardContent className="p-5"><p className="text-xs text-text-secondary">当前客户</p><p className="mt-1 font-medium">{selectedLead.company || selectedLead.name}</p><p className="mt-1 text-sm text-text-secondary">{selectedLead.products || "未填写产品需求"}</p></CardContent></Card>}
        </aside>
      </div>

      <Modal
        open={confirmOpen}
        onClose={() => !confirming && setConfirmOpen(false)}
        title="确认创建报价草稿？"
        description="此操作会在 Genesis CRM 写入一份正式 draft；不会自动发送给客户。"
        footer={<><Button variant="ghost" disabled={confirming} onClick={() => setConfirmOpen(false)}>继续检查</Button><Button disabled={confirming} onClick={confirm}>{confirming && <Loader2 size={16} className="mr-2 animate-spin" />}确认创建</Button></>}
      >
        <div className="space-y-3 rounded-xl bg-surface-2 p-4 text-sm">
          <p><span className="text-text-secondary">客户：</span>{proposal?.company || proposal?.customerName}</p>
          <p><span className="text-text-secondary">产品行：</span>{proposal?.items.length}</p>
          <p><span className="text-text-secondary">本地预估：</span>{proposal ? `${proposal.currency} ${proposal.items.reduce((sum, item) => sum + ((item.quantity || 0) * (item.unitPrice || 0)), 0).toFixed(2)}` : "—"}</p>
        </div>
      </Modal>
    </main>
  );
}
