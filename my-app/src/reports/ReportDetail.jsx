import React from 'react';
import ReactMarkdown from 'react-markdown';
import { Button } from '@/components/ui/button';

const num = (value) => Number(value || 0).toLocaleString('pt-BR', { maximumFractionDigits: 2 });
const utcDate = (value) => value ? new Date(/Z$|[+-]\d\d:\d\d$/.test(value) ? value : value + 'Z').toLocaleString('pt-BR') : 'Não informada';

export default function ReportDetail({ report, onClose, onExport, exporting }) {
  const data = report.snapshot;
  if (report.rendered_html) return (
    <section className="space-y-3" aria-label="Relatório selecionado">
      <div className="flex flex-wrap gap-2 items-center justify-between dash-panel p-4">
        <div><h2 className="font-semibold text-slate-100">{report.title}</h2>
          <p className="text-sm text-slate-300">{data.source === 'demo' ? 'Dados fictícios · Não salvo no histórico real' : 'Retrato dos dados disponíveis na geração'}</p></div>
        <div className="flex flex-wrap gap-2">
          <Button disabled={exporting} onClick={() => onExport(report.id, false)}>Baixar HTML</Button>
          <Button disabled={exporting} variant="outline" onClick={() => onExport(report.id, true)}>Imprimir / Salvar PDF</Button>
          <Button variant="outline" onClick={onClose}>Fechar</Button>
        </div>
      </div>
      <iframe title="Prévia do relatório de performance" sandbox="" srcDoc={report.rendered_html}
        className="w-full rounded-xl border bg-white" style={{ height: 'min(1100px, 80vh)', minHeight: 500 }} />
    </section>
  );
  return (
    <section className="dash-panel p-6 space-y-5" aria-label="Relatório selecionado">
      <div className="flex flex-wrap justify-between gap-3">
        <div><h2 className="text-xl font-semibold text-slate-100">{report.title}</h2>
          <p className="text-slate-300">{report.client_name} · {utcDate(report.created_at)}</p></div>
        <Button variant="outline" onClick={onClose}>Fechar</Button>
      </div>
      <p className="text-sm text-slate-300">{data.period_note}</p>
      <p className="text-sm text-slate-400">{data.currency_note}</p>
      <h3 className="font-semibold text-slate-100">Resumo por conta</h3>
      <div className="grid md:grid-cols-2 gap-3">
        {data.accounts.map((account) => <div key={account.platform + account.account_id} className="border rounded-lg p-4 text-slate-200">
          <p className="font-semibold">{account.platform === 'meta_ads' ? 'Meta Ads' : 'Google Ads'} · {account.account_id || 'Conta não informada'}</p>
          <p>Gasto: {num(account.spend)} · Cliques: {num(account.clicks)}</p>
          <p>Impressões: {num(account.impressions)} · Conversões: {num(account.conversions)}</p>
          <p>CTR: {num(account.ctr)}% · CPC: {num(account.cpc)}</p>
        </div>)}
      </div>
      <div className="overflow-x-auto">
        <table className="w-full text-sm text-left text-slate-200">
          <thead><tr>{['Campanha', 'Plataforma', 'Gasto', 'Cliques', 'Conversões', 'CTR', 'Sincronização'].map((title) => <th className="p-2 border-b" key={title}>{title}</th>)}</tr></thead>
          <tbody>{data.campaigns.map((campaign) => <tr key={campaign.id}>
            <td className="p-2 border-b">{campaign.name}</td><td className="p-2 border-b">{campaign.platform}</td>
            <td className="p-2 border-b">{num(campaign.spend)}</td><td className="p-2 border-b">{num(campaign.clicks)}</td>
            <td className="p-2 border-b">{num(campaign.conversions)}</td><td className="p-2 border-b">{num(campaign.ctr)}%</td>
            <td className="p-2 border-b">{utcDate(campaign.synced_at)}</td>
          </tr>)}</tbody>
        </table>
      </div>
      <p className="text-xs text-slate-400">{data.conversion_note}</p>
      {report.analysis ? <div>
        <h3 className="font-semibold text-slate-100">Análise IA</h3>
        <div className="prose prose-slate max-w-none"><ReactMarkdown skipHtml components={{ img: () => null, a: ({ children }) => <span>{children}</span> }}>{report.analysis}</ReactMarkdown></div>
        <p className="text-xs text-slate-400 mt-3">{report.ai_model} · Recomendações para revisão humana.</p>
      </div> : <p className="text-slate-400">Relatório de métricas, sem análise IA.</p>}
      <div className="flex flex-wrap gap-2">
        <Button disabled={exporting} onClick={() => onExport(report.id, false)}>Baixar HTML</Button>
        <Button disabled={exporting} variant="outline" onClick={() => onExport(report.id, true)}>Imprimir / Salvar PDF</Button>
      </div>
    </section>
  );
}
