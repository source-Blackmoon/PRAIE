'use client'

import { motion } from 'framer-motion'
import { type LucideIcon } from 'lucide-react'

interface MetricCardProps {
  label: string
  value: string | number
  icon: LucideIcon
  gradient?: boolean
  color?: string
  delay?: number
}

export function MetricCard({ label, value, icon: Icon, gradient, color, delay = 0 }: MetricCardProps) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4, delay }}
      whileHover={{ scale: 1.02 }}
      className="rounded-2xl p-6 text-white shadow-lg"
      style={{
        background: gradient
          ? 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)'
          : color || 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
      }}
    >
      <div className="flex items-start justify-between">
        <div>
          <p className="text-white/70 text-sm font-medium mb-1">{label}</p>
          <p className="text-4xl font-black tracking-tight">{value}</p>
        </div>
        <div className="p-2.5 bg-white/20 rounded-xl">
          <Icon size={22} />
        </div>
      </div>
    </motion.div>
  )
}
