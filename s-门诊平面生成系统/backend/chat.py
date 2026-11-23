"""Translate a chat turn into one bounded edit to a reviewed design state."""

from copy import deepcopy

from chat_stream import stream_chat
from inputs import DesignError, number, validate_program


INSTRUCTION = (
    "Respond directly without a persona, role label, or self-introduction. For questions about the supplied room list, "
    "or clarification, start with the literal line TEXT followed by a newline and a concise Chinese reply. "
    "Use only supplied facts. Do not claim to have changed geometry or verified a layout. "
    "For design commands return only one JSON object instead. "
    "Only interpret the latest user message. Do not choose values that the user did not state, change constraints, "
    "produce geometric results, export, or write to Rhino. Allowed actions: "
    '{"action":"duplicate_room","room_id":"<existing ID>","count":1} for explicitly adding instances of an existing type; '
    '{"action":"set_area","room_id":"<existing ID>","min_area_m2":12,"max_area_m2":14} when the room and both '
    "area bounds are explicit (one exact value can be both bounds); "
    '{"action":"remove_room","room_id":"<existing ID>"} for a requested removal; '
    '{"action":"generate"} only for an explicit request to generate the unchanged current program; '
    '{"action":"clarify","message":"<one concise Chinese question>"} for meaningful ambiguity; '
    '{"action":"unsupported"} for edits not covered by these actions. '
    "If a request changes multiple distinct items, do not partially apply it. If room type alone identifies "
    "several rooms with the same area range, use any one as the template for duplication only."
)


def converse(get_config, source, publish):
    message = source.get("message")
    history = source.get("history", [])
    if not isinstance(message, str) or not message.strip() or len(message) > 2000:
        raise DesignError("单条消息最多 2,000 字。")
    if (not isinstance(history, list) or len(history) > 6 or
            any(not isinstance(turn, dict) or set(turn) != {"user", "assistant"} or
                any(not isinstance(value, str) or len(value) > 2000 for value in turn.values())
                for turn in history)):
        raise DesignError("最近对话的格式异常。")
    question = message.strip().rstrip("。！？.!?").strip().casefold()
    if question in {"你好", "您好", "嗨", "hello", "hi"}:
        answer = "你好！你想先讨论设计问题，还是从任务书开始整理房间清单？"
    elif question.removesuffix("呢") in {
        "你能做什么", "你可以做什么", "你会做什么", "你能帮我做什么", "你有什么功能",
        "有哪些功能", "功能介绍", "使用帮助", "怎么使用", "怎么用", "你能做些什么",
    }:
        answer = ("我可以和你讨论医院首层的功能分区、入口和流线，也可以根据任务书整理房间清单。"
                  "点「＋」添加任务书、选择建筑边界，核对清单后就能生成平面预览。"
                  "想先看效果，可以输入“生成示例”。")
    else:
        answer = None
    if answer:
        publish(answer)
        return {"action": "message", "message": answer}
    instruction = (
        "直接回答用户的问题，不使用助手身份或自我介绍。收到问候时简短回应；被问及功能时直接说明可执行的操作。可以讨论医院首层的功能分区、入口组织、人流与物流，"
        "根据最近对话理解追问。普通回复必须以单独一行 TEXT 开始，下一行写给用户的答复。"
        "遇到不明含义的短消息，友好地询问。你目前只能看到用户的聊天文字。"
        "仅当最新消息明确要求根据实际项目清单回答、修改或生成时，返回 JSON {\"action\":\"project\"}。"
        "明确要求读取任务书或拟定一份项目房间清单时，返回 JSON {\"action\":\"propose\"}。"
        "询问方法、举例或讨论设想时直接用 TEXT 回答。不要声称已访问或修改项目。"
    )
    reply = stream_chat(get_config(), instruction, {"message": message, "history": history}, publish)
    if reply.get("action") in ("project", "propose"):
        return {"action": reply["action"]}
    if reply.get("action") == "message" and isinstance(reply.get("message"), str) and reply["message"].strip():
        return {"action": "message", "message": reply["message"]}
    raise DesignError("聊天模型返回了无法识别的回复，请重试。")


def interpret(config, boundary, source, message, vocabulary, publish):
    if not isinstance(message, str) or not message.strip() or len(message) > 2000:
        raise DesignError("Provide a chat message with at most 2,000 characters")
    program = validate_program(source, vocabulary["types"], draft=True)
    rooms = [{label: room[label] for label in ("id", "type", "name", "min_area_m2", "max_area_m2")}
             for room in program["rooms"]]
    proposal = stream_chat(config, INSTRUCTION, {"message": message, "boundary_summary": boundary["summary"],
                                                 "rooms": rooms}, publish)
    if proposal.get("action") == "message" and isinstance(proposal.get("message"), str):
        return {"action": "message", "message": proposal["message"]}
    return apply_change(program, proposal, vocabulary["types"])


def apply_change(program, change, room_types):
    action = change.get("action")
    if action == "generate":
        return {"action": "generate"}
    if action == "clarify":
        question = change.get("message")
        return {"action": "message", "message": question[:220] if isinstance(question, str) and question.strip()
                else "请说明要修改的房间、数量或面积。"}
    if action not in ("duplicate_room", "set_area", "remove_room"):
        return {"action": "message", "message": "这条指令未改动方案。可对话增减已有类型的房间、修改面积，或打开清单修改其他约束。"}
    updated = deepcopy(program)
    rooms = updated["rooms"]
    original = next((room for room in rooms if room["id"] == change.get("room_id")), None)
    if original is None:
        return {"action": "message", "message": "没有找到要修改的房间。请说出房间名称或清单里的 ID。"}

    if action == "duplicate_room":
        count = change.get("count")
        if type(count) is not int or not 1 <= count <= 12 - len(rooms):
            return {"action": "message", "message": "请指定要增加几间房。当前 Demo 最多支持 12 间。"}
        used = {room["id"] for room in rooms}
        available = (f"R{index}" for index in range(1, 25) if f"R{index}" not in used)
        for _ in range(count):
            new_id = next(available)
            rooms.append({key: original[key] for key in ("name", "type", "min_area_m2", "max_area_m2")}
                         | {"id": new_id, "source": "chat_edit"})
        reply = f"草稿已增加 {count} 间{original['name']}，沿用原面积范围；没有更改其他房间或关系。"
    elif action == "set_area":
        original["min_area_m2"] = number(change.get("min_area_m2"), "minimum room area")
        original["max_area_m2"] = number(change.get("max_area_m2"), "maximum room area")
        reply = f"草稿已修改 {original['name']}（{original['id']}）的面积，其他要求保持不变。"
    else:
        room_id = original["id"]
        connected = any(room_id in pair for key in ("required_connections", "forbidden_connections", "optional_connections")
                        for pair in program[key])
        referenced = room_id == program["sight_target"] or any(room_id in (program[key] or [])
                                                                for key in ("patient_route", "staff_route"))
        if connected or referenced or len(rooms) <= 2:
            return {"action": "message", "message": "这个房间关联现有关系或评估端点，或清单已达最少房间数。请在清单里确认后再删除。"}
        rooms.remove(original)
        reply = f"草稿已移除 {original['name']}（{room_id}），没有更改其他要求。"
    return {"action": "revision", "message": reply, "draft": validate_program(updated, room_types, draft=True)}
