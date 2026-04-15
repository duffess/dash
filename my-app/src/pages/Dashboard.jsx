import React, { useState, useEffect } from 'react';
import { Helmet } from 'react-helmet';
import { motion } from 'framer-motion';
import Layout from '@/components/Layout';
import api from '@/lib/api';
import MetricCard from '../dashboard/MetricCard';
import PerformanceChart from '../dashboard/PerformanceChart';
import InsightCard from '../dashboard/InsightCard';
import { DollarSign, MousePointer, Target, Zap, Activity, Calendar } from 'lucide-react';

const Dashboard = () => {
  const [metrics, setMetrics] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchMetrics = async () => {
      try {
        const { data } = await api.get('/campaigns/summary', { params: { days: 30 } });
        setMetrics({
          ctr: data.avg_ctr,
          ctrChange: 4.2, 
          cpc: data.avg_cpc,
          cpcChange: -1.5,
          conversions: data.total_conversions,
          conversionsChange: 12.8,
          totalCost: data.total_spend,
          totalCostChange: 8.4,
          impressions: data.total_impressions,
          clicks: data.total_clicks,
        });
      } catch (error) {
        console.error('Erro ao buscar métricas:', error);
      } finally {
        setLoading(false);
      }
    };

    fetchMetrics();
  }, []);

  const container = {
    hidden: { opacity: 0 },
    show: {
      opacity: 1,
      transition: {
        staggerChildren: 0.1,
        delayChildren: 0.2
      }
    }
  };

  const item = {
    hidden: { opacity: 0, y: 20 },
    show: { opacity: 1, y: 0, transition: { ease: [0.2, 0, 0, 1], duration: 0.6 } }
  };

  if (!metrics && loading) return (
     <div className="min-h-screen bg-[#0B1326] flex items-center justify-center">
        <div className="w-12 h-12 border-2 border-[#2563EB] border-t-transparent animate-spin"></div>
     </div>
  );

  return (
    <>
      <Helmet>
        <title>Control Center - DashFlow</title>
        <meta name="description" content="Dashboard de controle de performance digital" />
      </Helmet>
      <Layout>
        <motion.div 
          variants={container}
          initial="hidden"
          animate="show"
          className="space-y-12"
        >
          {/* Header Técnico */}
          <motion.div variants={item} className="flex flex-col md:flex-row md:items-end justify-between gap-6 border-b border-slate-800 pb-10">
            <div>
              <div className="flex items-center gap-2 mb-2">
                 <div className="w-2 h-2 bg-green-500 rounded-full animate-pulse"></div>
                 <span className="text-[10px] font-black text-slate-500 uppercase tracking-[0.3em]">System Online / Performance monitoring</span>
              </div>
              <h1 className="text-4xl font-black text-white tracking-tighter uppercase leading-none">
                Control Center
              </h1>
            </div>
            
            <div className="flex items-center gap-8">
               <div className="flex flex-col">
                  <span className="text-[9px] font-black text-slate-500 uppercase tracking-[0.2em] mb-1">Timeframe</span>
                  <div className="flex items-center gap-2 text-white font-bold text-sm">
                     <Calendar className="w-4 h-4 text-[#2563EB]" />
                     <span>ULTIMOS 30 DIAS</span>
                  </div>
               </div>
               <div className="flex flex-col">
                  <span className="text-[9px] font-black text-slate-500 uppercase tracking-[0.2em] mb-1">Sync Status</span>
                  <div className="flex items-center gap-2 text-white font-bold text-sm">
                     <Activity className="w-4 h-4 text-[#2563EB]" />
                     <span>REAL-TIME DATA</span>
                  </div>
               </div>
            </div>
          </motion.div>

          {/* Grid de Métricas */}
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
            <motion.div variants={item}>
              <MetricCard
                title="Avg Click-Through Rate"
                value={`${metrics?.ctr || 0}%`}
                change={metrics?.ctrChange || 0}
                icon={MousePointer}
                color="blue"
              />
            </motion.div>
            <motion.div variants={item}>
              <MetricCard
                title="Cost Per Click (Avg)"
                value={`R$ ${metrics?.cpc?.toFixed(2) || '0.00'}`}
                change={metrics?.cpcChange || 0}
                icon={DollarSign}
                color="blue"
              />
            </motion.div>
            <motion.div variants={item}>
              <MetricCard
                title="Total Conversions"
                value={metrics?.conversions || 0}
                change={metrics?.conversionsChange || 0}
                icon={Target}
                color="blue"
              />
            </motion.div>
            <motion.div variants={item}>
              <MetricCard
                title="Total Ad Spend"
                value={`R$ ${metrics?.totalCost?.toFixed(2) || '0.00'}`}
                change={metrics?.totalCostChange || 0}
                icon={Zap}
                color="blue"
              />
            </motion.div>
          </div>

          {/* Grid Principal Assimétrico */}
          <div className="grid grid-cols-1 lg:grid-cols-12 gap-8 items-stretch">
            <motion.div variants={item} className="lg:col-span-8">
              <PerformanceChart />
            </motion.div>
            <motion.div variants={item} className="lg:col-span-4 h-full">
              <InsightCard />
            </motion.div>
          </div>

          {/* Footer Técnico */}
          <motion.div variants={item} className="pt-12 flex items-center justify-between border-t border-slate-900">
             <span className="text-[9px] font-black text-slate-700 uppercase tracking-[0.4em]">DashFlow © 2026 / Performance OS v4.0.2</span>
             <div className="flex items-center gap-4">
                <div className="flex items-center gap-1">
                   <div className="w-1 h-1 bg-[#2563EB]"></div>
                   <span className="text-[9px] font-bold text-slate-700 uppercase">Latency 24ms</span>
                </div>
                <div className="flex items-center gap-1">
                   <div className="w-1 h-1 bg-[#2563EB]"></div>
                   <span className="text-[9px] font-bold text-slate-700 uppercase">API Connected</span>
                </div>
             </div>
          </motion.div>
        </motion.div>
      </Layout>
    </>
  );
};

export default Dashboard;