// Reproduce contrast checks against the actual preview tokens, without dependencies.
const fs = require('node:fs');
const assert = require('node:assert/strict');
const html = fs.readFileSync(__dirname + '/indigo-preview.html', 'utf8');
function luminance(hex) {
  const rgb = hex.match(/[a-f\d]{2}/gi).map(v => parseInt(v, 16) / 255)
    .map(v => v <= .04045 ? v / 12.92 : ((v + .055) / 1.055) ** 2.4);
  return rgb[0] * .2126 + rgb[1] * .7152 + rgb[2] * .0722;
}
const pairs = [
  ['text', 'bg', 4.5], ['text', 'surface', 4.5], ['muted', 'surface', 4.5],
  ['muted', 'bg', 4.5], ['accent', 'surface', 4.5], ['accent', 'selected', 4.5],
  ['on-accent', 'accent', 4.5], ['success', 'success-bg', 4.5], ['error', 'error-bg', 4.5],
  ['control', 'surface', 3], ['accent', 'bg', 3],
];
for (const [i, match] of [...html.matchAll(/:root(?:\[data-theme=dark\])?\{([^}]+)\}/g)].entries()) {
  const tokens = Object.fromEntries([...match[1].matchAll(/--([\w-]+):#([a-f\d]{6})/gi)].map(m => [m[1], m[2]]));
  for (const [foreground, background, minimum] of pairs) {
    const values = [luminance(tokens[foreground]), luminance(tokens[background])];
    const ratio = (Math.max(...values) + .05) / (Math.min(...values) + .05);
    assert(ratio >= minimum, `${i ? 'dark' : 'light'} ${foreground}/${background}: ${ratio}`);
    console.log(`${i ? 'dark' : 'light'} ${foreground}/${background}: ${ratio.toFixed(2)} PASS`);
  }
}
