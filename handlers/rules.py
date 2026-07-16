"""Общие правила матчинга команд."""


def text_in(*variants: str):
    """Case-insensitive точное совпадение текста."""
    lowered = {v.strip().casefold() for v in variants}

    def checker(message) -> bool:
        text = (message.text or "").strip().casefold()
        return text in lowered

    return checker


def payload_cmd(*commands: str):
    """Совпадение payload.cmd."""
    wanted = set(commands)

    def checker(message) -> bool:
        payload = message.get_payload_json() or {}
        return isinstance(payload, dict) and payload.get("cmd") in wanted

    return checker


def match_cmd(cmd: str, *text_variants: str):
    """Кнопка (payload) или текст команды."""
    check_payload = payload_cmd(cmd)
    check_text = text_in(*text_variants) if text_variants else (lambda _m: False)

    def checker(message) -> bool:
        return check_payload(message) or check_text(message)

    return checker
