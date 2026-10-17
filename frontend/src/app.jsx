import React, { useState } from 'react';
import Sidebar from './components/Sidebar';
import TriageBentoBox from './components/TriageBentoBox';
import PatientQueue from './components/PatientQueue';
import PatientHistory from './components/PatientHistory';

function App() {
  const [activePage, setActivePage] = useState('triage');

  return (
    <div className="flex h-screen bg-slate-100 font-sans overflow-hidden">

      <Sidebar activePage={activePage} setActivePage={setActivePage} />


      <div className="flex-1 overflow-y-auto p-8">
        {activePage === 'triage' && <TriageBentoBox />}
        {activePage === 'queue' && <PatientQueue />}
        {activePage === 'history' && <PatientHistory />}
      </div>
    </div>
  );
}

export default App;
