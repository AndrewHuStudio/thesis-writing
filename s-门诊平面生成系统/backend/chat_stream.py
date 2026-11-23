"""Stream user-facing replies while buffering structured edits until complete."""

import json
from urllib.error import HTTPError, URLError
from urllib.request import build_opener

from ai import NoRedirect, request_model
from inputs import DesignError


def content_chunks(response):
    if response.headers.get_content_type() == "application/json":
        choice = json.load(response)["choices"][0]
        if choice.get("finish_reason") != "stop":
            raise DesignError("模型回复未完整返回。")
        yield choice["message"]["content"]
        return
    stopped = False
    data = []
    for line in response:
        line = line.decode("utf-8").rstrip("\r\n")
        if line.startswith("data:"):
            data.append(line[5:].lstrip(" "))
        if line or not data:
            continue
        event = "\n".join(data)
        data.clear()
        if event == "[DONE]":
            break
        packet = json.loads(event)
        if "error" in packet:
            raise DesignError("模型服务中断了本次回复。")
        for choice in packet.get("choices", []):
            if choice.get("index", 0) != 0:
                continue
            chunk = choice["delta"].get("content")
            if chunk:
                yield chunk
            reason = choice.get("finish_reason")
            if reason is not None:
                if reason != "stop":
                    raise DesignError("模型回复未完整返回。")
                stopped = True
    if not stopped:
        raise DesignError("模型回复中断，请重试。")


def read_reply(chunks, publish):
    # A fixed first line separates conversational text from the private edit JSON.
    prefix = "TEXT\n"
    buffer = ""
    visible = None
    for chunk in chunks:
        if visible is not None:
            visible.append(chunk)
            publish(chunk)
            continue
        buffer += chunk
        trimmed = buffer.lstrip().replace("\r\n", "\n", 1)
        if trimmed.startswith(prefix):
            body = trimmed[len(prefix):]
            visible = [body]
            if body:
                publish(body)
    if visible is not None:
        message = "".join(visible)
        if not message.strip():
            raise DesignError("模型返回了空回复。")
        return {"action": "message", "message": message}
    raw = buffer.strip()
    if raw.startswith("```") and raw.endswith("```"):
        raw = raw.split("\n", 1)[-1][:-3].strip()
    if raw and not raw.startswith(("{", "[", "`")):
        # Some providers omit the TEXT line for a short conversational answer.
        message = raw.removeprefix("TEXT").lstrip() if raw.startswith(("TEXT ", "TEXT：", "TEXT:")) else raw
        message = message.lstrip("：:").strip()
        if not message:
            raise DesignError("模型返回了空回复。")
        publish(message)
        return {"action": "message", "message": message}
    action = json.loads(raw)
    if not isinstance(action, dict):
        raise ValueError("Expected an action")
    return action


def stream_chat(config, instruction, data, publish):
    request = request_model(config, instruction, data, stream=True)
    try:
        with build_opener(NoRedirect()).open(request, timeout=70) as response:
            return read_reply(content_chunks(response), publish)
    except HTTPError as exc:
        raise DesignError(f"模型服务返回 HTTP {exc.code}。") from None
    except (URLError, TimeoutError, ConnectionError) as exc:
        if isinstance(getattr(exc, "reason", exc), TimeoutError):
            raise DesignError("等待模型服务响应超时，请重新发送这条消息。") from None
        raise DesignError("模型服务连接失败，请检查网络或代理后重试。") from None
    except DesignError:
        raise
    except (ValueError, KeyError, IndexError, TypeError, AttributeError):
        raise DesignError("模型回复格式异常，请重试。") from None
