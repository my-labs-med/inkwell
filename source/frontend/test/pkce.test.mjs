import assert from "node:assert/strict";
import { test } from "node:test";

import { base64url, challengeFor } from "../js/pkce.js";

test("S256 challenge matches the RFC 7636 test vector", async () => {
  const verifier = "dBjftJeZ4CVP-mB92K27uhbUJU1p1r_wW1gFWFOEjXk";
  assert.equal(await challengeFor(verifier), "E9Melhoa2OwvFrEMTJguCHaoeK1t8URWbuGJSstw-cM");
});

test("base64url has no padding or unsafe characters", () => {
  assert.equal(base64url(new Uint8Array([251, 255, 254])), "-__-");
});
