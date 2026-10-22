import api from '@/lib/api';

export async function exportReport(reportId, print = false, renderedHTML = null) {
  // Open synchronously from the click to avoid the browser's popup blocker.
  const preview = print ? window.open('', '_blank') : null;
  if (print && !preview) throw new Error('Permita pop-ups para abrir a impressão em PDF.');
  if (preview) {
    preview.opener = null;
    preview.document.body.textContent = 'Preparando relatório para impressão...';
  }
  try {
    const data = renderedHTML ?? (await api.get(`/reports/${reportId}/html`, { responseType: 'text' })).data;
    if (print) {
      if (preview.closed) return;
      preview.document.open();
      preview.document.write(data);
      preview.document.close();
      preview.focus();
      setTimeout(() => { if (!preview.closed) preview.print(); }, 300);
    } else {
      const url = URL.createObjectURL(new Blob([data], { type: 'text/html;charset=utf-8' }));
      const link = document.createElement('a');
      link.href = url;
      link.download = `dashflow-report-${reportId}.html`;
      document.body.appendChild(link);
      link.click();
      link.remove();
      setTimeout(() => URL.revokeObjectURL(url), 1000);
    }
  } catch (error) {
    if (preview) preview.close();
    throw error;
  }
}
