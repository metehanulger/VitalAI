import React, { useState } from 'react';

export default function TriageBentoBox() {
  const [isLocked, setIsLocked] = useState(false);
  const [errorMsg, setErrorMsg] = useState('');
  const [activeTooltip, setActiveTooltip] = useState(null);

  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [analysisResult, setAnalysisResult] = useState(null);

  const [demographics, setDemographics] = useState({
    name: '', age: '', height: '', weight: '', bloodType: '', identityType: 'PASAPORT', passportId: ''
  });

  const [medicalHistory, setMedicalHistory] = useState({
    chronicIllness: '', regularMedication: ''
  });

  const [vitals, setVitals] = useState({
    pulse: '', systolicBP: '', diastolicBP: '', respiration: '', temperature: '', spO2: ''
  });

  const [complaint, setComplaint] = useState({
    mainComplaint: '', painScale: 5
  });

  const handleLock = () => {
    const requiredDemographics = ['name', 'age', 'passportId'];
    const requiredVitals = ['pulse', 'systolicBP', 'diastolicBP', 'respiration', 'temperature', 'spO2'];

    for (let field of requiredDemographics) {
      if (!String(demographics[field]).trim()) {
         setErrorMsg('Error: Missing data in Basic Demographics.');
         return;
      }
    }

    for (let field of requiredVitals) {
      if (!String(vitals[field]).trim()) {
         setErrorMsg('Error: Current Vitals must be completely filled.');
         return;
      }
    }

    if (Number(vitals.systolicBP) <= Number(vitals.diastolicBP)) {
      setErrorMsg('Systolic blood pressure must be higher than diastolic pressure.');
      return;
    }

    if (!complaint.mainComplaint.trim()) {
      setErrorMsg('Error: Main clinical complaint is missing.');
      return;
    }

    setErrorMsg('');
    setIsLocked(true);
    setActiveTooltip(null);
  };

  const handleAnalyze = async () => {
    if (!isLocked) return;
    setIsAnalyzing(true);
    setErrorMsg('');
    setAnalysisResult(null);

    const optionalNumber = value => value === '' ? null : Number(value);
    const requestBody = {
      demografi: {
        isim: demographics.name.trim(),
        yas: Number(demographics.age),
        boy: optionalNumber(demographics.height),
        kilo: optionalNumber(demographics.weight),
        kan_grubu: demographics.bloodType || 'BILINMIYOR',
        kimlik_turu: demographics.identityType,
        kimlik_no: demographics.passportId.trim(),
      },
      tibbi_gecmis: {
        kronik_rahatsizlik: medicalHistory.chronicIllness.trim() || null,
        surekli_ilac: medicalHistory.regularMedication.trim() || null,
      },
      vitaller: {
        nabiz: Number(vitals.pulse),
        tansiyon_sistolik: Number(vitals.systolicBP),
        tansiyon_diastolik: Number(vitals.diastolicBP),
        solunum: Number(vitals.respiration),
        ates: Number(vitals.temperature),
        spo2: Number(vitals.spO2),
      },
      sikayet: {
        ana_sikayet: complaint.mainComplaint.trim(),
        agri_skalasi: Number(complaint.painScale),
      },
    };

    try {
      const response = await fetch('/api/triage', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(requestBody),
      });
      const responseText = await response.text();
      let result;
      try {
        result = responseText ? JSON.parse(responseText) : {};
      } catch {
        throw new Error(`Backend HTTP ${response.status}: ${responseText.slice(0, 200) || 'Invalid response'}`);
      }
      if (!response.ok) {
        const fieldLabels = {
          demografi: 'Basic Demographics', isim: 'Full Name', yas: 'Age', boy: 'Height', kilo: 'Weight',
          kan_grubu: 'Blood Type', kimlik_turu: 'ID Type', kimlik_no: 'ID or Passport Number',
          tibbi_gecmis: 'Medical History', kronik_rahatsizlik: 'Chronic Illnesses', surekli_ilac: 'Regular Medications',
          vitaller: 'Current Vitals', nabiz: 'Heart Rate', tansiyon_sistolik: 'Systolic Blood Pressure',
          tansiyon_diastolik: 'Diastolic Blood Pressure', solunum: 'Respiration Rate', ates: 'Temperature', spo2: 'Oxygen Saturation',
          sikayet: 'Clinical Complaint', ana_sikayet: 'Main Complaint', agri_skalasi: 'Pain Scale',
        };
        const detail = Array.isArray(result.detail)
          ? result.detail.map(item => {
            const path = item.loc?.slice(1).map(part => fieldLabels[part] || part).join(' > ');
            return `${path ? `${path}: ` : ''}${item.msg}`;
          }).join(' | ')
          : result.detail;
        throw new Error(detail || `Request failed (${response.status}).`);
      }

      const urgency = result.aciliyet_seviyesi;
      const urgencyLabels = {
        1: 'Not urgent',
        2: 'Low urgency',
        3: 'Moderate urgency',
        4: 'Urgent',
        5: 'Very urgent',
      };
      const statusLabels = { KIRMIZI: 'RED', SARI: 'YELLOW', YESIL: 'GREEN' };
      const sourceLabels = { KURAL: 'RULE-BASED', AGE_64_PLUS: 'AGE 64+', ML: 'ML' };
      const departmentLabels = {
        'Acil Tıp': 'Emergency Medicine',
        'Kardiyoloji': 'Cardiology',
        'Nöroloji': 'Neurology',
        'Göğüs Hastalıkları': 'Pulmonology',
        'Genel Cerrahi': 'General Surgery',
        'Ortopedi ve Travmatoloji': 'Orthopedics and Traumatology',
        'Dahiliye': 'Internal Medicine',
        'Genel Dahiliye': 'Internal Medicine',
        'Kulak Burun Boğaz': 'Otolaryngology',
        'Göz Hastalıkları': 'Ophthalmology',
        'Enfeksiyon Hastalıkları': 'Infectious Diseases',
        'Gastroenteroloji': 'Gastroenterology',
        'Üroloji': 'Urology',
        'Endokrinoloji': 'Endocrinology',
        'Girişimsel Radyoloji': 'Interventional Radiology',
        'Göğüs Cerrahisi': 'Thoracic Surgery',
      };
      const department = result.onerilen_poliklinik || 'Not determined';
      const decisionSource = result.karar_kaynagi
        ?.split('+')
        .map(source => sourceLabels[source] || source)
        .join(' + ') || 'Unknown';
      setAnalysisResult({
        priorityScore: urgency,
        priorityLabel: urgencyLabels[urgency] || statusLabels[result.hasta_durumu] || result.hasta_durumu,
        recommendedPolyclinic: department.split(/\s*\/\s*/).map(name => departmentLabels[name] || name).join(' / '),
        reasoning: result.aciklama || 'No explanation was returned.',
        status: statusLabels[result.hasta_durumu] || result.hasta_durumu,
        source: decisionSource,
        logId: result.log_id,
      });
    } catch (error) {
      const message = error instanceof TypeError
        ? 'Cannot reach the backend. Check that it is running and that the Vite proxy is configured.'
        : `Analysis failed: ${error.message}`;
      setErrorMsg(message);
    } finally {
      setIsAnalyzing(false);
    }
  };

  const Tooltip = ({ id, title, content }) => (
    <div className="relative inline-block ml-2">
      <button
        type="button"
        disabled={isLocked}
        onClick={() => setActiveTooltip(activeTooltip === id ? null : id)}
        className="w-6 h-6 rounded-full bg-slate-200 text-slate-700 text-sm font-bold flex items-center justify-center hover:bg-slate-300 transition-colors disabled:opacity-50"
      >
        ?
      </button>
      {activeTooltip === id && !isLocked && (
        <div className="absolute z-10 w-64 p-4 mt-2 text-sm text-white bg-slate-800 rounded-xl shadow-xl left-0 md:-left-28 border border-slate-600">
          <div className="font-bold mb-2 text-red-400">{title}</div>
          <div className="text-slate-200 text-xs leading-relaxed">{content}</div>
        </div>
      )}
    </div>
  );

  return (
    <div className="min-h-screen p-6 flex flex-col items-center" onClick={(e) => {
      if (!e.target.closest('button') && activeTooltip) setActiveTooltip(null);
    }}>
      <div className="w-full max-w-6xl">

        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">


          <div className={`md:col-span-2 bg-white rounded-3xl p-6 shadow-sm border ${isLocked ? 'border-green-400 opacity-80' : 'border-slate-200'}`}>
            <h2 className="text-xl font-semibold text-slate-800 mb-4">Basic Demographics *</h2>
            <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
              <input type="text" placeholder="Full Name" disabled={isLocked} className="border p-3 rounded-xl w-full disabled:bg-slate-50"
                onChange={e => setDemographics({...demographics, name: e.target.value})} />
              <input type="number" placeholder="Age" disabled={isLocked} className="border p-3 rounded-xl w-full disabled:bg-slate-50"
                onChange={e => setDemographics({...demographics, age: e.target.value})} />
              <select value={demographics.identityType} disabled={isLocked} className="border p-3 rounded-xl w-full disabled:bg-slate-50"
                onChange={e => setDemographics({...demographics, identityType: e.target.value})}>
                <option value="PASAPORT">Passport</option>
                <option value="TC">Turkish ID</option>
              </select>

              <div className="relative w-full flex items-center border rounded-xl disabled:bg-slate-50 bg-white pr-2">
                <input type="text" placeholder={demographics.identityType === 'TC' ? '11-digit Turkish ID' : 'Passport number'} disabled={isLocked} className="p-3 rounded-xl w-full outline-none disabled:bg-slate-50 bg-transparent"
                  onChange={e => setDemographics({...demographics, passportId: e.target.value})} />
                <Tooltip
                  id="passport"
                  title="ID Number Rule"
                  content="Choose the matching ID type. Turkish IDs must be valid 11-digit numbers; passport numbers must be 5-20 letters or digits."
                />
              </div>

              <input type="number" placeholder="Height (cm)" disabled={isLocked} className="border p-3 rounded-xl w-full disabled:bg-slate-50"
                onChange={e => setDemographics({...demographics, height: e.target.value})} />
              <input type="number" placeholder="Weight (kg)" disabled={isLocked} className="border p-3 rounded-xl w-full disabled:bg-slate-50"
                onChange={e => setDemographics({...demographics, weight: e.target.value})} />
              <select disabled={isLocked} className="border p-3 rounded-xl w-full disabled:bg-slate-50"
                onChange={e => setDemographics({...demographics, bloodType: e.target.value})}>
                <option value="">Blood Type</option>
                <option value="A+">A+</option><option value="A-">A-</option>
                <option value="B+">B+</option><option value="B-">B-</option>
                <option value="AB+">AB+</option><option value="AB-">AB-</option>
                <option value="O+">O+</option><option value="O-">O-</option>
              </select>
            </div>
          </div>


          <div className={`md:col-span-1 bg-white rounded-3xl p-6 shadow-sm border ${isLocked ? 'border-green-400 opacity-80' : 'border-slate-200'}`}>
            <h2 className="text-xl font-semibold text-slate-800 mb-4">Current Vitals *</h2>
            <div className="flex flex-col gap-3">
              <input type="number" placeholder="Heart Rate (bpm)" disabled={isLocked} className="border p-3 rounded-xl w-full bg-red-50 focus:bg-white disabled:bg-slate-50"
                onChange={e => setVitals({...vitals, pulse: e.target.value})} />
              <div className="grid grid-cols-2 gap-3">
                <input type="number" min="40" max="300" placeholder="Systolic BP" disabled={isLocked} className="border p-3 rounded-xl w-full disabled:bg-slate-50"
                  onChange={e => setVitals({...vitals, systolicBP: e.target.value})} />
                <input type="number" min="20" max="200" placeholder="Diastolic BP" disabled={isLocked} className="border p-3 rounded-xl w-full disabled:bg-slate-50"
                  onChange={e => setVitals({...vitals, diastolicBP: e.target.value})} />
              </div>
              <input type="number" placeholder="SpO2 (%)" disabled={isLocked} className="border p-3 rounded-xl w-full bg-blue-50 focus:bg-white disabled:bg-slate-50"
                onChange={e => setVitals({...vitals, spO2: e.target.value})} />
              <div className="grid grid-cols-2 gap-3">
                <input type="number" placeholder="Temperature (°C)" disabled={isLocked} className="border p-3 rounded-xl w-full disabled:bg-slate-50"
                  onChange={e => setVitals({...vitals, temperature: e.target.value})} />
                <input type="number" placeholder="Respiration Rate" disabled={isLocked} className="border p-3 rounded-xl w-full disabled:bg-slate-50"
                  onChange={e => setVitals({...vitals, respiration: e.target.value})} />
              </div>
            </div>
          </div>


          <div className={`md:col-span-1 bg-white rounded-3xl p-6 shadow-sm border ${isLocked ? 'border-green-400 opacity-80' : 'border-slate-200'}`}>
            <h2 className="text-xl font-semibold text-slate-800 mb-4">Medical History</h2>
            <div className="flex flex-col gap-4">
              <textarea placeholder="Chronic Illnesses (Comma separated)" disabled={isLocked} className="border p-3 rounded-xl w-full h-24 resize-none disabled:bg-slate-50"
                onChange={e => setMedicalHistory({...medicalHistory, chronicIllness: e.target.value})} />
              <textarea placeholder="Regular Medications" disabled={isLocked} className="border p-3 rounded-xl w-full h-24 resize-none disabled:bg-slate-50"
                onChange={e => setMedicalHistory({...medicalHistory, regularMedication: e.target.value})} />
            </div>
          </div>


          <div className={`md:col-span-2 bg-white rounded-3xl p-6 shadow-sm border flex flex-col ${isLocked ? 'border-green-400 opacity-80' : 'border-slate-200'}`}>
            <div className="flex items-center mb-4">
              <h2 className="text-xl font-semibold text-slate-800">Clinical Complaint *</h2>
              <Tooltip
                id="complaintInfo"
                title="Complaint"
                content="Describe the patient's symptoms in English. Include when they began and any important accompanying symptoms."
              />
            </div>
            <div className="flex flex-col gap-6 flex-grow">
              <textarea placeholder="Describe the patient's complaint and symptoms..." disabled={isLocked} className="border p-4 rounded-xl w-full flex-grow resize-none disabled:bg-slate-50"
                onChange={e => setComplaint({...complaint, mainComplaint: e.target.value})} />

              <div className="bg-slate-50 p-4 rounded-xl border">
                <div className="flex items-center mb-2">
                  <label className="text-sm font-medium text-slate-600">
                    Pain Scale: <span className="text-lg font-bold text-red-600 ml-1">{complaint.painScale}</span>/10
                  </label>
                  <Tooltip
                    id="painScale"
                    title="Pain Scale Criteria"
                    content="Pain value should be determined based on the patient's current discomfort and trauma status. 1-3: Mild discomfort, 4-6: Moderate pain disrupting daily activity, 7-10: Severe/Unbearable acute pain."
                  />
                </div>
                <input type="range" min="1" max="10" defaultValue="5" disabled={isLocked} className="w-full h-2 bg-gray-200 rounded-lg appearance-none cursor-pointer accent-red-500 disabled:opacity-50"
                  onChange={e => setComplaint({...complaint, painScale: e.target.value})} />
                <div className="flex justify-between text-xs text-slate-400 mt-1">
                  <span>Mild (1)</span><span>Unbearable (10)</span>
                </div>
              </div>
            </div>
          </div>

        </div>


        <div className="mt-8 flex items-center justify-between bg-white p-4 rounded-2xl shadow-sm border border-slate-200">

          <div className="flex-1">
            {errorMsg && <p className="text-red-600 font-bold bg-red-50 p-3 rounded-lg border border-red-200 inline-block">{errorMsg}</p>}
            {isLocked && !isAnalyzing && !analysisResult && <p className="text-green-600 font-bold bg-green-50 p-3 rounded-lg border border-green-200 inline-block">Data locked and verified. Ready for analysis.</p>}
            {isAnalyzing && <p className="text-blue-600 font-bold bg-blue-50 p-3 rounded-lg border border-blue-200 inline-block animate-pulse">Backend is analyzing the patient information...</p>}
          </div>

          <div className="flex gap-4">
            {!isLocked ? (
              <button type="button" onClick={handleLock} className="bg-slate-900 hover:bg-slate-800 text-white font-semibold py-4 px-10 rounded-xl shadow-md transition-all">
                Lock Data
              </button>
            ) : (
              <>
                <button type="button" onClick={() => { setIsLocked(false); setAnalysisResult(null); }} disabled={isAnalyzing} className="bg-slate-200 hover:bg-slate-300 text-slate-800 font-semibold py-4 px-6 rounded-xl transition-all disabled:opacity-50">
                  Unlock / Edit
                </button>
                <button type="button" onClick={handleAnalyze} disabled={isAnalyzing} className="bg-red-600 hover:bg-red-700 text-white font-bold py-4 px-10 rounded-xl shadow-lg transition-transform hover:scale-105 disabled:opacity-50 disabled:hover:scale-100">
                  {isAnalyzing ? 'Analyzing...' : 'Send for Triage Analysis'}
                </button>
              </>
            )}
          </div>

        </div>


        {analysisResult && (
          <div className="mt-6 bg-slate-900 text-white rounded-3xl p-8 shadow-xl border-2 border-red-500 transition-all">
            <div className="flex flex-col md:flex-row items-start md:items-center justify-between gap-6 border-b border-slate-700 pb-6 mb-6">

              <div className="flex items-center gap-4">
                <div className="flex flex-col items-center justify-center bg-red-600 w-20 h-20 rounded-2xl shadow-inner">
                  <span className="text-xs font-semibold text-red-100 uppercase tracking-wider">Urgency</span>
                  <span className="text-4xl font-black text-white">{analysisResult.priorityScore}</span>
                </div>
                <div>
                  <h3 className="text-2xl font-bold text-slate-100">Triage Result</h3>
                  <p className="text-red-400 font-medium text-lg">{analysisResult.priorityLabel}</p>
                  <p className="text-slate-400 text-sm">{analysisResult.status} · Decision: {analysisResult.source}</p>
                </div>
              </div>

              <div className="bg-slate-800 px-6 py-4 rounded-2xl border border-slate-700">
                <span className="block text-xs text-slate-400 uppercase tracking-wider mb-1">Recommended Department</span>
                <span className="text-lg font-bold text-white">{analysisResult.recommendedPolyclinic}</span>
              </div>

            </div>

            <div>
              <span className="block text-sm text-slate-400 uppercase tracking-wider mb-2">Explanation</span>
              <p className="text-slate-300 text-base leading-relaxed bg-slate-800/50 p-4 rounded-xl">
                {analysisResult.reasoning}
              </p>
            </div>

            <div className="mt-6 flex justify-between text-sm text-slate-400">
              <span>Record #{analysisResult.logId} · This analysis has been saved.</span>
              <span>Urgency scale: 1 = not urgent, 5 = very urgent</span>
            </div>
          </div>
        )}

      </div>
    </div>
  );
}
