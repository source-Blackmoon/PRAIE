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

const WARM_GRADIENTS: Record<string, { bg: string; icon: string; text: string }> = {
  coral: { bg: 'linear-gradient(145deg, #D9502E, #F07040)', icon: '#FAF6F0', text: '#FAF6F0' },
  sand: { bg: 'linear-gradient(145deg, #C9963A, #E8B84B)', icon: '#FFFCF8', text: '#FFFCF8' },
  sage: { bg: 'linear-gradient(145deg, #2E6B62, #1B3E3A)', icon: '#F5E6D3', text: '#F5E6D3' },
  stone: { bg: 'linear-gradient(145deg, #7A6E65, #5A504A)', icon: '#FAF6F0', text: '#FAF6F0' },
  terracotta: { bg: 'linear-gradient(145deg, #A83C1E, #D9502E)', icon: '#FAF6F0', text: '#FAF6F0' },
}

function resolveScheme(color?: string): { bg: string; icon: string; text: string } {
  if (!color) return WARM_GRADIENTS.coral
  // Check if it's a gradient string (old format) and map to warm scheme
  if (color.includes('#10b981') || color.includes('#059669')) return WARM_GRADIENTS.sage
  if (color.includes('#f59e0b') || color.includes('#d97706')) return WARM_GRADIENTS.sand
  if (color.includes('#ef4444') || color.includes('#b91c1c')) return WARM_GRADIENTS.terracotta
  if (color.includes('#8b5cf6') || color.includes('#6d28d9') || color.includes('#764ba2')) return WARM_GRADIENTS.coral
  if (color.includes('#6b7280') || color.includes('#4b5563')) return WARM_GRADIENTS.stone
  return WARM_GRADIENTS.coral
}

export function MetricCard({ label, value, icon: Icon, gradient, color, delay = 0 }: MetricCardProps) {
  const scheme = resolveScheme(gradient ? undefined : color)

  return (
    <motion.div
      initial={{ opacity: 0, y: 16 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.5, delay, ease: [0.25, 0.46, 0.45, 0.94] }}
      whileHover={{ y: -2, transition: { duration: 0.2 } }}
      className="rounded-2xl p-6 relative overflow-hidden"
      style={{
        background: scheme.bg,
        color: scheme.text,
      }}
    >
      {/* Decorative circle */}
      <div
        className="absolute -right-4 -top-4 w-20 h-20 rounded-full"
        style={{ background: 'rgba(255,255,255,0.08)' }}
      />

      <div className="flex items-start justify-between relative z-10">
        <div>
          <p className="text-sm font-medium mb-2" style={{ opacity: 0.8 }}>{label}</p>
          <p
            className="text-3xl font-bold tracking-tight"
            style={{ fontFamily: 'var(--font-display)' }}
          >
            {value}
          </p>
        </div>
        <div
          className="p-2 rounded-xl"
          style={{ background: 'rgba(255,255,255,0.15)' }}
        >
          <Icon size={20} style={{ color: scheme.icon }} />
        </div>
      </div>
    </motion.div>
  )
}
