import React from 'react';

export default function Sidebar({ activePage, setActivePage }) {
  const menuItems = [
    { id: 'triage', label: 'Triage Entry' },
    { id: 'queue', label: 'Live Queue' },
    { id: 'history', label: 'Patient History' }
  ];

  return (
    <div className="w-64 bg-slate-900 text-white h-screen flex flex-col">
      <div className="p-6 text-2xl font-bold border-b border-slate-700">
        <span className="text-red-500 mr-2">+</span> PreTriage AI
      </div>
      <div className="flex flex-col p-4 gap-2">
        {menuItems.map(item => (
          <button
            key={item.id}
            onClick={() => setActivePage(item.id)}
            className={`flex items-center p-3 rounded-xl transition-all ${
              activePage === item.id 
                ? 'bg-red-500 text-white shadow-lg' 
                : 'hover:bg-slate-800 text-slate-300'
            }`}
          >
            <span className="font-medium">{item.label}</span>
          </button>
        ))}
      </div>
    </div>
  );
}
