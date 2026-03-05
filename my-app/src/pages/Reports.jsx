import React, { useState } from 'react';
import { Helmet } from 'react-helmet';
import { motion } from 'framer-motion';
import Layout from '@/components/Layout';
import ReportCard from '@/reports/ReportCard';
import { Button } from '@/components/ui/button';
import { Plus, FileText } from 'lucide-react';
import { useToast } from '@/components/ui/use-toast';

const Reports = () => {
  const { toast } = useToast();
  const [reports] = useState([
    {
      id: '1',
      name: 'Relatório Semanal - 28 Out a 03 Nov',
      date: '2024-11-03',
      campaigns: 3,
      status: 'completed',
    },
    {
      id: '2',
      name: 'Relatório Mensal - Outubro 2024',
      date: '2024-10-31',
      campaigns: 5,
      status: 'completed',
    },
  ]);

  const handleNewReport = () => {
    toast({
      title: "🚧 Funcionalidade em desenvolvimento",
      description: "A criação de relatórios personalizados estará disponível em breve!",
    });
  };

  const handleExportPDF = () => {
    toast({
      title: "🚧 Exportação em desenvolvimento",
      description: "A exportação em PDF estará disponível em breve!",
    });
  };

  const handleExportHTML = () => {
    toast({
      title: "🚧 Exportação em desenvolvimento",
      description: "A exportação em HTML estará disponível em breve!",
    });
  };

  return (
    <>
      <Helmet>
        <title>Relatórios - DashFlow</title>
        <meta name="description" content="Gere e exporte relatórios profissionais das suas campanhas" />
      </Helmet>
      <Layout>
        <div className="space-y-6">
          <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4">
            <div>
              <h1 className="text-3xl font-bold text-slate-900">Relatórios</h1>
              <p className="text-slate-600 mt-1">Gere relatórios profissionais para seus clientes</p>
            </div>
            <Button onClick={handleNewReport} className="bg-[#2563EB] hover:bg-[#1E4FD1]">
              <Plus className="w-5 h-5 mr-2" />
              Novo Relatório
            </Button>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {reports.map((report, index) => (
              <motion.div
                key={report.id}
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: index * 0.1 }}
              >
                <ReportCard 
                  report={report} 
                  onExportPDF={handleExportPDF}
                  onExportHTML={handleExportHTML}
                />
              </motion.div>
            ))}
          </div>

          {reports.length === 0 && (
            <div className="text-center py-12 bg-white rounded-xl border-2 border-dashed border-slate-300">
              <FileText className="w-16 h-16 text-slate-400 mx-auto mb-4" />
              <p className="text-slate-500 mb-4">Nenhum relatório criado ainda</p>
              <Button onClick={handleNewReport} variant="outline">
                Criar primeiro relatório
              </Button>
            </div>
          )}
        </div>
      </Layout>
    </>
  );
};

export default Reports;
