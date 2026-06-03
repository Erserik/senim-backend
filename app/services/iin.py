"""Offline validation of Kazakhstan IIN (ИИН — Индивидуальный идентификационный номер).

Format: 12 digits.
  - digits[0:6]  — birthdate YYMMDD
  - digits[6]    — century + gender code (1=male XIX, 2=female XIX, 3=male XX, 4=female XX, 5=male XXI, 6=female XXI)
  - digits[7:11] — sequential registration number within a day
  - digits[11]   — checksum (ГОСТ РК algorithm)

Checksum algorithm:
  s1 = sum(digit[i] * weight1[i] for i in 0..10) mod 11
  if s1 < 10 → checksum = s1
  if s1 == 10 → retry with weight2
    s2 = sum(digit[i] * weight2[i] for i in 0..10) mod 11
    if s2 == 10 → IIN is considered invalid
    else → checksum = s2
"""

from __future__ import annotations

from datetime import date, datetime, timezone


WEIGHTS_1 = (1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11)
WEIGHTS_2 = (3, 4, 5, 6, 7, 8, 9, 10, 11, 1, 2)

MIN_AGE_YEARS = 18


class IinError(Exception):
    """Domain error for IIN validation failures."""

    def __init__(self, code: str, message: str):
        self.code = code
        self.message = message
        super().__init__(message)


def _checksum_ok(digits: list[int]) -> bool:
    s1 = sum(digits[i] * WEIGHTS_1[i] for i in range(11)) % 11
    if s1 < 10:
        return s1 == digits[11]
    s2 = sum(digits[i] * WEIGHTS_2[i] for i in range(11)) % 11
    if s2 == 10:
        return False
    return s2 == digits[11]


def _parse_birthdate(iin: str) -> tuple[date, bool]:
    """Return (birthdate, is_male). Raises IinError on bad century/gender code or invalid date."""
    yy = int(iin[0:2])
    mm = int(iin[2:4])
    dd = int(iin[4:6])
    cg = int(iin[6])
    if cg in (1, 2):
        year = 1800 + yy
    elif cg in (3, 4):
        year = 1900 + yy
    elif cg in (5, 6):
        year = 2000 + yy
    else:
        raise IinError("invalid_century", "Некорректный код века в ИИН")
    try:
        return date(year, mm, dd), cg in (1, 3, 5)
    except ValueError as ex:
        raise IinError("invalid_date", "Некорректная дата рождения в ИИН") from ex


def _age_years(birthday: date, today: date) -> int:
    years = today.year - birthday.year
    if (today.month, today.day) < (birthday.month, birthday.day):
        years -= 1
    return years


def validate_iin(raw: str) -> tuple[date, bool]:
    """Offline-check IIN. Returns (birthdate, is_male).

    Raises IinError with one of these codes:
      invalid_format   — not 12 digits
      invalid_checksum — ГОСТ РК checksum fails
      invalid_century  — century/gender code is 0 or 7..9
      invalid_date     — birthdate is not a real calendar date
      future_birthday  — birthday is in the future
      underage         — younger than MIN_AGE_YEARS
    """
    if not isinstance(raw, str) or len(raw) != 12 or not raw.isdigit():
        raise IinError("invalid_format", "ИИН должен состоять из 12 цифр")

    digits = [int(c) for c in raw]
    if not _checksum_ok(digits):
        raise IinError("invalid_checksum", "Неверная контрольная сумма ИИН")

    birthday, is_male = _parse_birthdate(raw)
    today = datetime.now(timezone.utc).date()
    if birthday > today:
        raise IinError("future_birthday", "Дата рождения в ИИН — в будущем")
    if _age_years(birthday, today) < MIN_AGE_YEARS:
        raise IinError("underage", f"Возраст должен быть не менее {MIN_AGE_YEARS} лет")

    return birthday, is_male
