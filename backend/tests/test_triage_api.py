import copy

from app.core import triage


def test_health(client):
    r = client.get("/api/health")
    assert r.status_code == 200
    assert r.json() == {"durum": "ok", "veritabani": True, "watsonx": False}


def test_triaj_olustur_kodlari_loga_yazar(client, istek):
    r = client.post("/api/triage", json=istek)
    assert r.status_code == 201, r.text
    veri = r.json()
    assert veri["hasta_durumu"] == "YESIL"
    assert veri["karar_kaynagi"] == "KURAL"
    assert set(veri["kodlar"]) == {"demografi_id", "tibbi_gecmis_id", "vitaller_id", "sikayet_id"}

    detay = client.get(f"/api/triage/{veri['log_id']}").json()
    assert detay["kodlar"] == veri["kodlar"]
    assert detay["demografi"]["id"] == veri["kodlar"]["demografi_id"]
    assert detay["demografi"]["kimlik_no"] == "10*******46"
    assert detay["tibbi_gecmis"]["surekli_ilac"] is None
    assert detay["vitaller"]["spo2"] == 98


def test_sira_no_her_kayitta_artar(client, istek):
    ilk = client.post("/api/triage", json=istek).json()
    ikinci = client.post("/api/triage", json=istek).json()
    assert ikinci["sira_no"] == ilk["sira_no"] + 1
    assert ikinci["tarih"] == ilk["tarih"]


def test_kritik_vital_kirmizi(client, istek):
    istek["vitaller"]["spo2"] = 85
    veri = client.post("/api/triage", json=istek).json()
    assert veri["hasta_durumu"] == "KIRMIZI"
    assert "SpO2" in veri["aciklama"]


def test_kuyruk_aciliyete_gore_sirali(client, istek):
    kritik = copy.deepcopy(istek)
    kritik["sikayet"]["ana_sikayet"] = "Göğüs ağrısı, sol kola yayılıyor"
    client.post("/api/triage", json=istek)
    client.post("/api/triage", json=kritik)

    liste = client.get("/api/triage").json()
    seviye = {"KIRMIZI": 0, "SARI": 1, "YESIL": 2}
    anahtarlar = [(seviye[k["hasta_durumu"]], k["sira_no"]) for k in liste]
    assert anahtarlar == sorted(anahtarlar)
    assert liste[0]["hasta_durumu"] == "KIRMIZI"

    yesiller = client.get("/api/triage", params={"durum": "YESIL"}).json()
    assert yesiller and all(k["hasta_durumu"] == "YESIL" for k in yesiller)


def test_durum_elle_guncellenir(client, istek):
    log_id = client.post("/api/triage", json=istek).json()["log_id"]
    r = client.patch(f"/api/triage/{log_id}", json={"hasta_durumu": "SARI", "aciklama": "Doktor değerlendirmesi"})
    assert r.status_code == 200
    assert r.json()["hasta_durumu"] == "SARI"
    assert r.json()["karar_kaynagi"] == "MANUEL"


def test_olmayan_kayit_404(client):
    assert client.get("/api/triage/999999").status_code == 404


def test_secenekler(client):
    veri = client.get("/api/triage/secenekler").json()
    assert "0+" in veri["kan_gruplari"]
    assert veri["agri_skalasi"] == {"min": 1, "max": 10}


def test_gecersiz_girdiler_422(client, istek):
    hatalilar = []
    for yol, deger in [
        (("demografi", "kimlik_no"), "12345678901"),
        (("sikayet", "agri_skalasi"), 11),
        (("vitaller", "tansiyon_diastolik"), 130),
        (("vitaller", "spo2"), 101),
    ]:
        kopya = copy.deepcopy(istek)
        kopya[yol[0]][yol[1]] = deger
        hatalilar.append(client.post("/api/triage", json=kopya).status_code)
    assert hatalilar == [422, 422, 422, 422]


def test_pasaport_ve_kan_grubu_normalize(client, istek):
    istek["demografi"].update(kimlik_turu="PASAPORT", kimlik_no="u 1234567", kan_grubu="O Rh-")
    veri = client.post("/api/triage", json=istek).json()
    demografi = client.get(f"/api/triage/{veri['log_id']}").json()["demografi"]
    assert demografi["kan_grubu"] == "0-"
    assert demografi["kimlik_no"] == "U1****67"


def test_yapay_zeka_yalnizca_yukseltebilir(client, istek, monkeypatch):
    monkeypatch.setattr(triage.watsonx, "degerlendir", lambda ozet: ("KIRMIZI", "Klinik tablo ağır."))
    veri = client.post("/api/triage", json=istek).json()
    assert (veri["hasta_durumu"], veri["karar_kaynagi"]) == ("KIRMIZI", "WATSONX")

    istek["sikayet"]["agri_skalasi"] = 9  # kural: SARI
    monkeypatch.setattr(triage.watsonx, "degerlendir", lambda ozet: ("YESIL", "Hafif."))
    veri = client.post("/api/triage", json=istek).json()
    assert (veri["hasta_durumu"], veri["karar_kaynagi"]) == ("SARI", "KURAL")
