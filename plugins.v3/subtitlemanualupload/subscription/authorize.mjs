import { createHash, createPublicKey, randomBytes, randomUUID, timingSafeEqual, verify } from 'node:crypto';
import { createServer } from 'node:http';
import { existsSync, readFileSync, renameSync, writeFileSync } from 'node:fs';
import { join } from 'node:path';

const location = process.argv[2];
if (!location) throw new Error('需要提供权限受限的凭证目录。');

const issuer = 'https://auth.openai.com';
const resource = 'https://api.openai.com/v1';
const port = Number(process.argv[3] || 48761);
const origin = `http://127.0.0.1:${port}`;
const redirectUri = `${origin}/auth/callback`;
const scope = 'openid profile email offline_access resource.invoke chatgpt.tokens.use.direct';
const registrationPath = join(location, 'registration.json');
const credentialPath = join(location, 'credentials.json');
const registration = existsSync(registrationPath)
  ? JSON.parse(readFileSync(registrationPath, 'utf8'))
  : { host_id: `urn:uuid:${randomUUID()}` };

function saveJson(path, value) {
  const temporary = `${path}.${randomUUID()}.tmp`;
  writeFileSync(temporary, JSON.stringify(value), { flag: 'wx', mode: 0o600 });
  renameSync(temporary, path);
}

function render(response, status, message) {
  response.writeHead(status, {
    'Content-Type': 'text/html; charset=utf-8',
    'Cache-Control': 'no-store',
    'Referrer-Policy': 'no-referrer',
    'Content-Security-Policy': "default-src 'none'; base-uri 'none'; frame-ancestors 'none'",
  });
  response.end(`<!doctype html><html lang="zh"><title>AutoSubv3 授权</title><p>${message}</p></html>`);
}

function random() {
  return randomBytes(32).toString('base64url');
}

async function fetchJson(url, init) {
  const result = await fetch(url, { signal: AbortSignal.timeout(20_000), redirect: 'error', ...init });
  if (!result.ok) throw new Error(`OpenAI HTTP ${result.status}`);
  return result.json();
}

async function validateIdentity(token, clientId, nonce) {
  const [header, payload, signature, extra] = token.split('.');
  if (!header || !payload || !signature || extra !== undefined) throw new Error('ID token 格式无效');
  const fromPart = (data) => JSON.parse(Buffer.from(data, 'base64url').toString('utf8'));
  const { alg, kid } = fromPart(header);
  if (alg !== 'RS256' || !kid) throw new Error('ID token 签名算法无效');
  const keys = await fetchJson(`${issuer}/.well-known/jwks.json`);
  const jwk = keys.keys.find((key) => key.kid === kid && key.kty === 'RSA' && (!key.alg || key.alg === alg));
  if (!jwk || !verify('RSA-SHA256', Buffer.from(`${header}.${payload}`), createPublicKey({ key: jwk, format: 'jwk' }), Buffer.from(signature, 'base64url'))) {
    throw new Error('ID token 签名无效');
  }
  const claims = fromPart(payload);
  const now = Date.now() / 1000;
  const audiences = Array.isArray(claims.aud) ? claims.aud : [claims.aud];
  if (claims.iss !== issuer || !audiences.includes(clientId) ||
    ((audiences.length > 1 || claims.azp) && claims.azp !== clientId) ||
    !Number.isFinite(claims.exp) || claims.exp <= now || (claims.nbf !== undefined && claims.nbf > now + 30) ||
    claims.nonce !== nonce || typeof claims.sub !== 'string' || !claims.sub) {
    throw new Error('ID token 声明无效');
  }
  return claims.sub;
}

let pending;
let exchanging = false;
const server = createServer(async (request, response) => {
  if (request.method !== 'GET' || request.headers.host !== `127.0.0.1:${port}`) return render(response, 404, '地址无效。');
  const url = new URL(request.url, origin);
  if (url.pathname === '/start' && !exchanging) {
    if (!pending || pending.deadline < Date.now()) {
      pending = { state: random(), nonce: random(), verifier: random(), deadline: Date.now() + 15 * 60_000 };
    }
    const target = new URL(`${issuer}/api/accounts/authorize`);
    target.search = new URLSearchParams({
      client_id: registration.client_id || 'dynamic_agent_client',
      ext_agent_host_id: registration.host_id,
      response_type: 'code', redirect_uri: redirectUri, resource, scope,
      state: pending.state, nonce: pending.nonce,
      code_challenge_method: 'S256',
      code_challenge: createHash('sha256').update(pending.verifier).digest('base64url'),
      ...(registration.client_id ? {} : { agent_name_hint: 'MoviePilot AutoSubv3' }),
    });
    response.writeHead(302, { Location: target.href, 'Cache-Control': 'no-store', 'Referrer-Policy': 'no-referrer' });
    return response.end();
  }
  if (url.pathname !== '/auth/callback') return render(response, 404, '请打开授权入口。');
  const returnedState = Buffer.from(url.searchParams.get('state') || '');
  const expectedState = Buffer.from(pending?.state || '');
  if (!pending || pending.deadline < Date.now() || returnedState.length !== expectedState.length ||
    !timingSafeEqual(returnedState, expectedState)) return render(response, 400, '授权请求已失效，请重开授权入口。');

  const { nonce, verifier } = pending;
  pending = undefined;
  if (url.searchParams.has('error')) {
    console.log('authorization not granted');
    return render(response, 400, '未授予套餐使用权限。可以关闭此页。');
  }
  const code = url.searchParams.get('code');
  const returnedClient = url.searchParams.get('client_id');
  const clientId = registration.client_id || returnedClient;
  if (!code || !clientId?.startsWith('oaiapp_') || (returnedClient && returnedClient !== clientId)) {
    return render(response, 400, '授权响应缺少有效的注册信息。');
  }

  exchanging = true;
  try {
    const token = await fetchJson(`${issuer}/api/accounts/oauth/token`, {
      method: 'POST',
      body: new URLSearchParams({ grant_type: 'authorization_code', client_id: clientId, code,
        code_verifier: verifier, redirect_uri: redirectUri, resource }),
    });
    const granted = String(token.scope || '').split(/\s+/);
    if (!granted.includes('chatgpt.tokens.use.direct') || !token.refresh_token || !token.access_token ||
      !token.id_token || !Number.isFinite(token.expires_in) || token.expires_in <= 0) throw new Error('缺少套餐授权或续期凭证');
    const subject = await validateIdentity(token.id_token, clientId, nonce);
    if (registration.subject && registration.subject !== subject) throw new Error('授权账户与已有注册不一致');
    saveJson(registrationPath, { host_id: registration.host_id, client_id: clientId, subject });
    saveJson(credentialPath, {
      client_id: clientId, access_token: token.access_token, refresh_token: token.refresh_token,
      id_token: token.id_token, scope: token.scope, expires_at: Date.now() / 1000 + token.expires_in,
    });
    render(response, 200, 'ChatGPT 套餐已授权。可以关闭此页，回到 Codex。');
    console.log('authorization complete');
    server.close();
  } catch (error) {
    const message = error instanceof Error && /^OpenAI HTTP \d+$/.test(error.message) ? error.message : '验证或保存失败';
    console.log(`authorization failed: ${message}`);
    render(response, 502, '授权处理失败，请重开授权入口再试。');
  } finally {
    exchanging = false;
  }
});

server.listen(port, '127.0.0.1', () => console.log(`authorization listener ready ${origin}/start`));
setTimeout(() => server.close(), 25 * 60_000).unref();
