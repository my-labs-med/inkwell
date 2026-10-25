import config from "./config.js";
import { base64url, challengeFor } from "./pkce.js";

const KEYS = { session: "inkwell.session", pkce: "inkwell.pkce" };

function randomString(size = 32) {
  return base64url(crypto.getRandomValues(new Uint8Array(size)));
}

function readJson(key) {
  try {
    return JSON.parse(sessionStorage.getItem(key));
  } catch {
    return null;
  }
}

function writeJson(key, value) {
  try {
    if (value === null) sessionStorage.removeItem(key);
    else sessionStorage.setItem(key, JSON.stringify(value));
  } catch {}
}

function decodeClaims(token) {
  try {
    const part = token.split(".")[1].replace(/-/g, "+").replace(/_/g, "/");
    const bytes = Uint8Array.from(atob(part), (ch) => ch.charCodeAt(0));
    return JSON.parse(new TextDecoder().decode(bytes));
  } catch {
    return {};
  }
}

export async function signIn() {
  const verifier = randomString(48);
  const state = randomString(16);
  writeJson(KEYS.pkce, { verifier, state });
  const params = new URLSearchParams({
    response_type: "code",
    client_id: config.clientId,
    redirect_uri: config.redirectUri,
    scope: config.scopes,
    state,
    code_challenge_method: "S256",
    code_challenge: await challengeFor(verifier),
  });
  window.location.assign(`${config.cognitoDomain}/oauth2/authorize?${params}`);
}

export async function handleCallback() {
  const url = new URL(window.location.href);
  const code = url.searchParams.get("code");
  if (!code) return false;
  const pending = readJson(KEYS.pkce);
  writeJson(KEYS.pkce, null);
  window.history.replaceState({}, "", url.pathname);
  if (!pending || pending.state !== url.searchParams.get("state")) return false;

  const response = await fetch(`${config.cognitoDomain}/oauth2/token`, {
    method: "POST",
    headers: { "Content-Type": "application/x-www-form-urlencoded" },
    body: new URLSearchParams({
      grant_type: "authorization_code",
      client_id: config.clientId,
      code,
      redirect_uri: config.redirectUri,
      code_verifier: pending.verifier,
    }),
  });
  if (!response.ok) return false;
  const tokens = await response.json();
  writeJson(KEYS.session, {
    idToken: tokens.id_token,
    expiresAt: Date.now() + tokens.expires_in * 1000,
  });
  return true;
}

export function token() {
  if (config.mock) return "mock";
  const session = readJson(KEYS.session);
  if (!session || session.expiresAt - 60000 < Date.now()) return null;
  return session.idToken;
}

export function profile() {
  if (config.mock) return { email: "you@example.com" };
  const current = token();
  return current ? decodeClaims(current) : null;
}

export function signOut() {
  writeJson(KEYS.session, null);
  if (config.mock) {
    window.location.reload();
    return;
  }
  const params = new URLSearchParams({ client_id: config.clientId, logout_uri: config.redirectUri });
  window.location.assign(`${config.cognitoDomain}/logout?${params}`);
}
