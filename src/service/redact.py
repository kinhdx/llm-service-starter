"""Masks personal identifiers before text is sent to a model or written to a log.

Covered: card numbers (13-19 digits passing the Luhn check), citizen ID numbers (12 digits) and old ID card
numbers (9 digits), Vietnamese mobile numbers, e-mail addresses, and account numbers written after an
account label ("STK", "số tài khoản"). Each match is replaced by a typed placeholder such as [PHONE], so the
model still knows what kind of value was there.

Order matters: card numbers are matched before plain digit runs so a 16-digit card is not split into an
ID number and a remainder.
"""
from __future__ import annotations

import re
from collections import Counter
from dataclasses import dataclass, field

_CARD = re.compile(r"(?<!\d)(?:\d[ -]?){12,18}\d(?!\d)")
_ACCOUNT = re.compile(r"(?i)\b(stk|số tài khoản|so tai khoan|tài khoản số|account)\s*[:#]?\s*(\d[\d ]{5,18}\d)")
_EMAIL = re.compile(r"\b[\w.+-]+@[\w-]+(?:\.[\w-]+)+\b")
_PHONE = re.compile(r"(?<!\d)(?:\+84|0084|0)(?:[\s.]?\d){9}(?!\d)")
_CITIZEN_ID = re.compile(r"(?<!\d)\d{12}(?!\d)")
_OLD_ID = re.compile(r"(?<!\d)\d{9}(?!\d)")


@dataclass
class Redacted:
    text: str
    counts: Counter = field(default_factory=Counter)


def luhn_ok(digits: str) -> bool:
    total, parity = 0, len(digits) % 2
    for i, ch in enumerate(digits):
        d = int(ch)
        if i % 2 == parity:
            d = d * 2 - 9 if d > 4 else d * 2
        total += d
    return total % 10 == 0


def redact(text: str) -> Redacted:
    counts: Counter = Counter()

    def card(m: re.Match) -> str:
        digits = re.sub(r"\D", "", m.group())
        if 13 <= len(digits) <= 19 and luhn_ok(digits):
            counts["CARD"] += 1
            return "[CARD]"
        return m.group()

    def account(m: re.Match) -> str:
        counts["ACCOUNT"] += 1
        return f"{m.group(1)} [ACCOUNT]"

    def typed(label: str):
        def replace(m: re.Match) -> str:
            counts[label] += 1
            return f"[{label}]"
        return replace

    text = _CARD.sub(card, text)
    text = _ACCOUNT.sub(account, text)
    text = _EMAIL.sub(typed("EMAIL"), text)
    text = _PHONE.sub(typed("PHONE"), text)
    text = _CITIZEN_ID.sub(typed("ID_NUMBER"), text)
    text = _OLD_ID.sub(typed("ID_NUMBER"), text)
    return Redacted(text, counts)
