"""Общие правила матчинга команд."""


def text_in(*variants: str):
    """Case-insensitive точное совпадение текста (без учёта регистра)."""
    lowered = {v.strip().lower() for v in variants}

    def checker(message) -> bool:
        text = (message.text or "").strip().lower()
        return text in lowered

    return checker
