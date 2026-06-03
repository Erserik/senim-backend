import re

_PHONE_RE = re.compile(r"^\+7\d{10}$")


def normalize_phone(raw: str | None) -> str | None:
    """Привести ввод к каноническому +7XXXXXXXXXX (КЗ). None — если не похоже на номер.

    10-значный ввод трактуется как локальный номер без кода страны и обязан
    начинаться с 7 (мобильные коды КЗ). Ввод вида «+7 + 9 цифр» неотличим от
    легитимного 10-значного 77X… — такая неоднозначность принята осознанно;
    фронтенд всегда шлёт полный +7XXXXXXXXXX.
    """
    digits = re.sub(r"\D", "", raw or "")
    if len(digits) == 10 and digits[0] == "7":
        digits = "7" + digits
    elif len(digits) == 11 and digits[0] in ("7", "8"):
        digits = "7" + digits[1:]
    else:
        return None
    candidate = f"+{digits}"
    return candidate if _PHONE_RE.fullmatch(candidate) else None
