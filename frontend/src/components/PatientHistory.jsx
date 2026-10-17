import React, { useEffect, useState } from 'react';

const urgencyStyles = {
  5: 'bg-red-100 text-red-700',
  4: 'bg-orange-100 text-orange-700',
  3: 'bg-yellow-100 text-yellow-800',
  2: 'bg-green-100 text-green-700',
  1: 'bg-blue-100 text-blue-700',
};

const urgencyLabels = {
  5: 'Very urgent',
  4: 'Urgent',
  3: 'Moderate urgency',
  2: 'Low urgency',
  1: 'Not urgent',
};

const displayValue = (value) => value === null || value === undefined || value === '' ? 'Not recorded' : value;

export default function PatientHistory() {
  const [records, setRecords] = useState([]);
  const [error, setError] = useState('');
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    let isMounted = true;

    const loadHistory = async () => {
      try {
        const response = await fetch('/api/triage/history');
        const result = await response.json();
        if (!response.ok) {
          throw new Error(result.detail || `Request failed (${response.status}).`);
        }
        if (isMounted) {
          setRecords(Array.isArray(result) ? result : []);
          setError('');
          setIsLoading(false);
        }
      } catch (requestError) {
        if (isMounted) {
          setError(`Could not load patient history: ${requestError.message}`);
          setIsLoading(false);
        }
      }
    };

    loadHistory();
    const refreshTimer = setInterval(loadHistory, 30000);
    return () => {
      isMounted = false;
      clearInterval(refreshTimer);
    };
  }, []);

  return (
    <div className="p-6 flex flex-col items-center min-h-screen">
      <div className="w-full max-w-6xl bg-white rounded-3xl p-6 shadow-sm border border-slate-200">
        <div className="flex flex-wrap justify-between items-center gap-4 mb-6">
          <h2 className="text-2xl font-semibold text-slate-800">Patient History</h2>
          <span className="px-4 py-2 bg-slate-100 rounded-xl text-slate-700 font-semibold">
            Saved records: {records.length}
          </span>
        </div>

        {error && <p className="mb-4 p-3 rounded-lg bg-red-50 text-red-700">{error}</p>}
        {isLoading && <p className="p-8 text-center text-slate-500">Loading patient history...</p>}

        {!isLoading && !error && records.length === 0 && (
          <div className="p-8 text-center text-slate-500 bg-slate-50 rounded-xl border border-slate-100">
            No patient records have been saved yet.
          </div>
        )}

        {records.length > 0 && (
          <div className="overflow-x-auto">
            <table className="w-full min-w-[900px] text-left border-collapse">
              <thead>
                <tr className="bg-slate-100 text-slate-600 text-sm uppercase tracking-wider border-b border-slate-200">
                  <th className="p-4 font-semibold">Date and Time</th>
                  <th className="p-4 font-semibold">Full Name</th>
                  <th className="p-4 font-semibold">Age</th>
                  <th className="p-4 font-semibold">Chief Complaint</th>
                  <th className="p-4 font-semibold">Recommended Department</th>
                  <th className="p-4 font-semibold">Urgency</th>
                  <th className="p-4 font-semibold">Record</th>
                </tr>
              </thead>
              <tbody className="text-slate-700 divide-y divide-slate-100">
                {records.map((record) => {
                  const urgency = record.aciliyet_seviyesi;
                  const patient = record.demografi;
                  const medicalHistory = record.tibbi_gecmis;
                  const vitals = record.vitaller;
                  const complaint = record.sikayet;

                  return (
                    <React.Fragment key={record.log_id}>
                      <tr className="align-top hover:bg-slate-50 transition-colors">
                        <td className="p-4 whitespace-nowrap">
                          <div>{record.tarih}</div>
                          <div className="text-sm text-slate-500">{String(record.saat || '').slice(0, 5)}</div>
                        </td>
                        <td className="p-4 font-medium">{patient.isim}</td>
                        <td className="p-4">{patient.yas}</td>
                        <td className="p-4 max-w-xs">{complaint.ana_sikayet}</td>
                        <td className="p-4">{displayValue(record.onerilen_poliklinik)}</td>
                        <td className="p-4">
                          <span className={`px-3 py-1 rounded-full text-xs font-bold ${urgencyStyles[urgency] || 'bg-slate-100 text-slate-600'}`}>
                            {urgency}/5 · {urgencyLabels[urgency] || 'Unknown'}
                          </span>
                        </td>
                        <td className="p-4">
                          <details>
                            <summary className="cursor-pointer text-sm font-semibold text-blue-700">View details</summary>
                            <div className="fixed inset-0 z-20 flex items-center justify-center bg-slate-950/40 p-4" onClick={(event) => {
                              if (event.target === event.currentTarget) event.currentTarget.closest('details').open = false;
                            }}>
                              <div className="w-full max-w-3xl max-h-[85vh] overflow-y-auto rounded-2xl bg-white p-6 shadow-2xl" onClick={(event) => event.stopPropagation()}>
                                <div className="flex justify-between items-center mb-5">
                                  <h3 className="text-xl font-bold text-slate-800">Patient Record</h3>
                                  <button type="button" className="rounded-lg bg-slate-100 px-3 py-2 text-slate-700" onClick={(event) => {
                                    event.currentTarget.closest('details').open = false;
                                  }}>
                                    Close
                                  </button>
                                </div>
                                <div className="grid gap-4 sm:grid-cols-2">
                                  <section className="rounded-xl bg-slate-50 p-4">
                                    <h4 className="font-semibold text-slate-800">Demographics</h4>
                                    <p>Name: {patient.isim}</p>
                                    <p>Age: {patient.yas}</p>
                                    <p>Height: {displayValue(patient.boy)} cm</p>
                                    <p>Weight: {displayValue(patient.kilo)} kg</p>
                                    <p>Blood type: {patient.kan_grubu === 'BILINMIYOR' ? 'Unknown' : patient.kan_grubu}</p>
                                    <p>ID type: {patient.kimlik_turu === 'TC' ? 'Turkish ID' : 'Passport'}</p>
                                    <p>ID number: {patient.kimlik_no}</p>
                                  </section>
                                  <section className="rounded-xl bg-slate-50 p-4">
                                    <h4 className="font-semibold text-slate-800">Medical History</h4>
                                    <p>Chronic illnesses: {displayValue(medicalHistory.kronik_rahatsizlik)}</p>
                                    <p>Regular medications: {displayValue(medicalHistory.surekli_ilac)}</p>
                                  </section>
                                  <section className="rounded-xl bg-slate-50 p-4">
                                    <h4 className="font-semibold text-slate-800">Current Vitals</h4>
                                    <p>Heart rate: {vitals.nabiz} bpm</p>
                                    <p>Blood pressure: {vitals.tansiyon_sistolik}/{vitals.tansiyon_diastolik} mmHg</p>
                                    <p>Respiration rate: {vitals.solunum} breaths/min</p>
                                    <p>Temperature: {vitals.ates} °C</p>
                                    <p>SpO2: {vitals.spo2}%</p>
                                  </section>
                                  <section className="rounded-xl bg-slate-50 p-4">
                                    <h4 className="font-semibold text-slate-800">Triage Result</h4>
                                    <p>Urgency: {urgency}/5 · {urgencyLabels[urgency] || 'Unknown'}</p>
                                    <p>Department: {displayValue(record.onerilen_poliklinik)}</p>
                                    <p>Pain score: {complaint.agri_skalasi}/10</p>
                                    <p>Explanation: {displayValue(record.aciklama)}</p>
                                  </section>
                                </div>
                              </div>
                            </div>
                          </details>
                        </td>
                      </tr>
                    </React.Fragment>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}
