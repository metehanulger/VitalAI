import React, { useState } from 'react';

export default function TriageBentoBox() {
  const [isLocked, setIsLocked] = useState(false);
  const [errorMsg, setErrorMsg] = useState('');

  const [demographics, setDemographics] = useState({
    name: '', age: '', height: '', weight: '', bloodType: '', passportId: ''
  });
  
  const [medicalHistory, setMedicalHistory] = useState({
    chronicIllness: '', regularMedication: '' // Zorunlu Değil
  });

  const [vitals, setVitals] = useState({
    pulse: '', bloodPressure: '', respiration: '', temperature: '', spO2: ''
  });

  const [complaint, setComplaint] = useState({
    mainComplaint: '', painScale: 5 // Ağrı Skalası Zorunlu Değil (Varsayılan 5)
  });

  // 1. Aşama: Verileri Doğrula ve Kilitle
  const handleLock = () => {
    // Zorunlu alanların listesi
    const requiredDemographics = ['name', 'age', 'height', 'weight', 'bloodType', 'passportId'];
    const requiredVitals = ['pulse', 'bloodPressure', 'respiration', 'temperature', 'spO2'];

    // Temel demografi kontrolü
    for (let field of requiredDemographics) {
      if (!demographics[field].trim && !demographics[field]) {
         setErrorMsg('Hata: Temel Demografi alanlarında eksik veri var.');
         return;
      }
    }

    // Vitallerin kontrolü
    for (let field of requiredVitals) {
      if (!vitals[field].trim && !vitals[field]) {
         setErrorMsg('Hata: Anlık Vitaller eksiksiz girilmelidir.');
         return;
      }
    }

    // Ana şikayet kontrolü
    if (!complaint.mainComplaint) {
      setErrorMsg('Hata: Hastanın ana şikayetini girmediniz.');
      return;
    }

    // Sorun yoksa hataları temizle ve formu kilitle
    setErrorMsg('');
    setIsLocked(true);
  };

  // 2. Aşama: AI Analizini Başlat
  const handleAnalyze = () => {
    if (!isLocked) return;
    const finalTriageData = { demographics, medicalHistory, vitals, complaint };
    console.log("Veritabanı ve AI'a Gönderilecek Doğrulanmış Veri:", finalTriageData);
    alert("Veriler backend'e gönderiliyor. Konsolu kontrol et.");
    // TODO: Axios ile backend endpointine istek atılacak
  };

  return (
    <div className="min-h-screen p-6 flex flex-col items-center">
      <div className="w-full max-w-6xl">
        
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          
          {/* KART 1: Temel Demografi (ZORUNLU) */}
          <div className={`md:col-span-2 bg-white rounded-3xl p-6 shadow-sm border ${isLocked ? 'border-green-400 opacity-80' : 'border-slate-200'}`}>
            <h2 className="text-xl font-semibold text-slate-800 mb-4">Temel Demografi *</h2>
            <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
              <input type="text" placeholder="İsim Soyisim" disabled={isLocked} className="border p-3 rounded-xl w-full disabled:bg-slate-50" 
                onChange={e => setDemographics({...demographics, name: e.target.value})} />
              <input type="number" placeholder="Yaş" disabled={isLocked} className="border p-3 rounded-xl w-full disabled:bg-slate-50" 
                onChange={e => setDemographics({...demographics, age: e.target.value})} />
              <input type="text" placeholder="Pasaport / TC ID" disabled={isLocked} className="border p-3 rounded-xl w-full disabled:bg-slate-50" 
                onChange={e => setDemographics({...demographics, passportId: e.target.value})} />
              <input type="number" placeholder="Boy (cm)" disabled={isLocked} className="border p-3 rounded-xl w-full disabled:bg-slate-50" 
                onChange={e => setDemographics({...demographics, height: e.target.value})} />
              <input type="number" placeholder="Kilo (kg)" disabled={isLocked} className="border p-3 rounded-xl w-full disabled:bg-slate-50" 
                onChange={e => setDemographics({...demographics, weight: e.target.value})} />
              <select disabled={isLocked} className="border p-3 rounded-xl w-full disabled:bg-slate-50" 
                onChange={e => setDemographics({...demographics, bloodType: e.target.value})}>
                <option value="">Kan Grubu</option>
                <option value="A+">A+</option><option value="A-">A-</option>
                <option value="B+">B+</option><option value="B-">B-</option>
                <option value="AB+">AB+</option><option value="AB-">AB-</option>
                <option value="O+">0+</option><option value="O-">0-</option>
              </select>
            </div>
          </div>

          {/* KART 3: Anlık Vitaller (ZORUNLU) */}
          <div className={`md:col-span-1 bg-white rounded-3xl p-6 shadow-sm border ${isLocked ? 'border-green-400 opacity-80' : 'border-slate-200'}`}>
            <h2 className="text-xl font-semibold text-slate-800 mb-4">Anlık Vitaller *</h2>
            <div className="flex flex-col gap-3">
              <input type="number" placeholder="Nabız (bpm)" disabled={isLocked} className="border p-3 rounded-xl w-full bg-red-50 focus:bg-white disabled:bg-slate-50" 
                onChange={e => setVitals({...vitals, pulse: e.target.value})} />
              <input type="text" placeholder="Tansiyon (Örn: 120/80)" disabled={isLocked} className="border p-3 rounded-xl w-full disabled:bg-slate-50" 
                onChange={e => setVitals({...vitals, bloodPressure: e.target.value})} />
              <input type="number" placeholder="SpO2 (%)" disabled={isLocked} className="border p-3 rounded-xl w-full bg-blue-50 focus:bg-white disabled:bg-slate-50" 
                onChange={e => setVitals({...vitals, spO2: e.target.value})} />
              <div className="grid grid-cols-2 gap-3">
                <input type="number" placeholder="Ateş (°C)" disabled={isLocked} className="border p-3 rounded-xl w-full disabled:bg-slate-50" 
                  onChange={e => setVitals({...vitals, temperature: e.target.value})} />
                <input type="number" placeholder="Solunum" disabled={isLocked} className="border p-3 rounded-xl w-full disabled:bg-slate-50" 
                  onChange={e => setVitals({...vitals, respiration: e.target.value})} />
              </div>
            </div>
          </div>

          {/* KART 2: Tıbbi Geçmiş (OPSİYONEL) */}
          <div className={`md:col-span-1 bg-white rounded-3xl p-6 shadow-sm border ${isLocked ? 'border-green-400 opacity-80' : 'border-slate-200'}`}>
            <h2 className="text-xl font-semibold text-slate-800 mb-4">Tıbbi Geçmiş</h2>
            <div className="flex flex-col gap-4">
              <textarea placeholder="Kronik Rahatsızlıklar (Virgülle ayırın)" disabled={isLocked} className="border p-3 rounded-xl w-full h-24 resize-none disabled:bg-slate-50" 
                onChange={e => setMedicalHistory({...medicalHistory, chronicIllness: e.target.value})} />
              <textarea placeholder="Sürekli Kullanılan İlaçlar" disabled={isLocked} className="border p-3 rounded-xl w-full h-24 resize-none disabled:bg-slate-50" 
                onChange={e => setMedicalHistory({...medicalHistory, regularMedication: e.target.value})} />
            </div>
          </div>

          {/* KART 4: Şikayet (ANA ŞİKAYET ZORUNLU, SKALA OPSİYONEL) */}
          <div className={`md:col-span-2 bg-white rounded-3xl p-6 shadow-sm border flex flex-col ${isLocked ? 'border-green-400 opacity-80' : 'border-slate-200'}`}>
            <h2 className="text-xl font-semibold text-slate-800 mb-4">Klinik Şikayet *</h2>
            <div className="flex flex-col gap-6 flex-grow">
              <textarea placeholder="Hastanın ana şikayeti ve semptomların süresi..." disabled={isLocked} className="border p-4 rounded-xl w-full flex-grow resize-none disabled:bg-slate-50" 
                onChange={e => setComplaint({...complaint, mainComplaint: e.target.value})} />
              
              <div className="bg-slate-50 p-4 rounded-xl border">
                <label className="block text-sm font-medium text-slate-600 mb-2">
                  Ağrı Skalası: <span className="text-lg font-bold text-red-600">{complaint.painScale}</span>/10
                </label>
                <input type="range" min="1" max="10" defaultValue="5" disabled={isLocked} className="w-full h-2 bg-gray-200 rounded-lg appearance-none cursor-pointer accent-red-500 disabled:opacity-50" 
                  onChange={e => setComplaint({...complaint, painScale: e.target.value})} />
                <div className="flex justify-between text-xs text-slate-400 mt-1">
                  <span>Hafif (1)</span><span>Dayanılmaz (10)</span>
                </div>
              </div>
            </div>
          </div>

        </div>

        {/* Aksiyon Barı */}
        <div className="mt-8 flex items-center justify-between bg-white p-4 rounded-2xl shadow-sm border border-slate-200">
          
          <div className="flex-1">
            {errorMsg && <p className="text-red-600 font-bold bg-red-50 p-3 rounded-lg border border-red-200 inline-block">{errorMsg}</p>}
            {isLocked && <p className="text-green-600 font-bold bg-green-50 p-3 rounded-lg border border-green-200 inline-block">Veriler kilitlendi ve doğrulandı. Analize hazır.</p>}
          </div>

          <div className="flex gap-4">
            {!isLocked ? (
              <button type="button" onClick={handleLock} className="bg-slate-900 hover:bg-slate-800 text-white font-semibold py-4 px-10 rounded-xl shadow-md transition-all">
                Verileri Kilitle
              </button>
            ) : (
              <>
                <button type="button" onClick={() => setIsLocked(false)} className="bg-slate-200 hover:bg-slate-300 text-slate-800 font-semibold py-4 px-6 rounded-xl transition-all">
                  Kilidi Aç / Düzenle
                </button>
                <button type="button" onClick={handleAnalyze} className="bg-red-600 hover:bg-red-700 text-white font-bold py-4 px-10 rounded-xl shadow-lg transition-transform hover:scale-105 animate-pulse">
                  AI Analizi Başlat
                </button>
              </>
            )}
          </div>
          
        </div>

      </div>
    </div>
  );
}