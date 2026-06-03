import re

_PHONE_RE = re.compile(r"^\+7\d{10}$")


def normalize_phone(raw: str) -> str | None:
    """Привести ввод к каноническому +7XXXXXXXXXX (КЗ). None — если не похоже на номер."""
    digits = re.sub(r"\D", "", raw or "")
    if len(digits) == 10:
        digits = "7" + digits
    elif len(digits) == 11 and digits[0] in ("7", "8"):
        digits = "7" + digits[1:]
    else:
        return None
    candidate = f"+{digits}"
    return candidate if _PHONE_RE.fullmatch(candidate) else None
