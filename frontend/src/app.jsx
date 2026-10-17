import React, { useState } from 'react';
import Sidebar from './components/Sidebar';
import TriageBentoBox from './components/TriageBentoBox';
import PatientHistory from './components/PatientHistory';
import DailySummary from './components/DailySummary';

function App() {
  // Varsayılan açılış sayfası 'triage'
  const [activePage, setActivePage] = useState('triage');

  return (
    <div className="flex h-screen bg-slate-100 font-sans overflow-hidden">
      {/* Sol Menü */}
      <Sidebar activePage={activePage} setActivePage={setActivePage} />
      
      {/* Sağ İçerik Alanı */}
      <div className="flex-1 overflow-y-auto p-8">
        {activePage === 'triage' && <TriageBentoBox />}
        {activePage === 'history' && <PatientHistory />}
        {activePage === 'summary' && <DailySummary />}
      </div>
    </div>
  );
}

export default App;