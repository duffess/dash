import React from 'react';
import { ArrowDown, ArrowUp, Minus } from 'lucide-react';

export function comparison(current, previous, preference) {
  if (!Number.isFinite(current) || !Number.isFinite(previous) || previous < 0 || current < 0) return null;
  if (previous === 0) return current === 0 ? { direction: 'flat', tone: 'neutral', label: 'Sem variação' } : null;
  const change = ((current - previous) / previous) * 100;
  if (change === 0) return { direction: 'flat', tone: 'neutral', label: 'Sem variação' };
  const direction = change > 0 ? 'up' : 'down';
  const tone = preference === 'neutral' ? 'neutral' : (change > 0) === (preference === 'higher') ? 'positive' : 'negative';
  return { direction, tone, label: `${Math.abs(change).toLocaleString('pt-BR', { maximumFractionDigits: 1 })}%` };
}

export default function MetricCard({ title, value, icon: Icon, current, previous, preference = 'neutral', formatValue = String, loading = false }) {
  const result = comparison(current, previous, preference);
  const Direction = result?.direction === 'up' ? ArrowUp : result?.direction === 'down' ? ArrowDown : Minus;
  const description = result && Number.isFinite(previous) ? `Atual: ${formatValue(current)}. Período anterior: ${formatValue(previous)}.` : undefined;
  return <div className="metric-card dash-inset"><p className="metric-label"><Icon size={15} aria-hidden="true" />{title}</p><p className="metric-value">{value}</p>
    {result ? <p className={`metric-comparison metric-comparison--${result.tone}`} title={description} aria-label={`${result.direction === 'flat' ? 'Sem alteração' : `${result.direction === 'up' ? 'Aumento' : 'Redução'} de ${result.label}`} em relação ao período anterior. ${description}`}>
      <Direction size={14} aria-hidden="true" /><strong>{result.label}</strong><span>vs. período anterior</span>
    </p> : <p className="metric-comparison metric-comparison--unavailable">{loading ? 'Carregando comparação…' : 'Sem dados para comparação'}</p>}
  </div>;
}
