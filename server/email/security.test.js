const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const generate = require("./generateEmail");

test("newsletter escapes untrusted fields and rejects unsafe links", () => {
  process.env.CLIENT = 'javascript:alert(1)';
  const html = generate([{ id: '../bad"', category: '__proto__', title: '<script>alert(1)</script>',
    location: '<img onerror=alert(1)>', summary: '<b>bad</b>', publication_date: 123 }]);
  assert.ok(html.includes('__proto__'));
  assert.ok(html.includes('&lt;script&gt;'));
  assert.ok(!html.includes('<script>'));
  assert.ok(!html.includes('href="javascript:'));
});

test("SMTP module verifies TLS and has no send-on-import or credential logging", () => {
  const code = fs.readFileSync(require.resolve('./sendEmail'), 'utf8');
  assert.ok(code.includes('rejectUnauthorized: true'));
  assert.ok(code.includes('require.main === module'));
  assert.ok(!code.includes('console.log("process.env.PASS'));
});
