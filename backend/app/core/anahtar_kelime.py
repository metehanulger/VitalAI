"""Keyword matching for triage rules and department routing.

Text is expected to be folded with ``katla`` (Turkish letters to ASCII, lower case).

- Turkish keywords match at a word start, so suffixed forms count ("kanamasi").
- English keywords must be whole words with an optional English ending, so "burn"
  does not match the Turkish word "burnum" (my nose).
- A keyword is ignored when a negation clearly belongs to it. Turkish negates after
  the symptom ("gogus agrisi yok"), English before it ("no chest pain"). The check
  is conservative: when in doubt, the keyword still counts.
- A few Turkish word forms that merely start like a symptom keyword are excluded
  (for example "inmek", to get off, versus "inme", stroke).
"""

import re
from typing import Iterable

_OLUMSUZLAR_SONRA = frozenset({
    "yok", "yoktur", "degil", "degildir", "olmadi", "olmuyor", "olmamis",
    "yasamadim", "yasamadi", "yasamiyor", "yasamiyorum", "hissetmiyor", "hissetmiyorum",
    "gecirmedi", "gecirmedim",
})
_OLUMSUZLAR_ONCE = frozenset({"no", "not", "denies", "denied", "without", "never", "negative"})
_CUMLE_SINIRI = re.compile(r"[.,;:!?\n]|\b(?:ama|ancak|fakat|lakin|ve|veya|ile|but|and|or|however)\b")
_KELIME = re.compile(r"\w+")

# Whole words that begin like a keyword but mean something else. Only unambiguous
# forms are listed; ambiguous ones (for example "inmeye") keep counting.
YANLIS_POZITIF_KELIMELER = frozenset({
    "inmek", "inmeden", "inmedi", "inmedim", "inmeliyim", "inmekte",
    "nobetci", "nobetcisi", "nobetciyim", "nobetteydim",
    "bayilmadim", "bayilmadi", "bayilmiyor", "bayilmiyorum",
    "kirikkale",
})
# Multi-word forms where a keyword is clearly a different word ("inmeye calisirken",
# trying to get off). Checked against the text that starts at the match.
YANLIS_POZITIF_IFADELER = ("inmeye calis", "inmeye cal", "inerken")


def desen(turkce: Iterable[str], ingilizce: Iterable[str] = ()) -> re.Pattern:
    """Compile Turkish and English keywords into one pattern, longest terms first."""
    def _secenekler(terimler: Iterable[str]) -> str:
        return "|".join(re.escape(t) for t in sorted(set(terimler), key=len, reverse=True))

    parcalar = []
    tr, en = _secenekler(turkce), _secenekler(ingilizce)
    if tr:
        parcalar.append(r"\b(?:" + tr + ")")
    if en:
        parcalar.append(r"\b(?:" + en + r")(?:s|es|d|ed|ing)?\b")
    return re.compile("|".join(parcalar) or r"(?!x)x")


def olumsuzlanmis(metin: str, bas: int, son: int) -> bool:
    """Return True when the keyword at metin[bas:son] is explicitly negated."""
    sonrasi = metin[son:]
    sinir = _CUMLE_SINIRI.search(sonrasi)
    for kelime in _KELIME.findall(sonrasi[: sinir.start()] if sinir else sonrasi)[:3]:
        if kelime == "var":
            break
        if kelime in _OLUMSUZLAR_SONRA:
            return True

    oncesi = metin[:bas]
    sinirlar = list(_CUMLE_SINIRI.finditer(oncesi))
    if sinirlar:
        oncesi = oncesi[sinirlar[-1].end():]
    return any(kelime in _OLUMSUZLAR_ONCE for kelime in _KELIME.findall(oncesi)[-2:])


def _gecerli(metin: str, eslesme: re.Match) -> bool:
    kelime = _KELIME.match(metin, eslesme.start())
    if kelime and kelime.group() in YANLIS_POZITIF_KELIMELER:
        return False
    if metin.startswith(YANLIS_POZITIF_IFADELER, eslesme.start()):
        return False
    return not olumsuzlanmis(metin, eslesme.start(), eslesme.end())


def eslesme_sayisi(metin: str, desen_: re.Pattern) -> int:
    """Count keyword matches that are neither negated nor known false positives."""
    return sum(1 for m in desen_.finditer(metin) if _gecerli(metin, m))


def terim_var(metin: str, desen_: re.Pattern) -> bool:
    """True when the text contains at least one valid keyword match."""
    return any(_gecerli(metin, m) for m in desen_.finditer(metin))
