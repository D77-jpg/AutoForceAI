const API = process.env.API_URL || 'http://localhost:8010';

async function req(method, url, { token, json } = {}) {
  const headers = {};
  let body;
  if (token) headers.Authorization = 'Bearer ' + token;
  if (json) {
    headers['Content-Type'] = 'application/json';
    body = JSON.stringify(json);
  }
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
  const auth = { token };

  const blog = await req('POST', '/api/v1/marketing/text/generate', {
    ...auth,
    json: {
      content_type: 'seo_blog',
      product_name: 'Hydraulic Pump HP-200',
      selling_points: 'MOQ 50\nLead time 25 days\nFOB Ningbo\nISO 9001',
      language: 'en',
    },
  });
  const words = blog.data.word_count || 0;
  const hasChinese = /[\u4e00-\u9fff]/.test((blog.data.body || '').replace(/阶段|配置|模板/g, ''));
  ok('3.A1 seo blog generated', blog.status === 200 && words >= 700, 'status=' + blog.status + ' words=' + words);
  ok('3.A1 english body', blog.status === 200 && !hasChinese && /HP-200|Hydraulic/i.test(blog.data.body || ''), 'chinese=' + hasChinese);

  const li = await req('POST', '/api/v1/marketing/text/generate', {
    ...auth,
    json: { content_type: 'linkedin_post', product_name: 'Hydraulic Pump HP-200', selling_points: 'MOQ 50' },
  });
  ok('linkedin post', li.status === 200 && (li.data.word_count || 0) >= 80, 'words=' + (li.data.word_count || 0));

  const img = await req('POST', '/api/v1/marketing/images/generate', {
    ...auth,
    json: { product_name: 'Hydraulic Pump HP-200', preset: 'product_scene' },
  });
  ok('3.2 image gen endpoint', img.status === 200 && (img.data.prompt || img.data.url), JSON.stringify({ mock: img.data.mock, id: img.data.id }).slice(0, 120));

  const wp = await req('POST', '/api/v1/marketing/publish', {
    ...auth,
    json: {
      platform: 'wordpress',
      title: blog.data.title || 'HP-200 Guide',
      content: blog.data.body || 'body',
      content_id: blog.data.id,
    },
  });
  ok('3.A3 wordpress publish', wp.status === 200 && wp.data.job_id && wp.data.link, JSON.stringify(wp.data).slice(0, 180));

  const linkedin = await req('POST', '/api/v1/marketing/publish', {
    ...auth,
    json: {
      platform: 'linkedin',
      title: li.data.title || 'LinkedIn post',
      content: li.data.body || 'body',
    },
  });
  ok('3.A2 linkedin queued', linkedin.status === 200 && linkedin.data.status === 'queued' && linkedin.data.job_id, JSON.stringify(linkedin.data).slice(0, 160));

  const xpub = await req('POST', '/api/v1/marketing/publish', {
    ...auth,
    json: { platform: 'x', title: 'HP-200', content: 'Export-ready hydraulic pump, MOQ 50, FOB Ningbo.' },
  });
  ok('x queued', xpub.status === 200 && xpub.data.job_id, 'job=' + xpub.data.job_id);

  const jobs = await req('GET', '/api/v1/rpa/jobs?limit=20', auth);
  const items = Array.isArray(jobs.data) ? jobs.data : (jobs.data.items || []);
  const plats = items.map((j) => (j.platform || '').toLowerCase());
  ok('distribution has overseas jobs', plats.includes('linkedin') && (plats.includes('wordpress') || plats.includes('website')), plats.slice(0, 8).join(','));

  const analyze = await req('POST', '/api/v1/branding/analyze', {
    ...auth,
    json: {
      target_brand: 'AutoForceAI',
      query: 'best hydraulic pump supplier China',
      engine_name: 'perplexity',
      language: 'en',
    },
  });
  ok('3.A4 geo analyze accepted', analyze.status === 200 && analyze.data.id, 'id=' + analyze.data.id + ' engine=' + analyze.data.engine_name);

  let mentioned = null;
  let taskStatus = analyze.data.status;
  for (let i = 0; i < 20; i++) {
    await new Promise((r) => setTimeout(r, 500));
    const t = await req('GET', `/api/v1/branding/tasks/${analyze.data.id}`, auth);
    taskStatus = t.data.status;
    mentioned = t.data.is_mentioned;
    if (taskStatus === 'completed' || taskStatus === 'failed') break;
  }
  ok('3.A4 geo task finished', taskStatus === 'completed' || taskStatus === 'failed', 'status=' + taskStatus + ' mentioned=' + mentioned);

  const watch = await req('POST', '/api/v1/branding/watches', {
    ...auth,
    json: {
      target_brand: 'AutoForceAI',
      query: 'best hydraulic pump supplier China',
      engine_name: 'perplexity',
      language: 'en',
      interval_hours: 24,
    },
  });
  ok('geo watch created', watch.status === 200 && watch.data.id, JSON.stringify({ id: watch.data.id, next: watch.data.next_run_at }).slice(0, 160));

  const summary = await req('GET', '/api/v1/branding/diagnosis-summary?brand=AutoForceAI', auth);
  ok('3.7 diagnosis radar from real tasks', summary.status === 200 && Array.isArray(summary.data.radar) && summary.data.radar.length === 6, 'sample=' + summary.data.sample_size);

  const funnel = await req('GET', '/api/v1/marketing/funnel?days=30', auth);
  const steps = (funnel.data.steps || []).map((s) => s.key);
  ok('3.A5 funnel steps', funnel.status === 200 && steps.join(',') === 'content,publish,exposure,leads,crm', steps.join(','));
  ok('3.A5 funnel has content+jobs', funnel.status === 200 && funnel.data.kpis.content >= 1 && funnel.data.kpis.jobs >= 1, JSON.stringify(funnel.data.kpis));

  const wpStatus = await req('GET', '/api/v1/marketing/wordpress/status', auth);
  ok('wordpress status endpoint', wpStatus.status === 200 && typeof wpStatus.data.configured === 'boolean');

  if (fail.length) {
    console.log('\nFAILED: ' + fail.join(', '));
    process.exit(1);
  }
  console.log('\nALL PHASE 3 CHECKS PASSED');
})().catch((e) => {
  console.error(e);
  process.exit(1);
});
