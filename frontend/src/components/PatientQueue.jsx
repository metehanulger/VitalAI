import React from 'react';

export default function PatientQueue() {
  const mockPatients = [
    { id: '8942', name: 'John Doe', time: '14:30', priority: 2 },
    { id: '3719', name: 'Jane Smith', time: '15:15', priority: 4 },
    { id: '1055', name: 'Alice Johnson', time: '09:45', priority: 1 },
    { id: '9921', name: 'Michael Brown', time: '14:40', priority: 2 },
    { id: '7634', name: 'Emma Davis', time: '16:00', priority: 5 },
    { id: '4488', name: 'David Wilson', time: '14:15', priority: 3 },
  ];

  const sortedPatients = [...mockPatients].sort((a, b) => {
    if (a.priority !== b.priority) {
      return a.priority - b.priority; 
    }
    return a.time.localeCompare(b.time); 
  });

  const formatPatientIdentity = (name, id) => {
    const namePrefix = name.substring(0, 2).toUpperCase();
    const idSuffix = String(id).slice(-2);
    return `${namePrefix}***${idSuffix}`;
  };

  const getPriorityStyles = (level) => {
    switch(level) {
      case 1: return { row: 'bg-red-50 border-l-4 border-red-500', badge: 'bg-red-600 text-white', label: 'Level 1 - Resuscitation' };
      case 2: return { row: 'bg-orange-50 border-l-4 border-orange-500', badge: 'bg-orange-500 text-white', label: 'Level 2 - Emergent' };
      case 3: return { row: 'bg-yellow-50 border-l-4 border-yellow-400', badge: 'bg-yellow-400 text-slate-900', label: 'Level 3 - Urgent' };
      case 4: return { row: 'bg-green-50 border-l-4 border-green-500', badge: 'bg-green-500 text-white', label: 'Level 4 - Less Urgent' };
      case 5: return { row: 'bg-blue-50 border-l-4 border-blue-500', badge: 'bg-blue-500 text-white', label: 'Level 5 - Non Urgent' };
      default: return { row: 'bg-slate-50', badge: 'bg-slate-400 text-white', label: 'Unknown' };
    }
  };

  return (
    <div className="p-6 flex flex-col items-center min-h-screen">
      <div className="w-full max-w-5xl bg-white rounded-3xl p-8 shadow-sm border border-slate-200">
        
        <div className="flex justify-between items-center mb-8 border-b border-slate-200 pb-4">
          <div>
            <h2 className="text-3xl font-bold text-slate-800">Live Patient Queue</h2>
            <p className="text-slate-500 mt-1">Patients are sorted by AI priority score, followed by registration time.</p>
          </div>
          <div className="bg-slate-900 text-white px-6 py-3 rounded-xl font-semibold shadow-md">
            Total Waiting: {sortedPatients.length}
          </div>
        </div>

        <div className="flex flex-col gap-4">
          <div className="grid grid-cols-12 gap-4 px-6 py-3 bg-slate-100 rounded-xl text-sm font-bold text-slate-500 uppercase tracking-wider">
            <div className="col-span-2 text-center">Queue</div>
            <div className="col-span-3">Patient Code</div>
            <div className="col-span-3 text-center">Time</div>
            <div className="col-span-4 text-right">Priority Level</div>
          </div>

          {sortedPatients.map((patient, index) => {
            const styles = getPriorityStyles(patient.priority);
            
            return (
              <div key={patient.id} className={`grid grid-cols-12 gap-4 items-center px-6 py-5 rounded-2xl transition-all shadow-sm ${styles.row}`}>
                <div className="col-span-2 text-center font-black text-2xl text-slate-700">
                  #{index + 1}
                </div>
                <div className="col-span-3 font-mono text-xl font-bold tracking-widest text-slate-800">
                  {formatPatientIdentity(patient.name, patient.id)}
                </div>
                <div className="col-span-3 text-center font-semibold text-slate-600 text-lg">
                  {patient.time}
                </div>
                <div className="col-span-4 flex justify-end">
                  <div className={`px-4 py-2 rounded-xl font-bold flex items-center gap-3 shadow-sm ${styles.badge}`}>
                    <span className="bg-white/20 px-2 py-1 rounded-lg text-sm">P{patient.priority}</span>
                    <span>{styles.label}</span>
                  </div>
                </div>
              </div>
            );
          })}
        </div>

        {sortedPatients.length === 0 && (
          <div className="p-12 text-center text-slate-500 bg-slate-50 rounded-2xl mt-4 border border-slate-100 font-medium">
            The queue is currently empty.
          </div>
        )}
      </div>
    </div>
  );
}