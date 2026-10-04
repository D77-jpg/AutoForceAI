// Real Genesis application + real isolated MongoDB. No mail/model worker starts.
// Genesis checkout is read-only; all fixtures/uploads are outside that checkout.
const path = require('node:path');
const { createRequire } = require('node:module');
const { spawn } = require('node:child_process');
const { mkdtemp, rm } = require('node:fs/promises');
const os = require('node:os');
const crypto = require('node:crypto');
const { pathToFileURL } = require('node:url');

(async () => {
  const root = path.resolve(__dirname, '..');
  const genesis = path.resolve(process.env.ACCEPTANCE_GENESIS_ROOT || path.join(root, '.codex-worktrees/genesis-main-release'));
  const serverRoot = path.join(genesis, 'server');
  const req = createRequire(path.join(serverRoot, 'package.json'));
  const { MongoMemoryServer } = req('mongodb-memory-server');
  const directory = await mkdtemp(path.join(os.tmpdir(), 'autoforce-genesis-'));
  const mongo = await MongoMemoryServer.create({ instance: { dbName: 'local_acceptance' } });
  Object.assign(process.env, {
    NODE_ENV: 'test', JWT_SECRET: crypto.randomBytes(32).toString('hex'),
    ADMIN_PASSWORD: 'Local-Acceptance-only!2026', MAIL_TRANSPORT: 'mock', IMAP_ENABLED: 'false',
    MONGODB_URI: mongo.getUri(), UPLOAD_DIR: directory,
    PROJECT_MAIL_CONFIGS_JSON: '{}', AI_PROVIDER: 'mock',
  });
  req('tsx/cjs');
  const mongoose = req('mongoose');
  let server, child, web, stopping;
  const stop = async () => {
    if (stopping) return stopping;
    stopping = (async () => {
      if (child && child.exitCode === null) { const exited = new Promise(resolve => child.once('exit', resolve)); child.kill(); await exited; }
      if (web) await web.close();
      if (server) await new Promise(resolve => server.close(resolve));
      await mongoose.disconnect();
      await mongo.stop();
      if (path.dirname(directory) !== os.tmpdir() || !path.basename(directory).startsWith('autoforce-genesis-')) throw new Error('Unsafe cleanup target');
      await rm(directory, { recursive: true, force: true });
    })();
    return stopping;
  };
  process.once('SIGINT', () => stop().then(() => process.exit(0)));
  process.once('SIGTERM', () => stop().then(() => process.exit(0)));
  try {
    await mongoose.connect(mongo.getUri(), { dbName: 'local_acceptance' });
    const models = req(path.join(serverRoot, 'src/models/index.ts'));
    const project = await models.Project.create({ name: 'Local acceptance', slug: 'local-acceptance', code: 'LOCAL', companyName: 'Fictional test supplier', mailProfileKey: 'unconfigured' });
    await Promise.all(['Customer', 'CustomerEvent', 'Quotation', 'IntegrationCredential', 'IntegrationIdempotency', 'User'].map(name => models[name].init()));
    await models.User.create({ username: 'acceptance', displayName: 'Local acceptance', role: 'admin', passwordHash: await models.hashPassword(process.env.ADMIN_PASSWORD), defaultProjectId: project._id, projectIds: [project._id] });
    const { token } = await req(path.join(serverRoot, 'src/services/integration-credential.service.ts')).createCredential({
      name: 'Isolated AutoForceAI acceptance', projectIds: [String(project._id)],
      scopes: ['customers:upsert', 'outcomes:read', 'stats:read', 'quotations:read', 'quotations:draft'],
    });
    const app = req(path.join(serverRoot, 'src/app.ts')).createApp();
    server = await new Promise(resolve => { const instance = app.listen(5012, '127.0.0.1', () => resolve(instance)); });
    if (process.argv.includes('--serve')) {
      // Consume the existing Genesis UI read-only; Vite caches belong to our temp root.
      const webRoot = path.join(genesis, 'web');
      const webReq = createRequire(path.join(webRoot, 'package.json'));
      const { createServer } = await import(pathToFileURL(webReq.resolve('vite')).href);
      const react = (await import(pathToFileURL(webReq.resolve('@vitejs/plugin-react')).href)).default;
      process.env.VITE_API_BASE_URL = '/api';
      // Tailwind's existing relative config/content globs resolve from web cwd.
      process.chdir(webRoot);
      web = await createServer({ root: webRoot, configFile: false, envDir: directory, cacheDir: path.join(directory, 'vite-cache'),
        plugins: [react()], resolve: { alias: { '@': path.join(webRoot, 'src') } },
        server: { host: '127.0.0.1', port: 5173, strictPort: true, proxy: { '/api': { target: 'http://127.0.0.1:5012', changeOrigin: true, headers: { origin: 'http://localhost:5173' } } } },
      });
      await web.listen();
    }
    child = spawn(path.join(root, 'services/digital-brain/venv/Scripts/python.exe'), [path.join(root, 'scripts/local-functional-acceptance.py'), '--crm', ...process.argv.slice(2)], {
      cwd: root, windowsHide: true, stdio: 'inherit',
      env: { ...process.env, ACCEPTANCE_TEMP_ROOT: directory, ACCEPTANCE_CRM_WEB_URL: web ? 'http://localhost:5173' : '', ACCEPTANCE_CRM_URL: 'http://127.0.0.1:5012/api', ACCEPTANCE_CRM_PROJECT: String(project._id), ACCEPTANCE_CRM_TOKEN: token, ACCEPTANCE_CRM_PASSWORD: process.env.ADMIN_PASSWORD },
    });
    const code = await new Promise(resolve => child.once('exit', resolve));
    process.exitCode = code || 0;
  } finally { await stop(); }
})().catch(error => { console.error(`Isolated Genesis acceptance failed (${error.name}).`); process.exitCode = 1; });
