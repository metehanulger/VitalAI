_TURKCE_ASCII = str.maketrans("çğıİöşüÇĞÖŞÜ", "cgiIosuCGOSU")


def katla(metin: str) -> str:
    """Convert Turkish characters to ASCII and lowercase the text."""
    return metin.translate(_TURKCE_ASCII).lower()


def bayt_kirp(metin: str, azami_bayt: int) -> str:
    """Truncate text to a UTF-8 byte limit (DB2 VARCHAR length is measured in bytes)."""
    return metin.encode("utf-8")[:azami_bayt].decode("utf-8", errors="ignore")
