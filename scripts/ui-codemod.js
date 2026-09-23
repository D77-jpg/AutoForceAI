/**
 * UI 重设计 codemod：将 web-console 中的硬编码颜色替换为 @autoforce/ui-tokens 令牌。
 * 仅做文本级替换，不触碰逻辑。可重复运行（幂等）。
 */
const fs = require('fs');
const path = require('path');

const ROOT = path.join(__dirname, '..', 'apps', 'web-console');
const DIRS = ['app', 'components', 'contexts', 'lib'];
const EXTS = ['.tsx', '.ts', '.css'];

// 1) 任意值十六进制 → 令牌（保持前缀：text-[#xxx] -> text-<token>）
const HEX_MAP = {
  'f5f5f7': 'text',
  'd2d2d7': 'text-secondary',
  '86868b': 'text-secondary',
  'a1a1a6': 'text-secondary',
  '6e6e73': 'text-tertiary',
  '1c1c1e': 'surface',
  '2c2c2e': 'surface-2',
  '3a3a3c': 'surface-2',
  '39393d': 'surface-2',
  '0a84ff': 'accent',
  '0071e3': 'accent',
  '0077ed': 'accent-hover',
  '2997ff': 'accent',
  '64d2ff': 'accent',
  '7dc1ff': 'accent',
  '30d158': 'success',
  '34c759': 'success',
  'ff9f0a': 'warning',
  'ffd60a': 'warning',
  'ff453a': 'danger',
  'ff3b30': 'danger',
  'ff6961': 'danger',
};

// 2) 非标准透明度档位 → 最近合法档位
function normalizeAlpha(alpha) {
  const valid = [0, 5, 10, 15, 20, 25, 30, 35, 40, 45, 50, 55, 60, 65, 70, 75, 80, 85, 90, 95, 100];
  const n = parseInt(alpha, 10);
  if (valid.includes(n)) return alpha;
  let best = valid[0];
  for (const v of valid) if (Math.abs(v - n) < Math.abs(best - n)) best = v;
  return String(best);
}

// 3) Tailwind 默认色 → 令牌（仅替换颜色词，保留 hover: 等前缀与 /alpha）
const PALETTE_MAP = [
  // 文字
  [/\btext-(?:slate|gray|zinc|neutral)-(?:100|200|300)\b/g, 'text-text'],
  [/\btext-(?:slate|gray|zinc|neutral)-(?:400|500)\b/g, 'text-text-secondary'],
  [/\btext-(?:slate|gray|zinc|neutral)-(?:600|700|800|900)\b/g, 'text-text-tertiary'],
  [/\btext-(?:green|emerald|teal)-(?:300|400|500|600|700)\b/g, 'text-success'],
  [/\btext-(?:red|rose|pink)-(?:300|400|500|600|700)\b/g, 'text-danger'],
  [/\btext-(?:yellow|amber|orange)-(?:300|400|500|600|700|800)\b/g, 'text-warning'],
  [/\btext-(?:blue|indigo|violet|purple|sky|cyan|fuchsia)-(?:300|400|500|600|700)\b/g, 'text-accent'],
  // 背景
  [/\bbg-(?:slate|gray|zinc|neutral)-(?:50|100)\b/g, 'bg-surface-2'],
  [/\bbg-(?:slate|gray|zinc|neutral)-(?:200|300|700|800|900)\b/g, 'bg-surface-2'],
  [/\bbg-(?:green|emerald|teal)-(?:400|500|600|700)\b/g, 'bg-success'],
  [/\bbg-(?:red|rose|pink)-(?:400|500|600|700)\b/g, 'bg-danger'],
  [/\bbg-(?:yellow|amber|orange)-(?:400|500|600|700)\b/g, 'bg-warning'],
  [/\bbg-(?:blue|indigo|violet|purple|sky|cyan|fuchsia)-(?:400|500|600|700)\b/g, 'bg-accent'],
  // 浅色底（如 bg-green-500/10、bg-yellow-50）在上方规则后处理
  [/\bbg-(?:green|emerald|teal)-(?:50|100)\b/g, 'bg-success/10'],
  [/\bbg-(?:red|rose|pink)-(?:50|100)\b/g, 'bg-danger/10'],
  [/\bbg-(?:yellow|amber|orange)-(?:50|100)\b/g, 'bg-warning/10'],
  [/\bbg-(?:blue|indigo|violet|purple|sky|cyan)-(?:50|100)\b/g, 'bg-accent/10'],
  // 边框
  [/\bborder-(?:slate|gray|zinc|neutral)-(?:100|200|300|400|500|600|700|800)\b/g, 'border-separator'],
  [/\bborder-(?:green|emerald|teal)-(?:200|300|400|500|600)\b/g, 'border-success'],
  [/\bborder-(?:red|rose|pink)-(?:200|300|400|500|600)\b/g, 'border-danger'],
  [/\bborder-(?:yellow|amber|orange)-(?:200|300|400|500|600)\b/g, 'border-warning'],
  [/\bborder-(?:blue|indigo|violet|purple|sky|cyan)-(?:200|300|400|500|600)\b/g, 'border-accent'],
  // placeholder / divide / ring
  [/\bplaceholder-(?:slate|gray|zinc|neutral)-(?:300|400|500|600|700)\b/g, 'placeholder-text-tertiary'],
  [/\bdivide-(?:slate|gray|zinc|neutral)-(?:100|200|300|700|800)\b/g, 'divide-separator'],
  [/\bring-(?:blue|indigo|sky)-(?:400|500|600)\b/g, 'ring-accent'],
];

// 4) white/black 透明度与杂项
const MISC_MAP = [
  [/\bborder-white\/(\d{1,3})\b/g, 'border-separator'],
  [/\bdivide-white\/(\d{1,3})\b/g, 'divide-separator'],
  [/\bring-white\/(\d{1,3})\b/g, 'ring-separator'],
  [/\bbg-white\/(\d{1,3})\b/g, (m, a) => `bg-text/${normalizeAlpha(Math.min(parseInt(a, 10), 15))}`],
  [/\bborder-white\b/g, 'border-separator'],
  [/\bshadow-apple-lg\b/g, 'shadow-popover'],
  [/\bshadow-apple\b/g, 'shadow-card'],
  [/\brounded-apple-xl\b/g, 'rounded-2xl'],
  [/\brounded-apple-lg\b/g, 'rounded-xl'],
  [/\brounded-apple\b/g, 'rounded-lg'],
  [/\brounded-\[12px\]/g, 'rounded-md'],
  [/\brounded-\[14px\]/g, 'rounded-lg'],
  [/\brounded-\[20px\]/g, 'rounded-xl'],
  [/\brounded-\[24px\]/g, 'rounded-2xl'],
  [/\brounded-\[28px\]/g, 'rounded-2xl'],
  [/\bbg-black\b/g, 'bg-bg'],
];

let filesChanged = 0;
let replacements = 0;

function walk(dir) {
  for (const entry of fs.readdirSync(dir, { withFileTypes: true })) {
    if (entry.name === 'node_modules' || entry.name === '.next') continue;
    const full = path.join(dir, entry.name);
    if (entry.isDirectory()) walk(full);
    else if (EXTS.includes(path.extname(entry.name))) transform(full);
  }
}

function transform(file) {
  let src = fs.readFileSync(file, 'utf8');
  let out = src;
  let count = 0;

  // hex 任意值（含 /alpha）：[#0a84ff]/16 -> accent/15
  out = out.replace(/\[#([0-9a-fA-F]{6})\](?:\/(\d{1,3}))?/g, (m, hex, alpha) => {
    const token = HEX_MAP[hex.toLowerCase()];
    if (!token) return m;
    count++;
    return alpha ? `${token}/${normalizeAlpha(alpha)}` : token;
  });

  for (const [re, rep] of [...PALETTE_MAP, ...MISC_MAP]) {
    out = out.replace(re, (...args) => {
      count++;
      return typeof rep === 'function' ? rep(...args) : rep;
    });
  }

  if (out !== src) {
    fs.writeFileSync(file, out, 'utf8');
    filesChanged++;
    replacements += count;
    console.log(`✔ ${path.relative(ROOT, file)} (${count})`);
  }
}

for (const d of DIRS) {
  const p = path.join(ROOT, d);
  if (fs.existsSync(p)) walk(p);
}
console.log(`\n完成：${filesChanged} 个文件，约 ${replacements} 处替换。`);
