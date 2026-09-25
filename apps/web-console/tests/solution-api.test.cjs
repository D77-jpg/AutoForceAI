const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const ts = require('typescript');
const Module = require('node:module');
const filename = path.resolve(__dirname, '../lib/solution-api.ts');
const mod = new Module(filename, module);
mod.filename = filename;
mod.paths = module.paths;
mod._compile(ts.transpileModule(fs.readFileSync(filename, 'utf8'), { compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2020 } }).outputText, filename);
const api = mod.exports;
const settings = { topic: '  方案  ', target_audience: '客户', style: '商务', kb_ids: [7] };
let token = 'secret';
global.localStorage = { getItem: () => token };

test('all endpoints use bearer auth, exact payload and binary download', async () => {
  const calls = [];
  global.fetch = async (url, init) => {
    calls.push({ url, ...init });
    return url.endsWith('/generate') ? new Response(new Blob(['pptx']), { headers: { 'Content-Type': 'application/vnd.openxmlformats-officedocument.presentationml.presentation' } }) : Response.json({ items: [] });
  };
  await api.listKnowledgeBases();
  await api.retrieveContext(settings);
  await api.generateOutline({ ...settings, context_override: 'must not leak' });
  await api.generatePageContent(settings, { page: 1, title: '标题', type: 'content', key_points_hint: '提示' });
  const content = { title: '标题', type: 'content', bullets: ['事实'], sources: [] };
  const blob = await api.generatePpt('方案', [content]);
  assert.equal(await blob.text(), 'pptx');
  assert.equal(calls[0].method, 'GET');
  assert.ok(calls[0].url.endsWith('/api/v1/solution/knowledge-bases'));
  for (const call of calls) assert.equal(call.headers.Authorization, 'Bearer secret');
  assert.deepEqual(JSON.parse(calls[2].body), { ...settings, topic: '方案' });
  assert.deepEqual(JSON.parse(calls[3].body), { ...settings, topic: '方案', page_title: '标题', page_type: 'content', context_hint: '提示' });
  assert.deepEqual(JSON.parse(calls[4].body), { topic: '方案', pages: [content] });
});

test('missing login and blank titles never issue a request', async () => {
  let calls = 0;
  global.fetch = async () => { calls++; return Response.json({}); };
  token = '';
  await assert.rejects(api.listKnowledgeBases(), /未登录/);
  token = 'secret';
  await assert.rejects(api.generateOutline({ ...settings, topic: '  ' }), /主题/);
  await assert.rejects(api.generatePageContent(settings, { title: ' ', type: 'content' }), /标题/);
  await assert.rejects(api.generatePpt('方案', [{ title: ' ' }]), /标题/);
  assert.equal(calls, 0);
});

test('HTTP 401, 403, validation and binary errors remain actionable', async () => {
  for (const [status, detail, expected] of [[401, 'expired', /登录/], [403, '知识库无权限', /403.*知识库无权限/], [422, [{ msg: '非法 ID' }], /422.*非法 ID/], [500, '导出失败', /500.*导出失败/]]) {
    global.fetch = async () => Response.json({ detail }, { status });
    await assert.rejects(api.generatePpt('方案', [{ title: '有效标题' }]), expected);
  }
});

test('network failure, timeout and cancellation are explicit', async () => {
  global.fetch = async () => { throw new TypeError('offline'); };
  await assert.rejects(api.listKnowledgeBases(), /网络/);
  global.fetch = async (_, init) => new Promise((resolve, reject) => init.signal.addEventListener('abort', () => reject(new DOMException('aborted', 'AbortError'))));
  await assert.rejects(api.listKnowledgeBases({ timeoutMs: 5 }), /超时/);
  const controller = new AbortController();
  const pending = api.listKnowledgeBases({ signal: controller.signal });
  controller.abort();
  await assert.rejects(pending, /取消/);
});

test('reorder preserves content identity, renumbers pages, and edits invalidate content', () => {
  const a = { id: 'a', outline: { page: 1, title: 'A' }, content: { title: 'A' } };
  const b = { id: 'b', outline: { page: 2, title: 'B' }, content: { title: 'B' } };
  const moved = api.movePage([a, b], 1, -1);
  assert.deepEqual(moved.map(p => p.id), ['b', 'a']);
  assert.deepEqual(moved.map(p => p.outline.page), [1, 2]);
  assert.equal(moved[0].content, b.content);
  assert.equal(a.outline.page, 1);
  assert.equal(api.editOutline(a, { title: 'new' }).content, undefined);
  assert.deepEqual(api.movePage([a, b], 0, -1), [a, b]);
});

test('fallback slides cannot be exported until a person fills their content', async () => {
  let sent = 0;
  global.fetch = async () => { sent++; return new Response(new Blob(['pptx'])); };
  await assert.rejects(api.generatePpt('方案', [{ title: '待确认', generation_mode: 'fallback', bullets: [] }]), /人工填写/);
  assert.equal(sent, 0);
  await api.generatePpt('方案', [{ title: '已审核', generation_mode: 'fallback', bullets: ['人工事实'] }]);
  assert.equal(sent, 1);
});
