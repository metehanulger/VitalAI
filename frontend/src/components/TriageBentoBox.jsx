import React, { useState } from 'react';

export default function TriageBentoBox() {
  const [isLocked, setIsLocked] = useState(false);
  const [errorMsg, setErrorMsg] = useState('');
  const [activeTooltip, setActiveTooltip] = useState(null);
  
  // AI Analiz State'leri
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [analysisResult, setAnalysisResult] = useState(null);

  const [demographics, setDemographics] = useState({
    name: '', age: '', height: '', weight: '', bloodType: '', passportId: ''
  });
  
  const [medicalHistory, setMedicalHistory] = useState({
    chronicIllness: '', regularMedication: ''
  });

  const [vitals, setVitals] = useState({
    pulse: '', bloodPressure: '', respiration: '', temperature: '', spO2: ''
  });

  const [complaint, setComplaint] = useState({
    mainComplaint: '', painScale: 5
  });

  const handleLock = () => {
    const requiredDemographics = ['name', 'age', 'height', 'weight', 'bloodType', 'passportId'];
    const requiredVitals = ['pulse', 'bloodPressure', 'respiration', 'temperature', 'spO2'];

    for (let field of requiredDemographics) {
      if (!demographics[field].trim && !demographics[field]) {
         setErrorMsg('Error: Missing data in Basic Demographics.');
         return;
      }
    }

    for (let field of requiredVitals) {
      if (!vitals[field].trim && !vitals[field]) {
         setErrorMsg('Error: Current Vitals must be completely filled.');
         return;
      }
    }

    if (!complaint.mainComplaint) {
      setErrorMsg('Error: Main clinical complaint is missing.');
      return;
    }

    setErrorMsg('');
    setIsLocked(true);
    setActiveTooltip(null);
  };

  const handleAnalyze = () => {
    if (!isLocked) return;
    setIsAnalyzing(true);
    setAnalysisResult(null);

    const finalTriageData = { demographics, medicalHistory, vitals, complaint };
    console.log("Verified Data for DB & AI:", finalTriageData);

    // Backend'e gidip gelme süresini simüle ediyoruz (2 saniye)
    setTimeout(() => {
      setIsAnalyzing(false);
      // WatsonX'ten dönecek olan örnek sonuç formatı
      setAnalysisResult({
        priorityScore: 2, // 1 (Highest) to 5 (Lowest)
        priorityLabel: 'Emergent',
        recommendedPolyclinic: 'Cardiology / Emergency Red Zone',
        reasoning: 'Patient exhibits severe chest pain with elevated heart rate, indicating high risk of acute myocardial infarction. Immediate ECG and cardiac enzyme tests are required.'
      });
    }, 2000);
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
          
          {/* CARD 1: Basic Demographics */}
          <div className={`md:col-span-2 bg-white rounded-3xl p-6 shadow-sm border ${isLocked ? 'border-green-400 opacity-80' : 'border-slate-200'}`}>
            <h2 className="text-xl font-semibold text-slate-800 mb-4">Basic Demographics *</h2>
            <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
              <input type="text" placeholder="Full Name" disabled={isLocked} className="border p-3 rounded-xl w-full disabled:bg-slate-50" 
                onChange={e => setDemographics({...demographics, name: e.target.value})} />
              <input type="number" placeholder="Age" disabled={isLocked} className="border p-3 rounded-xl w-full disabled:bg-slate-50" 
                onChange={e => setDemographics({...demographics, age: e.target.value})} />
              
              <div className="relative w-full flex items-center border rounded-xl disabled:bg-slate-50 bg-white pr-2">
                <input type="text" placeholder="Passport / National ID" disabled={isLocked} className="p-3 rounded-xl w-full outline-none disabled:bg-slate-50 bg-transparent" 
                  onChange={e => setDemographics({...demographics, passportId: e.target.value})} />
                <Tooltip 
                  id="passport" 
                  title="ID Number Rule" 
                  content="If the patient is not a citizen, an international Passport Number must be entered here." 
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

          {/* CARD 3: Current Vitals */}
          <div className={`md:col-span-1 bg-white rounded-3xl p-6 shadow-sm border ${isLocked ? 'border-green-400 opacity-80' : 'border-slate-200'}`}>
            <h2 className="text-xl font-semibold text-slate-800 mb-4">Current Vitals *</h2>
            <div className="flex flex-col gap-3">
              <input type="number" placeholder="Heart Rate (bpm)" disabled={isLocked} className="border p-3 rounded-xl w-full bg-red-50 focus:bg-white disabled:bg-slate-50" 
                onChange={e => setVitals({...vitals, pulse: e.target.value})} />
              <input type="text" placeholder="Blood Pressure (e.g. 120/80)" disabled={isLocked} className="border p-3 rounded-xl w-full disabled:bg-slate-50" 
                onChange={e => setVitals({...vitals, bloodPressure: e.target.value})} />
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

          {/* CARD 2: Medical History */}
          <div className={`md:col-span-1 bg-white rounded-3xl p-6 shadow-sm border ${isLocked ? 'border-green-400 opacity-80' : 'border-slate-200'}`}>
            <h2 className="text-xl font-semibold text-slate-800 mb-4">Medical History</h2>
            <div className="flex flex-col gap-4">
              <textarea placeholder="Chronic Illnesses (Comma separated)" disabled={isLocked} className="border p-3 rounded-xl w-full h-24 resize-none disabled:bg-slate-50" 
                onChange={e => setMedicalHistory({...medicalHistory, chronicIllness: e.target.value})} />
              <textarea placeholder="Regular Medications" disabled={isLocked} className="border p-3 rounded-xl w-full h-24 resize-none disabled:bg-slate-50" 
                onChange={e => setMedicalHistory({...medicalHistory, regularMedication: e.target.value})} />
            </div>
          </div>

          {/* CARD 4: Clinical Complaint */}
          <div className={`md:col-span-2 bg-white rounded-3xl p-6 shadow-sm border flex flex-col ${isLocked ? 'border-green-400 opacity-80' : 'border-slate-200'}`}>
            <div className="flex items-center mb-4">
              <h2 className="text-xl font-semibold text-slate-800">Clinical Complaint *</h2>
              <Tooltip 
                id="complaintInfo" 
                title="English Terminology Requirement" 
                content="For WatsonX AI analysis quality, the patient's symptoms and main complaint must be written in English medical terminology. (e.g., Chest pain radiating to left arm, acute appendicitis suspect, severe dyspnea)." 
              />
            </div>
            <div className="flex flex-col gap-6 flex-grow">
              <textarea placeholder="Enter complaints using medical English terminology..." disabled={isLocked} className="border p-4 rounded-xl w-full flex-grow resize-none disabled:bg-slate-50" 
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

        {/* Action Bar */}
        <div className="mt-8 flex items-center justify-between bg-white p-4 rounded-2xl shadow-sm border border-slate-200">
          
          <div className="flex-1">
            {errorMsg && <p className="text-red-600 font-bold bg-red-50 p-3 rounded-lg border border-red-200 inline-block">{errorMsg}</p>}
            {isLocked && !isAnalyzing && !analysisResult && <p className="text-green-600 font-bold bg-green-50 p-3 rounded-lg border border-green-200 inline-block">Data locked and verified. Ready for analysis.</p>}
            {isAnalyzing && <p className="text-blue-600 font-bold bg-blue-50 p-3 rounded-lg border border-blue-200 inline-block animate-pulse">WatsonX AI is analyzing data...</p>}
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
                  {isAnalyzing ? 'Analyzing...' : 'Start AI Analysis'}
                </button>
              </>
            )}
          </div>
          
        </div>

        {/* AI Analysis Result Card */}
        {analysisResult && (
          <div className="mt-6 bg-slate-900 text-white rounded-3xl p-8 shadow-xl border-2 border-red-500 transition-all">
            <div className="flex flex-col md:flex-row items-start md:items-center justify-between gap-6 border-b border-slate-700 pb-6 mb-6">
              
              <div className="flex items-center gap-4">
                <div className="flex flex-col items-center justify-center bg-red-600 w-20 h-20 rounded-2xl shadow-inner">
                  <span className="text-xs font-semibold text-red-100 uppercase tracking-wider">Level</span>
                  <span className="text-4xl font-black text-white">{analysisResult.priorityScore}</span>
                </div>
                <div>
                  <h3 className="text-2xl font-bold text-slate-100">AI Triage Result</h3>
                  <p className="text-red-400 font-medium text-lg">{analysisResult.priorityLabel}</p>
                </div>
              </div>

              <div className="bg-slate-800 px-6 py-4 rounded-2xl border border-slate-700">
                <span className="block text-xs text-slate-400 uppercase tracking-wider mb-1">Recommended Department</span>
                <span className="text-lg font-bold text-white">{analysisResult.recommendedPolyclinic}</span>
              </div>

            </div>
            
            <div>
              <span className="block text-sm text-slate-400 uppercase tracking-wider mb-2">WatsonX Clinical Reasoning</span>
              <p className="text-slate-300 text-base leading-relaxed bg-slate-800/50 p-4 rounded-xl">
                {analysisResult.reasoning}
              </p>
            </div>
            
            <div className="mt-6 flex justify-end">
               <button type="button" className="bg-green-600 hover:bg-green-700 text-white font-bold py-3 px-8 rounded-xl transition-all">
                 Confirm & Save to DB
               </button>
            </div>
          </div>
        )}

      </div>
    </div>
  );
}