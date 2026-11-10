import React from 'react';
import { TrendingUp, TrendingDown } from 'lucide-react';
export default function MetricCard({ title, value, change, icon: Icon }) {
  return <div className="metric-card dash-inset"><p className="metric-label"><Icon size={15} aria-hidden="true" />{title}</p><p className="metric-value">{value}</p>
    {Number.isFinite(change) && <p className="text-xs text-slate-300 mt-2 flex items-center gap-1">{change > 0 ? <TrendingUp size={14} /> : <TrendingDown size={14} />}{change > 0 ? '+' : ''}{change}% no período</p>}
  </div>;
}
