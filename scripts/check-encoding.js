const fs = require('fs');
const path = require('path');
const root = path.join(__dirname, '..', 'apps', 'web-console');
const REPLACEMENT = String.fromCharCode(0xfffd);
const bad = [];
function walk(d) {
  for (const e of fs.readdirSync(d, { withFileTypes: true })) {
    if (e.name === 'node_modules' || e.name === '.next') continue;
    const f = path.join(d, e.name);
    if (e.isDirectory()) walk(f);
    else if (/\.(tsx?|css)$/.test(e.name)) {
      const s = fs.readFileSync(f, 'utf8');
      if (s.includes(REPLACEMENT)) bad.push(path.relative(root, f));
    }
  }
}
walk(root);
bad.forEach((f) => console.log(f));
console.log('total', bad.length);
