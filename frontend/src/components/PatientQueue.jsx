import React, { useEffect, useState } from 'react';

const urgencyStyles = {
  5: { row: 'bg-red-50 border-l-4 border-red-500', badge: 'bg-red-600 text-white', label: 'Very urgent' },
  4: { row: 'bg-orange-50 border-l-4 border-orange-500', badge: 'bg-orange-500 text-white', label: 'Urgent' },
  3: { row: 'bg-yellow-50 border-l-4 border-yellow-400', badge: 'bg-yellow-400 text-slate-900', label: 'Moderate urgency' },
  2: { row: 'bg-green-50 border-l-4 border-green-500', badge: 'bg-green-500 text-white', label: 'Low urgency' },
  1: { row: 'bg-blue-50 border-l-4 border-blue-500', badge: 'bg-blue-500 text-white', label: 'Not urgent' },
};

export default function PatientQueue() {
  const [patients, setPatients] = useState([]);
  const [error, setError] = useState('');
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    let isMounted = true;

    const loadQueue = async () => {
      try {
        const response = await fetch('/api/triage?limit=500');
        const result = await response.json();
        if (!response.ok) {
          throw new Error(result.detail || `Request failed (${response.status}).`);
        }
        if (isMounted) {
          setPatients(Array.isArray(result) ? result : []);
          setError('');
          setIsLoading(false);
        }
      } catch (requestError) {
        if (isMounted) {
          setError(`Could not load the live queue: ${requestError.message}`);
          setIsLoading(false);
        }
      }
    };

    loadQueue();
    const refreshTimer = setInterval(loadQueue, 10000);
    return () => {
      isMounted = false;
      clearInterval(refreshTimer);
    };
  }, []);

  const sortedPatients = [...patients].sort((a, b) =>
    b.aciliyet_seviyesi - a.aciliyet_seviyesi || a.sira_no - b.sira_no
  );

  return (
    <div className="p-6 flex flex-col items-center min-h-screen">
      <div className="w-full max-w-6xl bg-white rounded-3xl p-8 shadow-sm border border-slate-200">
        <div className="flex flex-wrap justify-between items-center gap-4 mb-8 border-b border-slate-200 pb-4">
          <div>
            <h2 className="text-3xl font-bold text-slate-800">Live Patient Queue</h2>
            <p className="text-slate-500 mt-1">Patients are ordered from highest to lowest urgency.</p>
          </div>
          <div className="bg-slate-900 text-white px-6 py-3 rounded-xl font-semibold shadow-md">
            Patients today: {sortedPatients.length}
          </div>
        </div>

        {error && <p className="mb-4 p-3 rounded-lg bg-red-50 text-red-700">{error}</p>}

        <div className="overflow-x-auto">
          <div className="min-w-[760px] flex flex-col gap-3">
            <div className="grid grid-cols-12 gap-4 px-5 py-3 bg-slate-100 rounded-xl text-sm font-bold text-slate-500 uppercase tracking-wider">
              <div className="col-span-1 text-center">Queue</div>
              <div className="col-span-3">Patient</div>
              <div className="col-span-4">Chief Complaint</div>
              <div className="col-span-2 text-center">Time</div>
              <div className="col-span-2 text-right">Urgency</div>
            </div>

            {sortedPatients.map((patient) => {
              const styles = urgencyStyles[patient.aciliyet_seviyesi] || {
                row: 'bg-slate-50 border-l-4 border-slate-300',
                badge: 'bg-slate-400 text-white',
                label: 'Unknown',
              };

              return (
                <div key={patient.log_id} className={`grid grid-cols-12 gap-4 items-center px-5 py-4 rounded-2xl shadow-sm ${styles.row}`}>
                  <div className="col-span-1 text-center font-black text-xl text-slate-700">#{patient.sira_no}</div>
                  <div className="col-span-3 font-semibold text-slate-800">{patient.isim}</div>
                  <div className="col-span-4 text-slate-600 truncate" title={patient.ana_sikayet}>{patient.ana_sikayet}</div>
                  <div className="col-span-2 text-center font-semibold text-slate-600">{String(patient.saat || '').slice(0, 5)}</div>
                  <div className="col-span-2 flex justify-end">
                    <div className={`px-3 py-2 rounded-xl font-bold flex items-center gap-2 shadow-sm ${styles.badge}`}>
                      <span>{patient.aciliyet_seviyesi}/5</span>
                      <span>{styles.label}</span>
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        </div>

        {!isLoading && !error && sortedPatients.length === 0 && (
          <div className="p-12 text-center text-slate-500 bg-slate-50 rounded-2xl mt-4 border border-slate-100 font-medium">
            The queue is currently empty.
          </div>
        )}
        {isLoading && <p className="p-8 text-center text-slate-500">Loading the live queue...</p>}
      </div>
    </div>
  );
}
