import React from 'react';

export default function PatientHistory() {
  // Örnek mock veriler (Veritabanından gelecek olan)
  const patients = [
    { id: 'TRJ-001', name: 'Ahmet Yılmaz', date: '17.10.2026', time: '14:30', priority: 1 },
    { id: 'TRJ-002', name: 'Ayşe Demir', date: '17.10.2026', time: '14:45', priority: 3 },
    { id: 'TRJ-003', name: 'Mehmet Kaya', date: '17.10.2026', time: '15:10', priority: 5 },
    { id: 'TRJ-004', name: 'Fatma Şahin', date: '17.10.2026', time: '15:25', priority: 2 },
  ];

  const getPriorityColor = (priority) => {
    if(priority === 1) return 'bg-red-100 text-red-700 border-red-200';
    if(priority === 2 || priority === 3) return 'bg-yellow-100 text-yellow-700 border-yellow-200';
    return 'bg-green-100 text-green-700 border-green-200';
  };

  return (
    <div className="w-full max-w-6xl">
      <h2 className="text-2xl font-bold text-slate-800 mb-6">Hasta Geçmişi (Son 24 Saat)</h2>
      <div className="bg-white rounded-3xl shadow-sm border border-slate-200 overflow-hidden">
        <table className="w-full text-left">
          <thead className="bg-slate-50 border-b border-slate-200">
            <tr>
              <th className="p-4 font-semibold text-slate-600">ID</th>
              <th className="p-4 font-semibold text-slate-600">Hasta İsim Soyisim</th>
              <th className="p-4 font-semibold text-slate-600">Tarih</th>
              <th className="p-4 font-semibold text-slate-600">Saat</th>
              <th className="p-4 font-semibold text-slate-600">Öncelik Derecesi</th>
            </tr>
          </thead>
          <tbody>
            {patients.map((patient) => (
              <tr key={patient.id} className="border-b border-slate-100 hover:bg-slate-50">
                <td className="p-4 text-slate-500 font-mono">{patient.id}</td>
                <td className="p-4 font-medium text-slate-800">{patient.name}</td>
                <td className="p-4 text-slate-600">{patient.date}</td>
                <td className="p-4 text-slate-600">{patient.time}</td>
                <td className="p-4">
                  <span className={`px-3 py-1 rounded-full text-sm font-semibold border ${getPriorityColor(patient.priority)}`}>
                    Skor: {patient.priority}
                  </span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}