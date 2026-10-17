import React from 'react';

export default function PatientHistory() {
  // Örnek sahte veriler (İleride DB'den gelecek)
  const mockPatients = [
    { id: '1001', name: 'John Doe', date: '2026-10-17', time: '14:30', priority: 'High' },
    { id: '1002', name: 'Jane Smith', date: '2026-10-17', time: '15:15', priority: 'Medium' },
    { id: '1003', name: 'Alice Johnson', date: '2026-10-16', time: '09:45', priority: 'Low' },
  ];

  const handleEditClick = (id) => {
    // İleride bu fonksiyon, seçilen hastanın verilerini çekip 
    // Triage Entry formuna yerleştirmek için kullanılacak.
    console.log(`Editing patient with ID: ${id}`);
    alert(`Edit mode activated for Patient ID: ${id}. (Routing will be implemented later)`);
  };

  return (
    <div className="p-6 flex flex-col items-center min-h-screen">
      <div className="w-full max-w-6xl bg-white rounded-3xl p-6 shadow-sm border border-slate-200">
        <h2 className="text-2xl font-semibold text-slate-800 mb-6">Patient History</h2>
        
        <div className="overflow-x-auto">
          <table className="w-full text-left border-collapse">
            <thead>
              <tr className="bg-slate-100 text-slate-600 text-sm uppercase tracking-wider border-b border-slate-200">
                <th className="p-4 font-semibold rounded-tl-xl">ID</th>
                <th className="p-4 font-semibold">Full Name</th>
                <th className="p-4 font-semibold">Date</th>
                <th className="p-4 font-semibold">Time</th>
                <th className="p-4 font-semibold">Priority</th>
                <th className="p-4 font-semibold text-center rounded-tr-xl">Action</th>
              </tr>
            </thead>
            <tbody className="text-slate-700 divide-y divide-slate-100">
              {mockPatients.map((patient) => (
                <tr key={patient.id} className="hover:bg-slate-50 transition-colors">
                  <td className="p-4 font-medium">{patient.id}</td>
                  <td className="p-4">{patient.name}</td>
                  <td className="p-4">{patient.date}</td>
                  <td className="p-4">{patient.time}</td>
                  <td className="p-4">
                    <span className={`px-3 py-1 rounded-full text-xs font-bold ${
                      patient.priority === 'High' ? 'bg-red-100 text-red-700' :
                      patient.priority === 'Medium' ? 'bg-orange-100 text-orange-700' :
                      'bg-green-100 text-green-700'
                    }`}>
                      {patient.priority}
                    </span>
                  </td>
                  <td className="p-4 text-center">
                    <button 
                      onClick={() => handleEditClick(patient.id)}
                      className="bg-slate-200 hover:bg-slate-300 text-slate-700 px-4 py-2 rounded-lg text-sm font-semibold transition-colors"
                    >
                      Edit
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        
        {mockPatients.length === 0 && (
          <div className="p-8 text-center text-slate-500 bg-slate-50 rounded-xl mt-4 border border-slate-100">
            No patient history found.
          </div>
        )}
      </div>
    </div>
  );
}