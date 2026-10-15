const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const postcss = require("postcss");
const tailwind = require("@tailwindcss/postcss");

test("Tailwind preserves theme, typography, layout and animation utilities", async () => {
  const file = path.resolve(__dirname, "../app/globals.css");
  const input = fs.readFileSync(file, "utf8") + `
    @source inline("container bg-background text-foreground border-border dark:bg-background rounded-md shadow-sm outline-none animate-in fade-in-0 zoom-in-95 prose prose-lg prose-headings:font-bold");
  `;
  const { css } = await postcss([tailwind()]).process(input, { from: file });
  for (const selector of [".container", ".bg-background", ".text-foreground", ".border-border", ".rounded-md", ".shadow-sm", ".outline-none", ".prose", ".prose-lg"]) {
    assert.ok(css.includes(selector), `Missing utility ${selector}`);
  }
  assert.ok(css.includes("hsl(var(--background))"));
  assert.ok(css.includes("max-width: 1400px"));
  assert.ok(css.includes("padding-inline: 2rem"));
  assert.ok(css.includes("outline: 2px solid transparent"));
  assert.ok(css.includes("--tw-enter-opacity: 0"));
  assert.ok(css.includes("@keyframes enter"));
  assert.ok(css.includes(".dark"));
  assert.ok(css.includes(":where(h1"));
});
