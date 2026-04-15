import React from 'react';
import { motion } from 'framer-motion';
import { TrendingUp, TrendingDown } from 'lucide-react';

const MetricCard = ({ title, value, change, icon: Icon, color }) => {
  const isPositive = change > 0;
  
  return (
    <motion.div
      whileHover={{ y: -4 }}
      className="architect-card relative p-8 group overflow-hidden"
    >
      {/* Barra de Acento Vertical - Signature Style */}
      <div className="absolute left-0 top-0 bottom-0 w-1 bg-[#2563EB] group-hover:w-2 transition-all duration-300"></div>
      
      <div className="flex items-start justify-between">
        <div>
          <p className="text-[10px] font-black text-[#2563EB] uppercase tracking-[0.2em] mb-3">{title}</p>
          <div className="flex items-baseline gap-2">
            <h3 className="text-xl xl:text-2xl font-bold text-white tracking-tighter whitespace-nowrap" style={{ fontFamily: "'Space Grotesk', sans-serif" }}>
              {value}
            </h3>
          </div>
        </div>
        
        <div className={`flex flex-col items-end gap-1 pr-6`}>
          <div className={`
            flex items-center gap-1 text-xs font-black px-2 py-1 
            ${isPositive ? 'bg-green-500/10 text-green-400' : 'bg-red-500/10 text-red-500'}
          `}>
            {isPositive ? <TrendingUp className="w-3 h-3" /> : <TrendingDown className="w-3 h-3" />}
            {Math.abs(change)}%
          </div>
          <span className="text-[10px] text-slate-500 font-bold uppercase tracking-wider">vs Last Period</span>
        </div>
      </div>

      <div className="mt-8 flex items-center justify-between">
         <div className="flex -space-x-2">
            {[1,2,3].map(i => (
              <div key={i} className="w-6 h-6 bg-[#1E293B] border border-[#0B1326] flex items-center justify-center">
                 <div className="w-2 h-2 bg-[#2563EB]/40"></div>
              </div>
            ))}
         </div>
         <Icon className="w-6 h-6 text-[#2563EB]/30 group-hover:text-[#2563EB] transition-colors" />
      </div>
    </motion.div>
  );
};

export default MetricCard;
