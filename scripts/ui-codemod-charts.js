/** 图表（recharts/SVG）与装饰性 glow 阴影的令牌化 */
const fs = require('fs');
const path = require('path');
const ROOT = path.join(__dirname, '..', 'apps', 'web-console');

const FIXES = [
  // 结构色
  [/"#334155"|'#334155'/g, '"rgb(var(--ui-text-tertiary))"'],
  [/"#94a3b8"|'#94a3b8'/g, '"rgb(var(--ui-text-secondary))"'],
  [/'#1c1c1e'/g, "'rgb(var(--ui-surface))'"],
  [/'#0F1116'/g, "'rgb(var(--ui-surface))'"],
  [/'rgba\(255,255,255,0\.1\)'/g, "'rgb(var(--ui-separator) / var(--ui-separator-alpha))'"],
  [/'#e2e8f0'/g, "'rgb(var(--ui-text))'"],
  [/'1px solid #333'/g, "'1px solid rgb(var(--ui-separator) / var(--ui-separator-alpha))'"],
  // 系列色
  [/"#6366f1"|'#6366f1'/g, '"rgb(var(--ui-accent))"'],
  [/"#818cf8"|'#818cf8'/g, '"rgb(var(--ui-accent) / 0.6)"'],
  [/"#ec4899"|'#ec4899'/g, '"rgb(var(--ui-danger))"'],
  [/"#1e293b"|'#1e293b'/g, '"rgb(var(--ui-surface-2))"'],
  [/"#10b981"|'#10b981'/g, '"rgb(var(--ui-success))"'],
  [/"#ef4444"|'#ef4444'/g, '"rgb(var(--ui-danger))"'],
  [/"#f97316"|'#f97316'/g, '"rgb(var(--ui-warning))"'],
  [/"#3b82f6"|'#3b82f6'/g, '"rgb(var(--ui-accent))"'],
  [/"#a855f7"|'#a855f7'/g, '"rgb(var(--ui-accent-hover))"'],
  [/#ec4899 1px/g, 'rgb(var(--ui-danger)) 1px'],
  [/"#ffffff10"/g, '"rgb(var(--ui-separator) / var(--ui-separator-alpha))"'],
  [/"#1c1c1e"/g, '"rgb(var(--ui-surface))"'],
  [/"rgba\(255,255,255,0\.1\)"/g, '"rgb(var(--ui-separator) / var(--ui-separator-alpha))"'],
  // glow 阴影
  [/rgba\(16,185,129,([\d.]+)\)/g, 'rgb(var(--ui-success)/$1)'],
  [/rgba\(139,92,246,([\d.]+)\)/g, 'rgb(var(--ui-accent)/$1)'],
  [/rgba\(244,63,94,([\d.]+)\)/g, 'rgb(var(--ui-danger)/$1)'],
  [/rgba\(236,72,153,([\d.]+)\)/g, 'rgb(var(--ui-danger)/$1)'],
];

function walk(d) {
  for (const e of fs.readdirSync(d, { withFileTypes: true })) {
    if (e.name === 'node_modules' || e.name === '.next') continue;
    const f = path.join(d, e.name);
    if (e.isDirectory()) walk(f);
    else if (/\.tsx$/.test(e.name)) {
      let s = fs.readFileSync(f, 'utf8');
      const before = s;
      for (const [re, rep] of FIXES) s = s.replace(re, rep);
      if (s !== before) {
        fs.writeFileSync(f, s, 'utf8');
        console.log('✔', path.relative(ROOT, f));
      }
    }
  }
}
walk(path.join(ROOT, 'app'));
walk(path.join(ROOT, 'components'));
console.log('done');
