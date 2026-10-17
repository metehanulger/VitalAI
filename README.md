# Ön Triaj Uygulaması

React (Vite) frontend + FastAPI backend + IBM DB2 + IBM watsonx.ai.

## Veri akışı

```
Triaj Ekranı (4 kart)  ──POST /api/triage──▶  Backend
                                               ├─ Kural motoru (NEWS2 + kritik eşikler + anahtar kelimeler)
                                               ├─ watsonx.ai (isteğe bağlı; yalnızca aciliyeti YÜKSELTEBİLİR)
                                               └─ DB2: tek transaction
                                                    HASTA_DEMOGRAFI ─┐
                                                    TIBBI_GECMIS    ─┤ ID'leri ─▶ HASTANE_LOG
                                                    ANLIK_VITALLER  ─┤           (+ hasta durumu, tarih,
                                                    SIKAYET         ─┘            saat, sıra no)
Sonuç Ekranı  ◀── {log_id, sira_no, hasta_durumu, aciklama, kodlar, ...}
```

| Tablo | Kart | Alanlar |
|---|---|---|
| `HASTA_DEMOGRAFI` | 1 Temel Demografi | isim, yaş, boy, kilo, kan grubu, kimlik türü (TC/PASAPORT), kimlik no |
| `TIBBI_GECMIS` | 2 Tıbbi Geçmiş | kronik rahatsızlık, sürekli ilaç |
| `ANLIK_VITALLER` | 3 Anlık Vitaller | nabız, tansiyon (sistolik/diastolik), solunum, ateş, SpO2 |
| `SIKAYET` | 4 Şikayet | ana şikayet, ağrı skalası (1-10) |
| `HASTANE_LOG` | — | 4 kartın ID'leri, hasta durumu (KIRMIZI/SARI/YESIL), açıklama, karar kaynağı, tarih, saat, sıra no |

Şemanın kaynağı [database/init.sql](database/init.sql). Sıra no her gün 1'den başlar.

## Kurulum

### Docker ile (DB2 + backend)

```bash
cp backend/.env.example backend/.env   # watsonx anahtarlarını buraya girin (isteğe bağlı)
docker compose up --build
```

İlk açılışta DB2 kurulumu 5-10 dakika sürer. Backend, DB2'de tablolar oluşunca başlar.
API: http://localhost:8000 — Swagger arayüzü: http://localhost:8000/docs

### Yerel geliştirme (DB2'siz, SQLite ile)

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate            # macOS/Linux: source .venv/bin/activate
pip install -r requirements-dev.txt
cp .env.example .env
uvicorn app.main:app --reload
```

Testler: `pytest` (backend klasöründe).

watsonx anahtarları boşsa backend yalnızca kural tabanlı triaj yapar. watsonx yanıt vermezse
(`WATSONX_TIMEOUT` saniye) yine kural sonucu kullanılır.

## API (frontend için)

Frontend `.env`: `VITE_API_URL=http://localhost:8000`

| Metot | Yol | Açıklama |
|---|---|---|
| `POST` | `/api/triage` | 4 kartı gönderir, triaj sonucu döner (201) |
| `GET` | `/api/triage?tarih=YYYY-MM-DD&durum=KIRMIZI` | Günün bekleme listesi: önce KIRMIZI, sonra SARI, YESIL |
| `GET` | `/api/triage/{log_id}` | Kayıt + 4 kartın tamamı (kimlik no maskeli) |
| `PATCH` | `/api/triage/{log_id}` | Personelin durumu elle değiştirmesi: `{"hasta_durumu": "SARI", "aciklama": "..."}` |
| `GET` | `/api/triage/secenekler` | Açılır listeler: kan grupları, kimlik türleri, durumlar |
| `GET` | `/api/health` | `{"durum", "veritabani", "watsonx"}` |

### `POST /api/triage` isteği

```json
{
  "demografi": {
    "isim": "Ayşe Yılmaz", "yas": 34, "boy": 165, "kilo": 60.5,
    "kan_grubu": "A+", "kimlik_turu": "TC", "kimlik_no": "10000000146"
  },
  "tibbi_gecmis": { "kronik_rahatsizlik": "Astım", "surekli_ilac": "" },
  "vitaller": {
    "nabiz": 78, "tansiyon_sistolik": 120, "tansiyon_diastolik": 80,
    "solunum": 16, "ates": 36.8, "spo2": 98
  },
  "sikayet": { "ana_sikayet": "Boğaz ağrısı", "agri_skalasi": 3 }
}
```

- `boy`, `kilo` isteğe bağlı; `kan_grubu` boşsa `BILINMIYOR`. `O+` yazımı `0+` olarak kaydedilir.
- TC kimlik no algoritmayla doğrulanır; pasaport 5-20 harf/rakam.
- Sınırlar: nabız 20-300, sistolik > diastolik, solunum 4-80, ateş 25-45, SpO2 30-100, ağrı 1-10.

### Yanıt (201)

```json
{
  "log_id": 12, "sira_no": 7, "tarih": "2026-10-17", "saat": "15:42:10",
  "hasta_durumu": "YESIL",
  "aciklama": "Kural tabanlı değerlendirmede kritik bulgu yok (NEWS2=0).",
  "karar_kaynagi": "KURAL",
  "kodlar": { "demografi_id": 12, "tibbi_gecmis_id": 12, "vitaller_id": 12, "sikayet_id": 12 }
}
```

`karar_kaynagi`: `KURAL`, `WATSONX` (model daha acil buldu), `KURAL+WATSONX` (ikisi aynı), `MANUEL`.

### Hatalar

- `422`: Form doğrulama hatası. `detail[].loc` alanı hangi kartın hangi alanı olduğunu gösterir,
  örn. `["body", "vitaller", "spo2"]`.
- `404`: Kayıt yok. `503`: Veritabanına ulaşılamıyor.
