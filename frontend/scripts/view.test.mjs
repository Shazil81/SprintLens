import assert from "node:assert/strict";
import test from "node:test";
import { build } from "esbuild";

const result = await build({
  entryPoints: ["src/hooks/useView.ts"],
  bundle: true,
  format: "esm",
  write: false,
  platform: "browser",
});
const { readView } = await import(
  `data:text/javascript;base64,${Buffer.from(result.outputFiles[0].text).toString("base64")}`
);

test("shared URLs restore sections and safely handle unknown destinations", () => {
  assert.equal(readView("#/tasks"), "Tasks");
  assert.equal(readView("#/profile"), "Profile");
  assert.equal(readView("#/audit-trail"), "Audit trail");
  assert.equal(readView("#/overview"), "Overview");
  assert.equal(readView(""), "Overview");
  assert.equal(readView("#/unknown"), "Overview");
  assert.equal(readView("#/%"), "Overview");
});
