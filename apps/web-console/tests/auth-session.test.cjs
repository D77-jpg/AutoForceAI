const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const ts = require('typescript');
const Module = require('node:module');
const axios = require('axios');

function load(relativePath, mocks = {}) {
  const filename = path.resolve(__dirname, relativePath);
  const mod = new Module(filename, module);
  mod.filename = filename;
  mod.paths = module.paths;
  const originalRequire = mod.require.bind(mod);
  mod.require = name => Object.hasOwn(mocks, name) ? mocks[name] : originalRequire(name);
  mod._compile(ts.transpileModule(fs.readFileSync(filename, 'utf8'), {
    compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2020, jsx: ts.JsxEmit.React, esModuleInterop: true },
  }).outputText, filename);
  return mod.exports;
}

const session = load('../lib/auth-session.ts');
const api = load('../lib/api.ts', { './auth-session': session }).default;

function browser(token = 'expired', user = JSON.stringify({ id: 1, username: 'tester' }), pathname = '/') {
  const values = new Map([['token', token], ['user', user]]);
  global.localStorage = {
    getItem: key => values.get(key) ?? null,
    setItem: (key, value) => values.set(key, value),
    removeItem: key => values.delete(key),
  };
  global.sessionStorage = { getItem: () => null, setItem: () => {} };
  const redirects = [];
  global.window = new EventTarget();
  window.location = { pathname, replace: url => {
    assert.equal(localStorage.getItem('token'), null, 'clear auth before navigation');
    assert.equal(localStorage.getItem('user'), null);
    redirects.push(url);
  } };
  return { values, redirects };
}

function rejectResponse(status) {
  return config => Promise.reject(new axios.AxiosError('rejected', 'ERR_BAD_RESPONSE', config, {}, { status }));
}

test('parallel dashboard 401s clear the rejected session and navigate only once', async () => {
  const { redirects } = browser();
  let events = 0;
  window.addEventListener(session.AUTH_SESSION_EXPIRED_EVENT, () => events++);
  const results = await Promise.allSettled(Array.from({ length: 4 }, () => api.get('/api/v1/leads/summary', { adapter: rejectResponse(401) })));
  assert.ok(results.every(result => result.status === 'rejected'));
  assert.deepEqual(redirects, ['/login']);
  assert.equal(events, 1);
});

test('a late 401 from an old session cannot erase a newer login', async () => {
  const { redirects } = browser('old');
  await assert.rejects(api.get('/api/v1/leads/summary', { adapter: config => {
    localStorage.setItem('token', 'new');
    return rejectResponse(401)(config);
  } }));
  assert.equal(localStorage.getItem('token'), 'new');
  assert.deepEqual(redirects, []);
});

test('401 on login clears auth without reloading, other failures retain auth', async () => {
  const { redirects } = browser('expired', undefined, '/login');
  await assert.rejects(api.get('/api/v1/leads/summary', { adapter: rejectResponse(401) }));
  assert.equal(localStorage.getItem('token'), null);
  assert.deepEqual(redirects, []);
  for (const status of [403, 500]) {
    browser('valid');
    await assert.rejects(api.get('/api/v1/leads/summary', { adapter: rejectResponse(status) }));
    assert.equal(localStorage.getItem('token'), 'valid');
  }
});

// Drive the provider's state/effects without mounting a dashboard or issuing real requests.
function providerHarness(pathname) {
  const states = [];
  const effects = [];
  const dependencies = [];
  const routes = [];
  const router = { push: url => routes.push(url), replace: url => routes.push(url) };
  let cursor = 0;
  const react = {
    createContext: () => ({ Provider: 'Provider' }),
    createElement: (type, props, children) => ({ type, props, children }),
    useState: initial => {
      const index = cursor++;
      if (!(index in states)) states[index] = initial;
      return [states[index], value => { states[index] = value; }];
    },
    useEffect: (effect, deps) => {
      const index = cursor++;
      if (!dependencies[index] || deps.some((value, i) => value !== dependencies[index][i])) {
        dependencies[index] = deps;
        effects.push(effect);
      }
    },
  };
  const { AuthProvider } = load('../contexts/AuthContext.tsx', {
    react,
    'next/navigation': { useRouter: () => router, usePathname: () => pathname, useSearchParams: () => null },
    '../lib/auth-session': session,
  });
  return {
    render: () => { cursor = 0; return AuthProvider({ children: 'dashboard' }); },
    flush: () => { effects.splice(0).forEach(effect => effect()); },
    routes,
  };
}

test('protected children wait for auth restoration, and disappear on session expiry', () => {
  browser('valid');
  const provider = providerHarness('/');
  assert.equal(provider.render(), null);
  provider.flush();
  assert.equal(provider.render().children, 'dashboard');
  provider.flush();
  session.expireAuthSession('valid');
  assert.equal(provider.render(), null);
  provider.flush();
  assert.deepEqual(provider.routes, ['/login']);
});

test('missing, partial or corrupt sessions never mount protected pages or bounce from login', () => {
  for (const [token, user] of [[null, null], ['old', null], [null, '{"id":1,"username":"tester"}'], ['old', '{broken'], ['old', 'null']]) {
    browser(token, user);
    const protectedPage = providerHarness('/');
    assert.equal(protectedPage.render(), null);
    protectedPage.flush();
    assert.equal(protectedPage.render(), null);
    protectedPage.flush();
    assert.deepEqual(protectedPage.routes, ['/login']);
    assert.equal(localStorage.getItem('token'), null);
    const loginPage = providerHarness('/login');
    loginPage.render();
    loginPage.flush();
    assert.equal(loginPage.render().children, 'dashboard');
    loginPage.flush();
    assert.deepEqual(loginPage.routes, []);
  }
});
