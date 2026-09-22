// Recover files whose UTF-8 bytes were misread as GBK then re-saved as UTF-8.
// Usage: node scripts/fix-mojibake.cjs <file> [--write]
const fs = require('fs');
const file = process.argv[2];
const doWrite = process.argv.includes('--write');

let iconv;
const candidates = [
  'iconv-lite',
  'D:/D77/project/AutoForceAI/apps/web-console/node_modules/iconv-lite',
];
for (const c of candidates) {
  try { iconv = require(c); break; } catch (e) {}
}
if (!iconv) {
  console.error('iconv-lite not found in any known location.');
  process.exit(2);
}

const s1 = fs.readFileSync(file, 'utf8');           // garbled text
const gbkBytes = iconv.encode(s1, 'gbk');           // back to misread bytes
const recovered = iconv.decode(gbkBytes, 'utf8');   // reinterpret as utf8

const lines = recovered.split('\n');
let shown = 0;
for (const l of lines) {
  if (/[一-鿿]/.test(l) && shown < 8) { console.log('  ' + l.trim()); shown++; }
}
const fffd = (recovered.split('').filter(c => c === '').length);
console.log('[preview] replacement-char count: ' + fffd);
if (doWrite && fffd < 5) {
  fs.writeFileSync(file, recovered, 'utf8');
  console.log('[write] recovered file saved.');
} else if (doWrite) {
  console.log('[abort] too many unrecoverable chars; not writing.');
}
