'use client'

import { useState, useEffect } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { AlertTriangle, CheckCircle, Clock, Phone, MessageSquare } from 'lucide-react'
import { api } from '@/lib/api'
import { formatDate, formatPhone } from '@/lib/utils'

interface Escalacion {
  id: number
  telefono: string
  razon: string
  resumen: string
  estado: string
  timestamp: string
}

export default function EscalacionesPage() {
  const [estado, setEstado] = useState<'pendiente' | 'resuelta'>('pendiente')
  const [escalaciones, setEscalaciones] = useState<Escalacion[]>([])
  const [loading, setLoading] = useState(true)
  const [resolviendo, setResolviendo] = useState<number | null>(null)

  const cargar = async () => {
    setLoading(true)
    try {
      const data = await api.escalaciones(estado)
      setEscalaciones(data)
    } catch {
      setEscalaciones([])
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { cargar() }, [estado])

  const resolver = async (id: number) => {
    setResolviendo(id)
    try {
      await api.resolverEscalacion(id)
      setEscalaciones(prev => prev.filter(e => e.id !== id))
    } finally {
      setResolviendo(null)
    }
  }

  return (
    <div>
      <div className="mb-10">
        <motion.h1
          initial={{ opacity: 0, x: -10 }}
          animate={{ opacity: 1, x: 0 }}
          className="heading-display gradient-text"
          style={{ fontSize: '2.25rem' }}
        >
          Escalaciones
        </motion.h1>
        <p className="text-sm mt-2" style={{ color: 'var(--color-text-muted)' }}>
          Casos que Laura no pudo resolver y necesitan atencion humana
        </p>
      </div>

      {/* Tabs */}
      <div className="flex gap-2 mb-6">
        {(['pendiente', 'resuelta'] as const).map((tab) => (
          <button
            key={tab}
            onClick={() => setEstado(tab)}
            className="card"
            style={{
              padding: '8px 20px',
              background: estado === tab ? 'var(--color-card)' : 'transparent',
              border: estado === tab ? '1px solid var(--color-primary)' : '1px solid var(--color-border)',
              color: estado === tab ? 'var(--color-primary)' : 'var(--color-text-muted)',
              fontWeight: estado === tab ? 600 : 400,
              fontSize: 14, cursor: 'pointer',
              boxShadow: estado === tab ? '0 2px 8px rgba(194, 97, 75, 0.1)' : 'none',
            }}
          >
            {tab === 'pendiente' ? 'Pendientes' : 'Resueltas'}
            {tab === 'pendiente' && escalaciones.length > 0 && estado === 'pendiente' && (
              <span className="ml-2 px-1.5 py-0.5 rounded-full text-xs text-white gradient-bg" style={{ fontSize: 10 }}>
                {escalaciones.length}
              </span>
            )}
          </button>
        ))}
      </div>

      {/* Content */}
      {loading ? (
        <div className="flex items-center justify-center py-20">
          <div className="w-6 h-6 rounded-full border-2 animate-spin" style={{ borderColor: 'var(--color-muted)', borderTopColor: 'var(--color-primary)' }} />
        </div>
      ) : escalaciones.length === 0 ? (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          className="text-center py-20"
        >
          <CheckCircle size={48} style={{ color: '#d4c4b0', margin: '0 auto 12px' }} />
          <p className="text-sm font-medium" style={{ color: 'var(--color-text-muted)' }}>
            {estado === 'pendiente'
              ? 'No hay escalaciones pendientes. Laura esta resolviendo todo sola.'
              : 'No hay escalaciones resueltas en este periodo.'}
          </p>
        </motion.div>
      ) : (
        <div className="space-y-3">
          <AnimatePresence>
            {escalaciones.map((esc) => (
              <motion.div
                key={esc.id}
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, x: -100 }}
                className="card p-5"
                style={{
                  borderLeft: estado === 'pendiente'
                    ? '3px solid #c49230'
                    : '3px solid #5a8a6e',
                }}
              >
                <div className="flex items-start justify-between">
                  <div className="flex-1">
                    <div className="flex items-center gap-3 mb-2">
                      <div
                        className="p-2 rounded-xl"
                        style={{
                          background: estado === 'pendiente' ? '#fef3e2' : '#e8f0eb',
                        }}
                      >
                        {estado === 'pendiente' ? (
                          <AlertTriangle size={16} style={{ color: '#c49230' }} />
                        ) : (
                          <CheckCircle size={16} style={{ color: '#5a8a6e' }} />
                        )}
                      </div>
                      <div>
                        <p className="font-bold text-sm" style={{ color: 'var(--color-text)' }}>
                          {esc.razon}
                        </p>
                        <div className="flex items-center gap-3 mt-0.5">
                          <span className="flex items-center gap-1 text-xs" style={{ color: 'var(--color-text-muted)' }}>
                            <Phone size={11} /> {formatPhone(esc.telefono)}
                          </span>
                          <span className="flex items-center gap-1 text-xs" style={{ color: 'var(--color-text-muted)' }}>
                            <Clock size={11} /> {formatDate(esc.timestamp)}
                          </span>
                        </div>
                      </div>
                    </div>

                    {esc.resumen && (
                      <div className="ml-11 mt-2 p-3 rounded-xl" style={{ background: 'var(--color-muted)' }}>
                        <div className="flex items-center gap-1.5 mb-1">
                          <MessageSquare size={12} style={{ color: 'var(--color-primary)' }} />
                          <span className="text-xs font-semibold" style={{ color: 'var(--color-text)' }}>
                            Resumen de Laura
                          </span>
                        </div>
                        <p className="text-sm" style={{ color: 'var(--color-text-muted)' }}>
                          {esc.resumen}
                        </p>
                      </div>
                    )}
                  </div>

                  {estado === 'pendiente' && (
                    <button
                      onClick={() => resolver(esc.id)}
                      disabled={resolviendo === esc.id}
                      className="flex items-center gap-1.5 px-4 py-2 rounded-xl text-sm font-semibold"
                      style={{
                        background: '#e8f0eb', color: '#3d6b4f',
                        border: 'none', cursor: resolviendo === esc.id ? 'default' : 'pointer',
                        opacity: resolviendo === esc.id ? 0.6 : 1,
                        whiteSpace: 'nowrap',
                      }}
                    >
                      {resolviendo === esc.id ? (
                        <div className="w-4 h-4 rounded-full border-2 animate-spin" style={{ borderColor: '#a8d4b8', borderTopColor: '#3d6b4f' }} />
                      ) : (
                        <CheckCircle size={14} />
                      )}
                      Resolver
                    </button>
                  )}
                </div>
              </motion.div>
            ))}
          </AnimatePresence>
        </div>
      )}
    </div>
  )
}
