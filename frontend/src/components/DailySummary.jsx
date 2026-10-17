import React from 'react';

export default function DailySummary() {
  return (
    <div className="w-full max-w-6xl">
      <h2 className="text-2xl font-bold text-slate-800 mb-6">Günlük Triaj Özeti</h2>
      
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        
        {/* KART 1: Toplam Hasta */}
        <div className="bg-white p-6 rounded-3xl shadow-sm border border-slate-200 flex flex-col justify-center items-center h-48">
          <h3 className="text-lg font-medium text-slate-500 mb-2">Bugün Gelen Hasta</h3>
          <p className="text-6xl font-bold text-slate-800">142</p>
          <span className="text-green-500 text-sm font-medium mt-2">↑ Düne göre %12 artış</span>
        </div>

        {/* KART 2: Poliklinik Yoğunluğu */}
        <div className="bg-white p-6 rounded-3xl shadow-sm border border-slate-200 h-48 flex flex-col justify-between">
          <h3 className="text-lg font-medium text-slate-500">AI Poliklinik Önerileri</h3>
          <div className="flex flex-col gap-2 w-full mt-4">
            <div className="flex justify-between items-center text-sm">
              <span className="font-medium">Acil Travma</span>
              <span className="text-red-500 font-bold">%45</span>
            </div>
            <div className="w-full bg-slate-100 rounded-full h-2">
              <div className="bg-red-500 h-2 rounded-full" style={{ width: '45%' }}></div>
            </div>
            
            <div className="flex justify-between items-center text-sm mt-2">
              <span className="font-medium">Kardiyoloji</span>
              <span className="text-yellow-500 font-bold">%30</span>
            </div>
            <div className="w-full bg-slate-100 rounded-full h-2">
              <div className="bg-yellow-500 h-2 rounded-full" style={{ width: '30%' }}></div>
            </div>
          </div>
        </div>

        {/* KART 3: Yaş Dağılımı Özeti */}
        <div className="bg-white p-6 rounded-3xl shadow-sm border border-slate-200 h-48">
          <h3 className="text-lg font-medium text-slate-500 mb-4">Yaş Verisi Özeti</h3>
          <div className="grid grid-cols-3 gap-2 text-center mt-6">
            <div>
              <p className="text-2xl font-bold text-slate-700">28</p>
              <p className="text-xs text-slate-400 font-medium uppercase mt-1">0-18 Yaş</p>
            </div>
            <div className="border-l border-r border-slate-100">
              <p className="text-2xl font-bold text-slate-700">84</p>
              <p className="text-xs text-slate-400 font-medium uppercase mt-1">19-64 Yaş</p>
            </div>
            <div>
              <p className="text-2xl font-bold text-slate-700">30</p>
              <p className="text-xs text-slate-400 font-medium uppercase mt-1">65+ Yaş</p>
            </div>
          </div>
        </div>

      </div>
    </div>
  );
}