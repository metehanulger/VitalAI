_TURKCE_ASCII = str.maketrans("çğıİöşüÇĞÖŞÜ", "cgiIosuCGOSU")


def katla(metin: str) -> str:
    """Türkçe karakterleri ASCII'ye çevirip küçük harfe indirir ("Göğüs AĞRISI" -> "gogus agrisi")."""
    return metin.translate(_TURKCE_ASCII).lower()


def bayt_kirp(metin: str, azami_bayt: int) -> str:
    """Metni UTF-8 bayt sınırına göre keser (DB2 VARCHAR uzunluğu bayttır)."""
    return metin.encode("utf-8")[:azami_bayt].decode("utf-8", errors="ignore")
