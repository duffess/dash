import React from 'react';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';

const PerformanceChart = () => {
  const data = [];

  const CustomTooltip = ({ active, payload, label }) => {
    if (active && payload && payload.length) {
      return (
        <div className="bg-[#131B2E] border border-white/10 p-4 shadow-2xl backdrop-blur-xl">
          <p className="text-[10px] font-black text-[#2563EB] uppercase tracking-[0.2em] mb-2">{label}</p>
          {payload.map((item, index) => (
            <div key={index} className="flex items-center justify-between gap-4 mt-1">
              <span className="text-xs text-slate-400 font-bold uppercase tracking-wider">{item.name}:</span>
              <span className="text-sm font-black text-white">{item.value}{item.name.includes('%') ? '%' : ''}</span>
            </div>
          ))}
        </div>
      );
    }
    return null;
  };

  return (
    <div className="architect-card bg-[#131B2E] p-10 flex flex-col h-full group">
      <div className="flex items-center justify-between mb-10">
        <div>
          <h3 className="text-sm font-black text-white uppercase tracking-[0.2em]">Fluxo de Performance</h3>
          <p className="text-[10px] text-slate-500 font-bold uppercase tracking-widest mt-1">Últimos 7 dias de atividade</p>
        </div>
        <div className="flex items-center gap-4">
           <div className="flex items-center gap-2">
              <div className="w-2 h-2 border border-[#2563EB]"></div>
              <span className="text-[9px] font-black text-slate-400 uppercase tracking-widest">CTR %</span>
           </div>
           <div className="flex items-center gap-2">
              <div className="w-2 h-2 bg-white"></div>
              <span className="text-[9px] font-black text-slate-400 uppercase tracking-widest">Conversões</span>
           </div>
        </div>
      </div>
      
      <div className="flex-1 w-full min-h-[300px]">
        {data.length === 0 ? <p className="text-slate-400 text-sm py-16 text-center">Histórico diário ainda indisponível. As métricas acima mostram os totais sincronizados.</p> : <ResponsiveContainer width="100%" height="100%">
          <LineChart data={data} margin={{ top: 5, right: 30, left: -20, bottom: 5 }}>
            <CartesianGrid strokeDasharray="0" stroke="#1E293B" vertical={false} />
            <XAxis 
              dataKey="date" 
              stroke="#475569" 
              fontSize={10} 
              fontFamily="'Space Grotesk', sans-serif"
              fontWeight={700}
              tickLine={false}
              axisLine={false}
              dy={15}
            />
            <YAxis 
              stroke="#475569" 
              fontSize={10} 
              fontFamily="'Space Grotesk', sans-serif"
              fontWeight={700}
              tickLine={false}
              axisLine={false}
              dx={-5}
            />
            <Tooltip content={<CustomTooltip />} cursor={{ stroke: '#2563EB', strokeWidth: 1, strokeDasharray: '4 4' }} />
            <Line 
              type="monotone" 
              dataKey="ctr" 
              stroke="#2563EB" 
              strokeWidth={4} 
              dot={{ r: 0 }} 
              activeDot={{ r: 6, fill: '#2563EB', stroke: '#0B1326', strokeWidth: 2 }}
              name="CTR (%)" 
            />
            <Line 
              type="monotone" 
              dataKey="conversions" 
              stroke="#F1F5F9" 
              strokeWidth={2} 
              strokeDasharray="5 5"
              dot={{ r: 0 }} 
              activeDot={{ r: 4, fill: '#fff' }}
              name="Conversões" 
            />
          </LineChart>
        </ResponsiveContainer>}
      </div>
      
      <div className="mt-6 flex items-center justify-end text-[9px] text-slate-600 font-bold uppercase tracking-[0.2em]">
          DATA ANALYTICS NODE / AC-1
      </div>
    </div>
  );
};

export default PerformanceChart;
