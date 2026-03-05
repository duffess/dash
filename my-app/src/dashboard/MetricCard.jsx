import React from 'react';
import { motion } from 'framer-motion';
import { TrendingUp, TrendingDown } from 'lucide-react';

const MetricCard = ({ title, value, change, icon: Icon, color }) => {
  const isPositive = change > 0;
  
  const colorClasses = {
    blue: 'bg-[#F5F5F5] text-[#2563EB]',
    green: 'bg-[#F5F5F5] text-[#2563EB]',
    purple: 'bg-[#F5F5F5] text-[#2563EB]',
    orange: 'bg-[#F5F5F5] text-[#2563EB]',
  };

  return (
    <motion.div
      whileHover={{ y: -4 }}
      className="bg-white rounded-xl border border-slate-200 p-6 hover:shadow-lg transition-shadow"
    >
      <div className="flex items-center justify-between mb-4">
        <div className={`w-12 h-12 rounded-lg flex items-center justify-center ${colorClasses[color]}`}>
          <Icon className="w-6 h-6" />
        </div>
        <div className={`flex items-center gap-1 text-sm font-medium ${isPositive ? 'text-[#2563EB]' : 'text-[#0F172A]'}`}>
          {isPositive ? <TrendingUp className="w-4 h-4" /> : <TrendingDown className="w-4 h-4" />}
          {Math.abs(change)}%
        </div>
      </div>
      <p className="text-slate-600 text-sm mb-1">{title}</p>
      <p className="text-2xl font-bold text-[#0F172A]">{value}</p>
    </motion.div>
  );
};

export default MetricCard;
