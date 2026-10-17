import React from 'react';

export default function Sidebar({ activePage, setActivePage }) {
  const menuItems = [
    { id: 'triage', label: 'Triaj Girişi', icon: '🩺' },
    { id: 'history', label: 'Hasta Geçmişi', icon: '📋' },
    { id: 'summary', label: 'Günlük Özet', icon: '📊' }
  ];

  return (
    <div className="w-64 bg-slate-900 text-white h-screen flex flex-col">
      <div className="p-6 text-2xl font-bold border-b border-slate-700 flex items-center gap-3">
        <span className="text-red-500">✚</span> ÖnTriaj AI
      </div>
      <div className="flex flex-col p-4 gap-2">
        {menuItems.map(item => (
          <button
            key={item.id}
            onClick={() => setActivePage(item.id)}
            className={`flex items-center gap-3 p-3 rounded-xl transition-all ${
              activePage === item.id 
                ? 'bg-red-500 text-white shadow-lg' 
                : 'hover:bg-slate-800 text-slate-300'
            }`}
          >
            <span className="text-xl">{item.icon}</span>
            <span className="font-medium">{item.label}</span>
          </button>
        ))}
      </div>
    </div>
  );
}