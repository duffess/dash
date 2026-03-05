import React from 'react';
import { motion } from 'framer-motion';
import { FileText, Download, Eye, Calendar, Megaphone } from 'lucide-react';
import { Button } from '@/components/ui/button';

const ReportCard = ({ report, onExportPDF, onExportHTML }) => {
  return (
    <motion.div
      whileHover={{ y: -2 }}
      className="bg-white rounded-xl border border-slate-200 p-6 hover:shadow-lg transition-shadow"
    >
      <div className="flex items-start gap-4 mb-4">
        <div className="w-12 h-12 bg-[#F5F5F5] rounded-lg flex items-center justify-center flex-shrink-0">
          <FileText className="w-6 h-6 text-[#2563EB]" />
        </div>
        <div className="flex-1">
          <h3 className="text-lg font-semibold text-slate-900 mb-1">{report.name}</h3>
          <div className="flex items-center gap-4 text-sm text-slate-600">
            <div className="flex items-center gap-1">
              <Calendar className="w-4 h-4" />
              {new Date(report.date).toLocaleDateString('pt-BR')}
            </div>
            <div className="flex items-center gap-1">
              <Megaphone className="w-4 h-4" />
              {report.campaigns} campanhas
            </div>
          </div>
        </div>
        <span className="px-3 py-1 bg-[#2563EB]/10 text-[#2563EB] rounded-full text-xs font-medium">
          Concluído
        </span>
      </div>

      <div className="flex gap-2">
        <Button variant="outline" className="flex-1" onClick={onExportPDF}>
          <Download className="w-4 h-4 mr-2" />
          Exportar PDF
        </Button>
        <Button variant="outline" className="flex-1" onClick={onExportHTML}>
          <Download className="w-4 h-4 mr-2" />
          Exportar HTML
        </Button>
      </div>
    </motion.div>
  );
};

export default ReportCard;
