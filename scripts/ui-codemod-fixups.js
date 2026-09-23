/** codemod 之后的残余硬编码修复（Node UTF-8 安全版） */
const fs = require('fs');
const path = require('path');
const ROOT = path.join(__dirname, '..', 'apps', 'web-console');

const FIXES = [
  [/bg-\[#020408\]/g, 'bg-bg'],
  [/bg-\[#0a0f1c\]/g, 'bg-surface'],
  [/bg-\[#050912\]/g, 'bg-bg'],
  [/bg-\[#0b101a\]/g, 'bg-surface'],
  [/\[#bf5af2\]/g, 'accent-hover'],
  [/text-\[#ff375f\]/g, 'text-danger'],
  [/hover:bg-\[#242426\]/g, 'hover:bg-surface-2'],
  [/bg-\[#1e293b\]/g, 'bg-surface'],
  [/border-separator\/20/g, 'border-separator'],
  [/bg-slate-500\/10/g, 'bg-surface-2'],
  [/bg-slate-500\b/g, 'bg-text-tertiary'],
  [/hover:bg-slate-600/g, 'hover:bg-text/10'],
  [/text-orange-200/g, 'text-warning'],
  [/white\/\[/g, 'text/['],
  [/via-white\/10/g, 'via-text/10'],
  [/border-b-white\/50/g, 'border-b-text/50'],
];

const TARGETS = [
  'app/optimize/page.tsx', 'app/diagnosis/page.tsx', 'app/monitor/page.tsx',
  'app/ops/enterprises/page.tsx', 'app/page.tsx', 'components/ecommerce/AICreateDialog.tsx',
  'app/distribution/page.tsx', 'app/ops/users/page.tsx', 'app/marketing/text-gen/page.tsx',
  'app/platform/skills/page.tsx', 'app/login/page.tsx', 'app/platform/models/page.tsx',
  'app/knowledge/stats/page.tsx', 'app/platform/traffic/page.tsx',
];

for (const rel of TARGETS) {
  const file = path.join(ROOT, rel);
  if (!fs.existsSync(file)) continue;
  let s = fs.readFileSync(file, 'utf8');
  for (const [re, rep] of FIXES) s = s.replace(re, rep);
  fs.writeFileSync(file, s, 'utf8');
}
console.log('fixups applied');
