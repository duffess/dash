import React from 'react';
import { Button } from '@/components/ui/button';

export default function ReportCard({ report, onView, onExport, disabled }) {
  return (
    <article className="dash-panel p-6 space-y-3">
      <h2 className="text-lg font-semibold text-slate-100">{report.title}</h2>
      <p className="text-slate-300">{report.client_name} · {report.campaign_count} campanhas</p>
      <p className="text-sm text-slate-400">Janela de {report.period_days} dias · {report.has_analysis ? 'Com análise IA' : 'Métricas'}</p>
      <p className="text-sm text-slate-400">Criado em {new Date(report.created_at.endsWith('Z') ? report.created_at : report.created_at + 'Z').toLocaleString('pt-BR')}</p>
      <div className="flex flex-wrap gap-2">
        <Button disabled={disabled} onClick={() => onView(report.id)}>Visualizar</Button>
        <Button disabled={disabled} variant="outline" onClick={() => onExport(report.id, false)}>HTML</Button>
        <Button disabled={disabled} variant="outline" onClick={() => onExport(report.id, true)}>Imprimir / PDF</Button>
      </div>
    </article>
  );
}
