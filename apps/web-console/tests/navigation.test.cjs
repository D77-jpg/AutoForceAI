const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const test = require('node:test');

const root = path.resolve(__dirname, '..');
const sources = [
  'components/sidebar.tsx',
  'components/dashboard/AppSidebar.tsx',
  'components/dashboard/TopBar.tsx',
  'components/dashboard/system-products.ts',
  'lib/dashboard-mock.ts',
  'app/ops/page.tsx',
];
const forbidden = [
  '/ecommerce', '/organization/agents', '/digital-human/assets', '/monitor/alerts',
  '/crm/customers', '/crm/opportunities', '/crm/contracts',
];

for (const source of sources) {
  test(`${source}: clickable static navigation resolves to an app page`, () => {
    const text = fs.readFileSync(path.join(root, source), 'utf8')
      .replace(/^\s*\/\/[^\n]*$/gm, '');
    // Both JSX href="/path" and object data href: '/path' are clickable navigation.
    const links = [...text.matchAll(/\bhref\s*(?:=|:)\s*['"](\/[^'"?#]*)['"]/g)]
      .map((match) => match[1]);
    assert.ok(links.length, `${source} should contain navigation links`);
    for (const href of links) {
      assert.ok(!forbidden.some((route) => href === route || href.startsWith(`${route}/`)),
        `${source}: retired/duplicate route ${href}`);
      assert.ok(fs.existsSync(path.join(root, 'app', href.slice(1), 'page.tsx')),
        `${source}: ${href} has no app page`);
    }
  });
}

test('knowledge solution remains visible and labelled as in development', () => {
  const sidebar = fs.readFileSync(path.join(root, 'components/sidebar.tsx'), 'utf8');
  assert.match(sidebar, /href: '\/knowledge\/solution'[^\n]*badge: '开发中'/);
});
