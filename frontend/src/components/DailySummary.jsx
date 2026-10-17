import React from 'react';

export default function DailySummary() {
  return (
    <div className="p-6 flex flex-col items-center min-h-screen">
      <div className="w-full max-w-6xl bg-white rounded-3xl p-6 shadow-sm border border-slate-200">
        <h2 className="text-2xl font-semibold text-slate-800 mb-4">Daily Summary</h2>
        <div className="p-4 bg-slate-50 rounded-xl border text-slate-600">
          Daily triage statistics and AI analysis logs will be displayed here.
        </div>
      </div>
    </div>
  );
}