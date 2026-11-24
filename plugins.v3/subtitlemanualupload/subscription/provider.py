from __future__ import annotations

import hmac
import json
import os
import secrets
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from uuid import uuid4

import httpx
from quality import quality_request


API = 'https://api.openai.com/v1'
TOKEN_ENDPOINT = 'https://auth.openai.com/api/accounts/oauth/token'
PLAN_SCOPE = 'chatgpt.tokens.use.direct'
ALIAS = 'chatgpt-subscription'
PREFERRED_MODELS = ('gpt-6.1-sol', 'gpt-5.4-mini', 'gpt-5.4', 'gpt-5.5')
MAX_REQUEST_BYTES = 4 * 1024 * 1024


class ProviderError(Exception):
    def __init__(self, status: int, message: str):
        super().__init__(message)
        self.status = status


def replace_private_file(path: Path, contents: str) -> None:
    temporary = path.with_name(f'.{path.name}.{uuid4().hex}.tmp')
    fd = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    try:
        with os.fdopen(fd, 'w', encoding='utf-8') as stream:
            stream.write(contents)
            stream.flush()
            os.fsync(stream.fileno())
        temporary.replace(path)
    finally:
        temporary.unlink(missing_ok=True)


def check_upstream(response: httpx.Response, action: str) -> None:
    if response.is_success:
        return
    status = response.status_code if response.status_code in (401, 403, 429) else 502
    raise ProviderError(status, f'ChatGPT {action}失败（HTTP {response.status_code}）')


class ChatGPTPlan:
    def __init__(self, directory: Path, http: httpx.Client):
        self.credentials = directory / 'credentials.json'
        self.http = http
        self.lock = threading.Lock()
        self.model = None

    def access_token(self) -> str:
        with self.lock:
            try:
                credentials = json.loads(self.credentials.read_text(encoding='utf-8'))
                if not isinstance(credentials, dict) or PLAN_SCOPE not in credentials['scope'].split():
                    raise ValueError('scope')
            except (FileNotFoundError, KeyError, TypeError, ValueError, AttributeError) as error:
                raise ProviderError(503, '请先完成 ChatGPT 套餐授权') from error
            if credentials['expires_at'] > time.time() + 60:
                return credentials['access_token']

            result = self.http.post(TOKEN_ENDPOINT, data={
                'grant_type': 'refresh_token', 'client_id': credentials['client_id'],
                'refresh_token': credentials['refresh_token'], 'resource': API,
            })
            if result.status_code == 400:
                raise ProviderError(401, 'ChatGPT 套餐授权需要重新登录')
            check_upstream(result, '续期')
            refreshed = result.json()
            scope = refreshed.get('scope', credentials['scope'])
            if (not refreshed.get('access_token') or not refreshed.get('refresh_token') or
                    PLAN_SCOPE not in scope.split() or not isinstance(refreshed.get('expires_in'), (int, float)) or
                    refreshed['expires_in'] <= 0):
                raise ProviderError(502, 'ChatGPT 续期响应不完整')
            credentials.update(access_token=refreshed['access_token'], refresh_token=refreshed['refresh_token'],
                               expires_at=time.time() + refreshed['expires_in'], scope=scope)
            replace_private_file(self.credentials, json.dumps(credentials))
            return credentials['access_token']

    def choose_model(self, token: str) -> str:
        with self.lock:
            if self.model:
                return self.model
            result = self.http.get(f'{API}/models', headers={'Authorization': f'Bearer {token}'})
            check_upstream(result, '读取模型列表')
            catalog = [item['slug'] for item in result.json().get('models', [])
                       if item.get('visibility') == 'list' and isinstance(item.get('slug'), str)]
            model = next((name for name in PREFERRED_MODELS if name in catalog), None)
            if model is None:
                model = next((name for name in catalog if name.startswith('gpt-') and
                              not any(tag in name for tag in ('codex', 'spark', 'audio', 'realtime'))), None)
            if model is None:
                raise ProviderError(503, '该 ChatGPT 账户没有可用于字幕翻译的文本模型')
            self.model = model
            return model

    def translate(self, messages: list[dict]) -> tuple[str, str, dict]:
        instructions = []
        inputs = []
        for message in messages:
            if not isinstance(message, dict) or not isinstance(message.get('content'), str):
                raise ProviderError(400, '字幕线路只接受文本消息')
            role = message.get('role')
            if role in ('system', 'developer'):
                instructions.append(message['content'])
            elif role in ('user', 'assistant'):
                inputs.append({'role': role, 'content': message['content']})
            else:
                raise ProviderError(400, '字幕消息角色无效')
        if not any(item['role'] == 'user' for item in inputs):
            raise ProviderError(400, '缺少待翻译文本')

        token = self.access_token()
        model = self.choose_model(token)
        payload = {'model': model, 'input': inputs, 'store': False, 'stream': True}
        if instructions:
            payload['instructions'] = '\n\n'.join(instructions)
        with self.http.stream('POST', f'{API}/responses', json=payload,
                              headers={'Authorization': f'Bearer {token}', 'Accept': 'text/event-stream'}) as result:
            check_upstream(result, '翻译')
            segments = []
            for line in result.iter_lines():
                if not line.startswith('data:') or line[5:].strip() in ('', '[DONE]'):
                    continue
                event = json.loads(line[5:])
                kind = event.get('type')
                if kind == 'response.output_text.delta':
                    segments.append(event['delta'])
                elif kind in ('error', 'response.failed', 'response.incomplete'):
                    raise ProviderError(502, 'ChatGPT 未完成翻译请求')
                elif kind == 'response.completed':
                    text = ''.join(segments)
                    if text.strip():
                        return text, model, event['response'].get('usage') or {}
                    break
        raise ProviderError(502, 'ChatGPT 未返回完整翻译正文')


def serve(directory: Path, port: int = 18743) -> None:
    if not (directory / 'bridge.key').exists():
        replace_private_file(directory / 'bridge.key', secrets.token_urlsafe(32))
    key = (directory / 'bridge.key').read_text(encoding='utf-8').strip()
    if len(key) < 32:
        raise RuntimeError('字幕线路密钥无效')
    client = httpx.Client(timeout=httpx.Timeout(100.0, connect=8.0), follow_redirects=False)
    plan = ChatGPTPlan(directory, client)

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *_args):
            pass

        def send_json(self, status, payload):
            raw = json.dumps(payload, ensure_ascii=False).encode('utf-8')
            self.send_response(status)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Cache-Control', 'no-store')
            self.send_header('Content-Length', str(len(raw)))
            self.end_headers()
            self.wfile.write(raw)

        def failure(self, status, message):
            self.send_json(status, {'error': {'message': message, 'type': 'chatgpt_subscription_error'}})

        def authorized(self):
            supplied = self.headers.get('Authorization', '').encode('utf-8')
            if hmac.compare_digest(supplied, f'Bearer {key}'.encode('utf-8')):
                return True
            self.failure(401, '字幕线路未授权')
            return False

        def do_GET(self):
            if self.path == '/healthz':
                self.send_json(200, {'status': 'ready' if plan.credentials.is_file() else 'awaiting_login',
                                     'model': plan.model})
            elif self.path == '/v1/models':
                if self.authorized():
                    self.send_json(200, {'object': 'list', 'data': [
                        {'id': ALIAS, 'object': 'model', 'created': 0, 'owned_by': 'local'},
                    ]})
            else:
                self.failure(404, '字幕线路地址无效')

        def do_POST(self):
            if self.path not in ('/v1/chat/completions', '/v1/subtitle'):
                return self.failure(404, '字幕线路地址无效')
            if not self.authorized():
                return None
            try:
                self.connection.settimeout(12)
                size = int(self.headers.get('Content-Length', '0'))
                if not 0 < size <= MAX_REQUEST_BYTES:
                    raise ProviderError(413, '字幕请求大小无效')
                body = json.loads(self.rfile.read(size))
                if self.path == '/v1/subtitle':
                    result = quality_request(plan, body, API, check_upstream, ProviderError)
                    return self.send_json(200, result)
                if not isinstance(body, dict) or body.get('model') != ALIAS or not isinstance(body.get('messages'), list):
                    raise ProviderError(400, '字幕请求缺少有效的模型或消息')
                if body.get('stream') or body.get('tools'):
                    raise ProviderError(400, '字幕线路只接受非流式文本请求')
                self.connection.settimeout(120)
                text, model, usage = plan.translate(body['messages'])
            except ProviderError as error:
                return self.failure(error.status, str(error))
            except (ValueError, UnicodeError):
                return self.failure(400, '字幕请求或上游响应格式无效')
            except (httpx.RequestError, OSError, KeyError, TypeError):
                return self.failure(502, '连接 ChatGPT 字幕线路失败')

            self.send_json(200, {
                'id': f'chatcmpl-{uuid4().hex}', 'object': 'chat.completion', 'created': int(time.time()), 'model': model,
                'choices': [{'index': 0, 'finish_reason': 'stop', 'message': {'role': 'assistant', 'content': text}}],
                'usage': {'prompt_tokens': usage.get('input_tokens', 0), 'completion_tokens': usage.get('output_tokens', 0),
                          'total_tokens': usage.get('total_tokens', 0)},
            })
            print(f'ChatGPT 套餐翻译完成：{model}', flush=True)

    with ThreadingHTTPServer(('127.0.0.1', port), Handler) as server:
        print('ChatGPT 字幕线路已就绪', flush=True)
        server.serve_forever()


if __name__ == '__main__':
    serve(Path('/state'))
