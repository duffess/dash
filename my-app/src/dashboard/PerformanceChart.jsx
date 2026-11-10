import React from 'react';
import { BarChart3 } from 'lucide-react';
export default function PerformanceChart() {
  return <section className="dash-panel history-panel"><div className="panel-heading"><div><h2>Evolução de resultados</h2><p>Histórico diário de performance</p></div><span className="dash-chip">Ainda indisponível</span></div><div className="empty-state"><BarChart3 aria-hidden="true" /><h3>O histórico ainda não está disponível</h3><p>Hoje, o DASH reúne totais de uma janela de 30 dias por sincronização. A evolução diária será exibida quando esse histórico estiver disponível.</p></div></section>;
}
