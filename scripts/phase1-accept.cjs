const fs = require('fs');
const path = require('path');
const API = 'http://localhost:8010';

async function req(method, url, { token, json, form, raw } = {}) {
  const headers = {};
  let body;
  if (token) headers.Authorization = 'Bearer ' + token;
  if (json) { headers['Content-Type'] = 'application/json'; body = JSON.stringify(json); }
  if (form) body = form;
  const res = await fetch(API + url, { method, headers, body });
  const text = await res.text();
  let data;
  try { data = JSON.parse(text); } catch { data = text; }
  return { status: res.status, data, text };
}

(async () => {
  const fail = [];
  const ok = (name, cond, extra) => {
    console.log((cond ? 'PASS ' : 'FAIL ') + name + (extra ? ' | ' + extra : ''));
    if (!cond) fail.push(name);
  };

  const h = await req('GET', '/health');
  ok('health', h.status === 200 && h.data.status === 'ok');

  let login = await req('POST', '/auth/login', { json: { email: 'admin@test.com', password: 'test123456' } });
  if (login.status !== 200) {
    await req('POST', '/auth/register', { json: { email: 'admin@test.com', password: 'test123456', nickname: 'admin' } });
    login = await req('POST', '/auth/login', { json: { email: 'admin@test.com', password: 'test123456' } });
  }
  ok('login', login.status === 200 && login.data.access_token, 'status=' + login.status);
  const token = login.data.access_token;

  const kb = await req('POST', '/api/v1/kb/bases', { token, json: { name: 'Product Catalog', description: 'Phase1 accept', is_public: true } });
  ok('create kb', kb.status === 200 && kb.data.id, JSON.stringify(kb.data).slice(0, 120));
  const kbId = kb.data.id;

  const tmp = path.join(__dirname, '_phase1_sample.md');
  fs.writeFileSync(tmp, `# Hydraulic Pump HP-200\n\nMOQ: 50 units\nLead time: 25 days\nPrice: FOB Ningbo USD 128 / unit\nMaterial: cast iron\nWarranty: 18 months\n`);
  const form = new FormData();
  form.append('file', new Blob([fs.readFileSync(tmp)], { type: 'text/markdown' }), 'product_hp200.md');
  const up = await req('POST', `/api/v1/kb/bases/${kbId}/docs`, { token, form });
  ok('upload doc', up.status === 200 && up.data.id, JSON.stringify(up.data).slice(0, 160));
  const docId = up.data.id;

  const pdfBody = Buffer.from(
    '%PDF-1.1\n' +
    '1 0 obj<< /Type /Catalog /Pages 2 0 R >>endobj\n' +
    '2 0 obj<< /Type /Pages /Kids [3 0 R] /Count 1 >>endobj\n' +
    '3 0 obj<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 4 0 R /Resources<< /Font<< /F1 5 0 R >> >> >>endobj\n' +
    '4 0 obj<< /Length 78 >>stream\n' +
    'BT /F1 12 Tf 72 720 Td (Hydraulic Pump HP-200 MOQ: 50 units Lead time 25 days) Tj ET\n' +
    'endstream\nendobj\n' +
    '5 0 obj<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>endobj\n' +
    'xref\n0 6\n0000000000 65535 f \ntrailer<< /Size 6 /Root 1 0 R >>\nstartxref\n0\n%%EOF\n'
  );
  const pdfForm = new FormData();
  pdfForm.append('file', new Blob([pdfBody], { type: 'application/pdf' }), 'product_hp200.pdf');
  const upPdf = await req('POST', `/api/v1/kb/bases/${kbId}/docs`, { token, form: pdfForm });
  ok('upload pdf', upPdf.status === 200 && upPdf.data.id, JSON.stringify(upPdf.data).slice(0, 160));
  let pdfStatus = 'pending';
  for (let i = 0; i < 15; i++) {
    await new Promise(r => setTimeout(r, 400));
    const docs = await req('GET', `/api/v1/kb/bases/${kbId}/docs`, { token });
    const d = (docs.data.items || []).find(x => x.id === upPdf.data.id);
    if (d) pdfStatus = d.status;
    if (pdfStatus === 'embedded' || pdfStatus === 'indexed' || pdfStatus === 'failed') break;
  }
  ok('pdf index status', pdfStatus === 'embedded' || pdfStatus === 'indexed', 'status=' + pdfStatus);

  // wait for background index
  let status = 'pending';
  for (let i = 0; i < 15; i++) {
    await new Promise(r => setTimeout(r, 400));
    const docs = await req('GET', `/api/v1/kb/bases/${kbId}/docs`, { token });
    const d = (docs.data.items || []).find(x => x.id === docId);
    if (d) status = d.status;
    if (status === 'embedded' || status === 'indexed' || status === 'failed') break;
  }
  ok('index status', status === 'embedded' || status === 'indexed', 'status=' + status);

  const search = await req('POST', '/api/v1/kb/search', { token, json: { query: "What's the MOQ for HP-200?", kb_ids: [kbId], score_threshold: 0.05 } });
  const hits = search.data.hits || [];
  ok('search hits', search.status === 200 && hits.length > 0, 'n=' + hits.length + ' first=' + ((hits[0] && hits[0].content) || '').slice(0, 80));
  ok('search mentions MOQ', JSON.stringify(hits).toLowerCase().includes('50') || JSON.stringify(hits).toLowerCase().includes('moq'));

  const bot = await req('POST', '/api/v1/service/bots', { token, json: { name: 'Export Assistant', kb_id: kbId, welcome_message: 'Hello! How can I help you today?' } });
  ok('create bot', bot.status === 200 && bot.data.id, JSON.stringify(bot.data).slice(0, 120));

  const start = await req('POST', '/api/v1/service/widget/start', { json: { bot_id: bot.data.id } });
  ok('widget start', start.status === 200 && start.data.session_uuid, JSON.stringify(start.data).slice(0, 160));
  const sid = start.data.session_uuid;

  const chat = await req('POST', '/api/v1/service/widget/chat', { json: { session_uuid: sid, message: "What's the MOQ for Hydraulic Pump HP-200? Please quote. My email is buyer@acme.com from Germany.", visitor_email: 'buyer@acme.com', visitor_name: 'Hans' } });
  ok('widget chat', chat.status === 200 && chat.data.reply, 'reply=' + String(chat.data.reply || '').slice(0, 100));
  ok('intent inquiry', chat.data.intent && chat.data.intent.is_inquiry === true, JSON.stringify(chat.data.intent));
  ok('lead created', chat.data.lead && chat.data.lead.id, JSON.stringify(chat.data.lead));

  const sessions = await req('GET', '/api/v1/service/sessions', { token });
  ok('sessions list', sessions.status === 200 && (sessions.data.items || []).length > 0, 'n=' + ((sessions.data.items || []).length));

  const leads = await req('GET', '/api/v1/leads', { token });
  ok('leads list', leads.status === 200 && (leads.data.items || []).some(x => (x.email || '').includes('buyer@acme.com')), 'n=' + ((leads.data.items || []).length));

  const chat2 = await req('POST', '/api/v1/service/widget/chat', { json: { session_uuid: sid, message: 'Please send catalog too. buyer@acme.com' } });
  const leads2 = await req('GET', '/api/v1/leads', { token });
  const same = (leads2.data.items || []).filter(x => (x.email || '') === 'buyer@acme.com');
  ok('email dedup', same.length === 1, 'count=' + same.length);

  if (same[0]) {
    const st = await req('PATCH', '/api/v1/leads/' + same[0].id, { token, json: { status: 'contacted' } });
    ok('status change', st.status === 200 && st.data.status === 'contacted');
  }

  const csv = await req('GET', '/api/v1/leads/export.csv', { token });
  ok('csv export', csv.status === 200 && String(csv.text).includes('buyer@acme.com'));

  const widgetJs = await req('GET', '/widget/autoforce-chat.js');
  ok('widget js', widgetJs.status === 200 && String(widgetJs.text).includes('widget/chat'));

  const demo = await req('GET', '/widget/demo.html');
  ok('widget demo', demo.status === 200);

  console.log('\n' + (fail.length ? ('FAILED: ' + fail.join(', ')) : 'ALL CHECKS PASSED'));
  process.exit(fail.length ? 1 : 0);
})().catch(e => { console.error(e); process.exit(1); });
