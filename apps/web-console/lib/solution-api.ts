const API = (process.env.NEXT_PUBLIC_API_URL || '').replace(/\/$/, '');
export type ContextItem = { doc_id: string | number; doc_name: string; content: string; score: number };
export type Settings = { topic: string; target_audience: string; style: string; kb_ids: number[] };
export type Generation = { generation_mode: 'llm' | 'fallback'; fallback_reason: string | null; knowledge_used: boolean };
export type ContextResult = { topic: string; items: ContextItem[]; logs: { step: string; details: unknown; timestamp: string }[] };
export type OutlinePage = { page: number; title: string; type: string; key_points_hint: string | null };
export type OutlineResult = Generation & { topic: string; pages: OutlinePage[]; sources?: ContextItem[] };
export type PageContent = Generation & { page?: number; title: string; type: string; bullets: string[]; image_suggestion: string | null; speaker_notes: string | null; data_source: string | null; sources: ContextItem[] };
export type DraftPage = { id: string; outline: OutlinePage; content?: PageContent; error?: string };
export type RequestOptions = { signal?: AbortSignal; timeoutMs?: number };

export class SolutionApiError extends Error {
  constructor(message: string, public status?: number) { super(message); this.name = 'SolutionApiError'; }
}
async function request<T>(path: string, body: unknown, options: RequestOptions = {}, binary = false): Promise<T> {
  const token = typeof localStorage !== 'undefined' ? localStorage.getItem('token') : null;
  if (!token) throw new SolutionApiError('未登录，请先登录后重试。', 401);
  const controller = new AbortController();
  let timedOut = false;
  const cancel = () => controller.abort();
  if (options.signal?.aborted) throw new SolutionApiError('请求已取消');
  options.signal?.addEventListener('abort', cancel, { once: true });
  const timer = setTimeout(() => { timedOut = true; controller.abort(); }, options.timeoutMs ?? 120000);
  try {
    const response = await fetch(`${API}/api/v1/${path}`, {
      method: body === undefined ? 'GET' : 'POST',
      headers: { Authorization: `Bearer ${token}`, ...(body === undefined ? {} : { 'Content-Type': 'application/json' }) },
      body: body === undefined ? undefined : JSON.stringify(body), signal: controller.signal,
    });
    if (!response.ok) {
      let detail = '';
      try {
        const payload = await response.json();
        detail = typeof payload.detail === 'string' ? payload.detail : Array.isArray(payload.detail) ? payload.detail.map((item: { msg?: string }) => item.msg).filter(Boolean).join('；') : payload.message || '';
      } catch { /* An HTML or empty error response still exposes its HTTP status. */ }
      throw new SolutionApiError(response.status === 401 ? '登录已过期，请重新登录。' : `请求失败（HTTP ${response.status}）${detail ? `：${detail}` : ''}`, response.status);
    }
    return (binary ? await response.blob() : await response.json()) as T;
  } catch (error) {
    if (timedOut) throw new SolutionApiError('请求超时，请重试。');
    if (controller.signal.aborted) throw new SolutionApiError('请求已取消');
    if (error instanceof SolutionApiError) throw error;
    throw new SolutionApiError('网络连接或响应异常，请检查连接后重试。');
  } finally {
    clearTimeout(timer);
    options.signal?.removeEventListener('abort', cancel);
  }
}
function required(value: string, label: string) {
  if (!value?.trim()) throw new SolutionApiError(`${label}不能为空`);
  return value.trim();
}
export function settingsPayload(settings: Settings): Settings {
  return { topic: required(settings.topic, '主题'), target_audience: settings.target_audience, style: settings.style, kb_ids: [...settings.kb_ids] };
}
export async function listKnowledgeBases(options?: RequestOptions): Promise<{ items: { id: number; name: string }[] }> {
  return request('solution/knowledge-bases', undefined, options);
}
export async function retrieveContext(settings: Settings, options?: RequestOptions): Promise<ContextResult> {
  return request('solution/context', settingsPayload(settings), options);
}
export async function generateOutline(settings: Settings, options?: RequestOptions): Promise<OutlineResult> {
  // Deliberately whitelist fields: context_override must never cross this boundary.
  return request('solution/outline', settingsPayload(settings), options);
}
export async function generatePageContent(settings: Settings, page: OutlinePage, options?: RequestOptions): Promise<PageContent> {
  return request('solution/page/content', { ...settingsPayload(settings), page_title: required(page.title, '页面标题'), page_type: page.type, context_hint: page.key_points_hint || '' }, options);
}
export async function generatePpt(topic: string, pages: PageContent[], options?: RequestOptions): Promise<Blob> {
  const title = required(topic, '主题');
  if (!pages.length) throw new SolutionApiError('请先生成页面内容');
  pages.forEach(page => {
    required(page.title, '页面标题');
    if (page.generation_mode === 'fallback' && !page.bullets?.some(bullet => bullet.trim()))
      throw new SolutionApiError('模板回退页需要人工填写内容要点才能导出');
  });
  return request('solution/generate', { topic: title, pages }, options, true);
}
export function renumberPages(pages: DraftPage[]): DraftPage[] {
  return pages.map((page, index) => ({ ...page, outline: { ...page.outline, page: index + 1 } }));
}
export function movePage(pages: DraftPage[], index: number, direction: -1 | 1): DraftPage[] {
  const target = index + direction;
  if (index < 0 || index >= pages.length || target < 0 || target >= pages.length) return pages;
  const next = [...pages];
  [next[index], next[target]] = [next[target], next[index]];
  return renumberPages(next);
}
export function editOutline(page: DraftPage, patch: Partial<OutlinePage>): DraftPage {
  return { ...page, outline: { ...page.outline, ...patch }, content: undefined, error: undefined };
}
