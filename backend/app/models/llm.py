from pydantic import BaseModel, Field
from typing import List, Literal, Optional
from datetime import datetime

class BirimUyumluluk(BaseModel):
    """
    Hastanın klinik ve vital tablosuna göre poliklinik / uzmanlık birimlerinin uyum analizi.
    """
    birim: str = Field(..., description="Hastane poliklinik / uzmanlık alanı adı")
    uyum_skoru: float = Field(..., ge=0.0, le=1.0, description="0.0 - 1.0 arası uyum skoru (1.0 en yüksek)")
    gerekce: str = Field(..., description="Bu birimin neden uygun görüldüğüne dair klinik açıklama")


class LLMTriageOutput(BaseModel):
    """
    Yapay Zekâ (Google Gemini) tarafından üretilen klinik karar ve triaj çıktısı.
    """
    Risk_Skoru: int = Field(..., ge=1, le=5, description="ESI Aciliyet Seviyesi (1: Hayatı Tehdit Eden, 5: Acil Değil)")
    Renk_Kodu: Literal["Kırmızı", "Sarı", "Yeşil"] = Field(..., description="Triaj Alan Renk Kodu")
    Onerilen_Poliklinik: str = Field(..., description="Birincil yönlendirilecek tıbbi uzmanlık alanı / poliklinik")
    Birim_Uyumluluk_Siralamasi: List[BirimUyumluluk] = Field(
        default_factory=list,
        description="Hastanın tablosuna en uyumludan başlayarak poliklinik/uzmanlık sıralaması"
    )
    Kritik_Bulgu: str = Field(..., description="Kararda etkili olan en kritik 1-2 bulgunun özeti")
    Erken_Uyari_Notu: str = Field(..., description="Hekim için 1 cümleyi geçmeyen erken uyarı notu")


class HastaneLogResponse(LLMTriageOutput):
    """
    5. Tablo olan HASTANE_LOG kaydının API yanıt modeli.
    4 tablonun ID'lerini bağlar ve triaj kararını tutar.
    """
    log_id: str = Field(..., description="Hastane master log / takip ID")
    demografi_id: str = Field(..., description="Kart 1 (Demografi) kayıt kodu")
    tibbi_gecmis_id: str = Field(..., description="Kart 2 (Tıbbi Geçmiş) kayıt kodu")
    vitaller_id: str = Field(..., description="Kart 3 (Vitaller) kayıt kodu")
    sikayet_id: str = Field(..., description="Kart 4 (Şikayet) kayıt kodu")
    
    tarih_saat: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    ai_provider: str = Field(default="Google-Gemini")
