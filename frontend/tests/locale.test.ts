import { strict as assert } from "node:assert";
import { test } from "node:test";
import { matchLocale, preferredLocale } from "../src/shared/i18n/locale";

test("saved languages take precedence over regional browser preferences", () => {
  assert.equal(preferredLocale("de", ["en-US"]), "de");
  assert.equal(preferredLocale(null, ["fr-FR", "en-GB", "de-DE"]), "en");
  assert.equal(matchLocale("DE-at"), "de");
});

test("invalid saved languages and unsupported browsers fall back predictably", () => {
  assert.equal(preferredLocale("garbage", ["en-AU"]), "en");
  assert.equal(preferredLocale(null, ["ja-JP"]), "de");
  assert.equal(preferredLocale(null, []), "de");
  assert.equal(matchLocale(""), undefined);
});
