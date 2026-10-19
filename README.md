<div align="center">

# VitialAI · Ön Triaj ve Poliklinik Yönlendirme

**Hasta kabul bilgilerini değerlendirir, öncelik seviyesini belirler ve günlük triaj kuyruğunu yönetir.**

React arayüzü · FastAPI servisi · SQLite, PostgreSQL veya IBM Db2

</div>

<p align="center">
  <a href="#proje-hakkında">Proje</a> ·
  <a href="#hızlı-başlangıç">Kurulum</a> ·
  <a href="#yapılandırma">Yapılandırma</a> ·
  <a href="#api-özeti">API</a> ·
  <a href="#yerel-ml-modellerini-eğitme-isteğe-bağlı">ML modelleri</a>
</p>

## Proje hakkında

VitialAI, acil servise başvuran kişiler için bir **ön triaj demonstrasyonudur**. Demografi, tıbbi geçmiş, yaşamsal bulgular ve ana şikâyet bilgilerini toplar; NEWS2 temelli kurallar, isteğe bağlı makine öğrenmesi modelleri ve yapılandırılmış bir LLM sağlayıcısından gelen çıktıları bir araya getirir.

Sonuç; renk kodlu durum, 1–5 arası aciliyet seviyesi, önerilen poliklinik ve açıklama içerir. Sonuçlar veritabanına kaydedilir ve günlük kuyrukta görüntülenir. LLM veya yerel modeller kullanılabilir olmadığında sistem kural tabanlı değerlendirmeyle çalışmaya devam eder.

> **Klinik kullanım uyarısı:** Bu proje eğitim ve yazılım demonstrasyonu içindir; teşhis veya tedavi amacıyla kullanılamaz. Sonuçlar sağlık profesyonelinin değerlendirmesinin yerini tutmaz ve klinik kullanım için doğrulanmamıştır.

## Özellikler

- Dört bölümden oluşan hasta kabul formu: demografi, tıbbi geçmiş, yaşamsal bulgular ve şikâyet
- NEWS2 ve kritik belirti kontrollerine dayanan kural tabanlı önceliklendirme
- İsteğe bağlı OpenAI uyumlu API, Gemini veya IBM watsonx.ai entegrasyonu
- FedMML ve MTSamples veri kümeleriyle eğitilebilen isteğe bağlı yerel sınıflandırıcılar
- Günlük hasta kuyruğu, kayıt geçmişi ve triaj sonucu görüntüleme
- Yerel geliştirme için SQLite; yapılandırılabilir PostgreSQL ve Docker Compose ile Db2
- T.C. kimlik numarası ve pasaport numarası doğrulaması; API yanıtlarında kimlik numarasını maskeleme

## Teknoloji yığını

| Katman | Teknolojiler |
|---|---|
| Arayüz | React 18, Vite, Tailwind CSS |
| API | Python 3.12, FastAPI, Pydantic |
| Veri tabanı | SQLite (yerel varsayılan), PostgreSQL, IBM Db2 (Compose yapılandırması) |
| ML | pandas, scikit-learn, joblib |
| LLM | OpenAI uyumlu REST API, Google Gemini veya IBM watsonx.ai |

## Hızlı başlangıç

### Gereksinimler

- Python 3.12 (64 bit önerilir)
- Node.js ve npm
- Git
- İsteğe bağlı: Docker Desktop (Compose ile Db2 kullanmak için)

### 1. Backend’i başlatın

PowerShell’de proje klasöründen:

```powershell
cd backend
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements-dev.txt
uvicorn app.main:app --reload
```

macOS/Linux için sanal ortamı etkinleştirme komutu:

```bash
source .venv/bin/activate
```

Yerel varsayılan veritabanı SQLite’tır; ayrı bir veritabanı sunucusu başlatmanız gerekmez. İlk çalıştırmada tablolar otomatik oluşturulur. Backend `http://localhost:8000` adresinde, API dokümantasyonu `http://localhost:8000/docs` adresinde açılır.

> PowerShell sanal ortamı etkinleştirmeyi engellerse, aynı terminal oturumu için `Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass` komutunu çalıştırıp etkinleştirme adımını tekrarlayın.

### 2. Web arayüzünü başlatın

Yeni bir terminal açıp proje kökünden çalıştırın:

```powershell
cd frontend
npm install
npm run dev
```

Vite arayüzü genellikle `http://localhost:5173` adresinde açar ve `/api` isteklerini `http://127.0.0.1:8000` adresindeki backend’e yönlendirir.

## Yapılandırma

Uygulama, yapılandırmayı proje kökündeki veya `backend/` klasöründeki `.env` dosyasından okuyabilir. `.env.example` dosyasında örnek ayarlar bulunur. **Yerel SQLite kurulumu için `.env` dosyası oluşturmak gerekmez.** Örnek dosyayı kullanırsanız `DATABASE_URL` PostgreSQL adresine ayarlıdır; PostgreSQL çalıştırmıyorsanız bu satırı kaldırın veya `DATABASE_URL=sqlite:///./triaj.db` olarak değiştirin.

| Değişken | Açıklama |
|---|---|
| `DATABASE_URL` | SQLAlchemy bağlantı adresi. Yerel varsayılan `sqlite:///./triaj.db` değeridir. |
| `LLM_PROVIDER` | `openai_compatible`, `gemini` veya `watsonx` |
| `LLM_API_KEY` | OpenAI uyumlu sağlayıcının API anahtarı |
| `LLM_BASE_URL` | OpenAI uyumlu API adresi; varsayılan `https://api.openai.com/v1` |
| `LLM_MODEL` | OpenAI uyumlu API’de kullanılacak model adı |
| `GEMINI_API_KEY` | Gemini kullanılıyorsa API anahtarı |
| `WATSONX_API_KEY` / `WATSONX_PROJECT_ID` | watsonx.ai kullanılıyorsa erişim bilgileri |
| `TRIAGE_URGENCY_MODEL` / `TRIAGE_SPECIALTY_MODEL` | Eğitilmiş yerel model dosyalarının isteğe bağlı yolları |

LLM anahtarları boş bırakıldığında triaj kuralları çalışmayı sürdürür; LLM destekli açıklama ve değerlendirme devre dışı kalır. watsonx.ai ayarları kullanılmıyorsa Db2 yapılandırma değişkenlerini girmeniz gerekmez.

### Docker Compose ile Db2

Proje kökünde:

```powershell
docker compose up --build
```

Compose yapılandırması backend ve IBM Db2’yi başlatır. İlk Db2 kurulumu birkaç dakika sürebilir. Compose, `DATABASE_URL` değerini Db2 bağlantısı için kendisi ayarlar. Verileri sıfırlamak gerekirse `docker compose down -v` komutu Db2 veri hacmini de siler.

## API özeti

Tüm endpoint’ler `http://localhost:8000` taban adresini kullanır.

| Metot | Yol | Açıklama |
|---|---|---|
| `POST` | `/api/triage` | Yeni triaj kaydı oluşturur ve sonucu döndürür (`201`) |
| `GET` | `/api/triage` | Günlük kuyruğu listeler; `tarih`, `durum` ve `limit` filtreleri alır |
| `GET` | `/api/triage/{log_id}` | Bir kaydın sonucunu ve dört kabul bölümünü getirir |
| `GET` | `/api/triage/history` | Kayıt geçmişini listeler |
| `PATCH` | `/api/triage/{log_id}` | Kaydın renk kodlu durumunu günceller |
| `GET` | `/api/triage/secenekler` | Form seçeneklerini döndürür |
| `GET` | `/api/health` | Servis ve veritabanı durumunu bildirir |

### Örnek istek

```json
{
  "demografi": {
    "isim": "Ayşe Yılmaz",
    "yas": 34,
    "boy": 165,
    "kilo": 60.5,
    "kan_grubu": "A+",
    "kimlik_turu": "PASAPORT",
    "kimlik_no": "A1234567"
  },
  "tibbi_gecmis": {
    "kronik_rahatsizlik": "Astım",
    "surekli_ilac": ""
  },
  "vitaller": {
    "nabiz": 78,
    "tansiyon_sistolik": 120,
    "tansiyon_diyastolik": 80,
    "solunum": 16,
    "ates": 36.8,
    "spo2": 98
  },
  "sikayet": {
    "ana_sikayet": "Boğaz ağrısı",
    "agri_skalasi": 3
  }
}
```

### Skorları okuma

- `risk_skoru`, ESI yönünü kullanır: **1 en acil**, **5 en az acil**.
- `aciliyet_seviyesi`, arayüzde gösterilen ters ölçektir: **1 en düşük**, **5 en yüksek aciliyet**.
- Renkli durumlar `KIRMIZI`, `SARI` ve `YESIL` değerleridir.
- 65 yaş ve üzerindeki kişiler için nihai aciliyet seviyesi bir basamak artırılır.
- API, T.C. kimlik numarası ve pasaport numarasını maskeleyerek döndürür. Gerçek kişisel veya sağlık verilerini herkese açık ortamlara göndermeyin.

## Yerel ML modellerini eğitme (isteğe bağlı)

Eğitim CSV dosyaları `backend/data/` altında bulunur. Backend klasöründen:

```bash
python -m app.models.train \
  --fedmml ./data/fedmml.csv \
  --mtsamples ./data/mtsamples.csv
```

Eğitim, sınıflandırma metriklerini yazdırır ve modelleri `backend/model_artifacts/` altına kaydeder. Bu dosyalar `.gitignore` kapsamındadır. Eğitim verilerindeki başarı ölçümleri bağımsız klinik doğrulama anlamına gelmez. Veri kümelerinin kaynakları, lisansları ve model sınırlamaları için [model notlarına](backend/app/models/README.md) bakın.

## Proje yapısı

```text
backend/
  app/api/       FastAPI endpoint’leri
  app/core/      Triaj kuralları, LLM bağlantıları ve yapılandırma
  app/db/        SQLAlchemy modelleri ve veri erişimi
  app/models/    Veri modelleri ve ML sınıflandırıcıları
  data/          Model eğitim verileri
  tests/         Backend testleri
frontend/        React arayüzü
database/        Db2 başlangıç şeması ve kurulum betiği
docker-compose.yml
```

## Lisans

Kod [MIT Lisansı](LICENSE) ile dağıtılır. Model eğitim verilerinin kaynak ve lisans bilgileri [model notlarında](backend/app/models/README.md) açıklanmıştır.
