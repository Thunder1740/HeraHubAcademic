import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import test from "node:test";

test("renders FarmaHub metadata and application shell", async () => {
  const html = await readFile(new URL("../out/index.html", import.meta.url), "utf8");
  assert.match(html, /<html\s+lang=["']pt-BR["']/i);
  assert.match(html, /<title>FarmaHub Acadêmico<\/title>/i);
  assert.match(html, /FARMAHUB ACADÊMICO/);
  assert.match(html, /farmahub-logo\.png/);
  assert.doesNotMatch(html, /codex-preview/i);
});
