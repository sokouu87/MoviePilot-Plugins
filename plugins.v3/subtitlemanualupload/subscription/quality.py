"""订阅精翻接口。从流事件记录实际完成的网页检索及引用。"""
import json
from urllib.parse import urlsplit


def response_text(response, require_search):
    pieces, messages, sources = [], [], []
    searched = completed = False

    def collect(item):
        nonlocal searched
        if item.get("type") == "web_search_call" and item.get("status") == "completed":
            searched = True
            action = item.get("action") or {}
            if action.get("type") == "open_page":
                sources.append(action.get("url"))
        if item.get("type") == "message" and item.get("role") == "assistant" and item.get("phase") != "commentary":
            segments = []
            for part in item.get("content", []):
                if part.get("type") == "output_text":
                    segments.append(part["text"])
                    sources.extend(a.get("url") for a in part.get("annotations", []) if a.get("type") == "url_citation")
            if segments:
                messages.append("".join(segments))

    for line in response.iter_lines():
        if not line.startswith("data:") or line[5:].strip() in ("", "[DONE]"):
            continue
        event = json.loads(line[5:])
        kind = event.get("type")
        if kind in ("error", "response.failed", "response.incomplete"):
            raise ValueError("订阅未完成推理，请检查模型额度并重试")
        if kind == "response.output_item.done":
            collect(event["item"])
        elif kind == "response.output_text.delta":
            pieces.append(event["delta"])
        elif kind == "response.completed":
            body = event["response"]
            if body.get("status") != "completed":
                raise ValueError("订阅返回了未完成的响应")
            for item in body.get("output", []):
                collect(item)
            completed = True
            break

    text = messages[-1] if messages else "".join(pieces)
    urls = list(dict.fromkeys(u for u in sources if isinstance(u, str) and urlsplit(u).scheme in ("http", "https") and urlsplit(u).hostname))
    if not completed or not text.strip():
        raise ValueError("未收到完整的模型正文")
    if require_search and not (searched and urls):
        raise ValueError("本次调研缺少已完成的网页搜索或真实网页来源")
    return {"text": text, "sources": urls}


def quality_request(plan, body, api, check, error):
    if not isinstance(body, dict):
        raise error(400, "精翻请求格式不对")
    model = body.get("model", "")
    effort = body.get("effort", "high")
    if not isinstance(model, str) or not model.startswith("gpt-") or len(model) > 80 or effort not in ("medium", "high", "xhigh"):
        raise error(400, "模型名或推理档位无效")
    if not all(isinstance(body.get(k), str) and body[k].strip() for k in ("instructions", "input")):
        raise error(400, "缺少字幕任务说明或内容")
    search, schema = body.get("search"), body.get("schema")
    if not isinstance(search, bool) or (search and schema is not None) or (not search and not isinstance(schema, dict)):
        raise error(400, "请选择联网调研或严格结构化输出")
    payload = {"model": model, "store": False, "stream": True, "instructions": body["instructions"],
               "input": [{"role": "user", "content": body["input"]}], "reasoning": {"effort": effort}}
    if search:
        payload.update(tools=[{"type": "web_search"}], tool_choice="required", include=["web_search_call.action.sources"])
    else:
        payload["text"] = {"format": {"name": "subtitle_result", "type": "json_schema", "strict": True, "schema": schema}}
    token = plan.access_token()
    with plan.http.stream("POST", api + "/responses", headers={"Authorization": "Bearer " + token, "Accept": "text/event-stream"},
                          json=payload, timeout=480) as response:
        check(response, "精翻")
        try:
            return response_text(response, search)
        except ValueError as exc:
            raise error(502, str(exc)) from exc
