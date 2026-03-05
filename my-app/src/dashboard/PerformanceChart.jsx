import React from 'react';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';

const PerformanceChart = () => {
  const data = [
    { date: '28 Out', ctr: 3.1, conversions: 18 },
    { date: '29 Out', ctr: 3.3, conversions: 22 },
    { date: '30 Out', ctr: 3.2, conversions: 19 },
    { date: '31 Out', ctr: 3.5, conversions: 25 },
    { date: '01 Nov', ctr: 3.4, conversions: 21 },
    { date: '02 Nov', ctr: 3.6, conversions: 28 },
    { date: '03 Nov', ctr: 3.8, conversions: 32 },
  ];

  return (
    <div className="bg-white rounded-xl border border-slate-200 p-6">
      <h3 className="text-lg font-semibold text-[#0F172A] mb-4">Desempenho nos Últimos 7 Dias</h3>
      <ResponsiveContainer width="100%" height={300}>
        <LineChart data={data}>
          <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
          <XAxis dataKey="date" stroke="#64748b" />
          <YAxis stroke="#64748b" />
          <Tooltip 
            contentStyle={{ 
              backgroundColor: '#fff', 
              border: '1px solid #e2e8f0',
              borderRadius: '8px',
              boxShadow: '0 4px 6px -1px rgb(0 0 0 / 0.1)'
            }}
          />
          <Line type="monotone" dataKey="ctr" stroke="#2563EB" strokeWidth={2} name="CTR (%)" />
          <Line type="monotone" dataKey="conversions" stroke="#0F172A" strokeWidth={2} name="Conversões" />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
};

export default PerformanceChart;
