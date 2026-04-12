'use client'

import { useEffect, useState } from 'react'
import { motion } from 'framer-motion'
import {
  MessageSquare, Users, BarChart3, AlertTriangle, RefreshCw, ShoppingCart, TrendingUp, DollarSign, Handshake,
} from 'lucide-react'
import {
  LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
} from 'recharts'
import { MetricCard } from '@/components/MetricCard'
import { api } from '@/lib/api'
import type { Conversion, Metricas } from '@/types'
import { formatDate } from '@/lib/utils'

function parseCOP(valor: string): number {
  const limpio = valor.replace(/[^0-9]/g, '')
  return limpio ? parseInt(limpio, 10) : 0
}

const FUENTE_LABEL: Record<string, string> = {
  chat: 'Chat',
  carrito: 'Carrito',
  ambos: 'Chat + Carrito',
}

const FUENTE_STYLE: Record<string, { bg: string; color: string }> = {
  chat: { bg: '#e8f0eb', color: '#3d6b4f' },
  carrito: { bg: '#fef3e2', color: '#8b6914' },
  ambos: { bg: '#f5efe8', color: '#a34e3b' },
}

const DIAS_OPTIONS = [3, 7, 14, 30]

export default function DashboardPage() {
  const [data, setData] = useState<Metricas | null>(null)
  const [conversiones, setConversiones] = useState<Conversion[]>([])
  const [dias, setDias] = useState(7)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  const load = async () => {
    setLoading(true)
    setError('')
    try {
      const [metricas, conv] = await Promise.all([
        api.metricas(dias),
        api.conversiones(dias),
      ])
      setData(metricas)
      setConversiones(conv)
    } catch {
      setError('No se pudo conectar con el backend. Verifica que el servidor este corriendo.')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { load() }, [dias])

  return (
    <div>
      {/* Header */}
      <div className="flex items-end justify-between mb-10">
        <div>
          <motion.h1
            initial={{ opacity: 0, x: -10 }}
            animate={{ opacity: 1, x: 0 }}
            className="heading-display gradient-text"
            style={{ fontSize: '2.25rem' }}
          >
            Dashboard
          </motion.h1>
          <p className="text-sm mt-2" style={{ color: 'var(--color-text-muted)', letterSpacing: '0.02em' }}>
            Panel de control — Laura PRAIE
          </p>
        </div>
        <div className="flex items-center gap-3">
          <div className="flex gap-1 p-1 rounded-xl" style={{ background: 'var(--color-muted)', border: '1px solid var(--color-border)' }}>
            {DIAS_OPTIONS.map((d) => (
              <button
                key={d}
                onClick={() => setDias(d)}
                style={{
                  background: dias === d ? 'var(--color-card)' : 'transparent',
                  color: dias === d ? 'var(--color-primary)' : 'var(--color-text-muted)',
                  fontWeight: dias === d ? 600 : 400,
                  padding: '6px 14px',
                  borderRadius: 10,
                  fontSize: 13,
                  border: 'none',
                  cursor: 'pointer',
                  boxShadow: dias === d ? '0 1px 4px rgba(28,25,23,0.08)' : undefined,
                  transition: 'all 0.15s',
                }}
              >
                {d}d
              </button>
            ))}
          </div>
          <button
            onClick={load}
            disabled={loading}
            className="card"
            style={{
              padding: '8px 10px',
              cursor: 'pointer',
              color: 'var(--color-primary)',
            }}
          >
            <RefreshCw size={16} className={loading ? 'animate-spin' : ''} />
          </button>
        </div>
      </div>

      {error && (
        <div className="mb-6 p-4 rounded-xl" style={{ background: '#fef2f0', borderLeft: '3px solid var(--color-danger)', color: '#7c2d12', fontSize: 14 }}>
          {error}
        </div>
      )}

      {loading && !data ? (
        <div className="grid grid-cols-4 gap-5 mb-8">
          {[...Array(4)].map((_, i) => (
            <div key={i} className="h-32 rounded-2xl animate-pulse" style={{ background: 'var(--color-muted)' }} />
          ))}
        </div>
      ) : data ? (
        <>
          {/* Section label */}
          <p className="text-xs font-semibold mb-3" style={{ color: 'var(--color-text-muted)', letterSpacing: '0.1em', textTransform: 'uppercase' }}>
            Conversaciones
          </p>
          <div className="grid grid-cols-2 gap-4 mb-6 lg:grid-cols-4">
            <MetricCard label="Conversaciones" value={data.conversaciones} icon={MessageSquare} delay={0} />
            <MetricCard label="Clientas unicas" value={data.clientas} icon={Users} delay={0.05} />
            <MetricCard label="Mensajes totales" value={data.mensajes} icon={BarChart3} delay={0.1} />
            <MetricCard
              label="Respuestas a mejorar"
              value={`${data.tasa_problema}%`}
              icon={AlertTriangle}
              delay={0.15}
              color={data.tasa_problema > 20
                ? 'linear-gradient(135deg, #ef4444 0%, #b91c1c 100%)'
                : 'linear-gradient(135deg, #10b981 0%, #059669 100%)'}
            />
          </div>

          <p className="text-xs font-semibold mb-3" style={{ color: 'var(--color-text-muted)', letterSpacing: '0.1em', textTransform: 'uppercase' }}>
            Recuperacion de carritos
          </p>
          <div className="grid grid-cols-2 gap-4 mb-6 lg:grid-cols-4">
            <MetricCard
              label="Carritos contactados"
              value={data.carritos_enviados}
              icon={ShoppingCart}
              delay={0.2}
              color="linear-gradient(135deg, #f59e0b 0%, #d97706 100%)"
            />
            <MetricCard
              label="Carritos recuperados"
              value={data.carritos_recuperados}
              icon={TrendingUp}
              delay={0.25}
              color={data.carritos_recuperados > 0
                ? 'linear-gradient(135deg, #10b981 0%, #059669 100%)'
                : 'linear-gradient(135deg, #6b7280 0%, #4b5563 100%)'}
            />
            <MetricCard
              label="Tasa de recuperacion"
              value={`${data.tasa_recuperacion}%`}
              icon={BarChart3}
              delay={0.3}
              color={data.tasa_recuperacion > 30
                ? 'linear-gradient(135deg, #10b981 0%, #059669 100%)'
                : data.tasa_recuperacion > 0
                ? 'linear-gradient(135deg, #f59e0b 0%, #d97706 100%)'
                : 'linear-gradient(135deg, #6b7280 0%, #4b5563 100%)'}
            />
            <MetricCard
              label="Valor recuperado"
              value={data.valor_recuperado > 0 ? `$${data.valor_recuperado.toLocaleString('es-CO')}` : '$0'}
              icon={DollarSign}
              delay={0.35}
              color="linear-gradient(135deg, #8b5cf6 0%, #6d28d9 100%)"
            />
          </div>

          <p className="text-xs font-semibold mb-3" style={{ color: 'var(--color-text-muted)', letterSpacing: '0.1em', textTransform: 'uppercase' }}>
            Ventas por chat
          </p>
          {(() => {
            const ventas = data.ventas_por_chat ?? 0
            const total = data.ventas_cerradas_total ?? 0
            const tasa = data.clientas > 0 ? Math.round(ventas / data.clientas * 100) : 0
            const valorTotal = conversiones
              .filter(c => c.fuente === 'chat' || c.fuente === 'ambos')
              .reduce((sum, c) => sum + parseCOP(c.order_total), 0)
            return (
              <div className="grid grid-cols-2 gap-4 mb-8 lg:grid-cols-4">
                <MetricCard
                  label="Ventas cerradas por chat"
                  value={ventas}
                  icon={Handshake}
                  delay={0.4}
                  color={ventas > 0
                    ? 'linear-gradient(135deg, #10b981 0%, #059669 100%)'
                    : 'linear-gradient(135deg, #6b7280 0%, #4b5563 100%)'}
                />
                <MetricCard
                  label="Tasa chat a venta"
                  value={`${tasa}%`}
                  icon={TrendingUp}
                  delay={0.45}
                  color={tasa > 10
                    ? 'linear-gradient(135deg, #10b981 0%, #059669 100%)'
                    : tasa > 0
                    ? 'linear-gradient(135deg, #f59e0b 0%, #d97706 100%)'
                    : 'linear-gradient(135deg, #6b7280 0%, #4b5563 100%)'}
                />
                <MetricCard
                  label="Total atribuidas a Laura"
                  value={total}
                  icon={BarChart3}
                  delay={0.5}
                  color="linear-gradient(135deg, #c2614b 0%, #d4a574 100%)"
                />
                <MetricCard
                  label="Valor generado por chat"
                  value={valorTotal > 0 ? `$${valorTotal.toLocaleString('es-CO')}` : '$0'}
                  icon={DollarSign}
                  delay={0.55}
                  color={valorTotal > 0
                    ? 'linear-gradient(135deg, #10b981 0%, #059669 100%)'
                    : 'linear-gradient(135deg, #6b7280 0%, #4b5563 100%)'}
                />
              </div>
            )
          })()}

          {/* Conversions table */}
          {conversiones.length > 0 && (
            <motion.div
              initial={{ opacity: 0, y: 16 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.5, ease: [0.25, 0.46, 0.45, 0.94] }}
              className="card p-6 mb-6"
            >
              <h2 className="heading-display text-lg mb-5" style={{ color: 'var(--color-text)' }}>
                Ventas cerradas gracias a Laura
              </h2>
              <div className="overflow-x-auto">
                <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 13 }}>
                  <thead>
                    <tr style={{ borderBottom: '2px solid var(--color-border)' }}>
                      {['Telefono', 'Productos', 'Total', 'Origen', 'Dias desde chat', 'Fecha'].map(h => (
                        <th key={h} style={{
                          textAlign: 'left', padding: '10px 12px',
                          color: 'var(--color-text-muted)', fontWeight: 600,
                          fontSize: 11, letterSpacing: '0.06em', textTransform: 'uppercase',
                        }}>{h}</th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {conversiones.slice(0, 10).map((c) => {
                      const fuente = FUENTE_STYLE[c.fuente] || FUENTE_STYLE.chat
                      return (
                        <tr key={c.id} style={{ borderBottom: '1px solid var(--color-border)' }}>
                          <td style={{ padding: '12px', color: 'var(--color-text)', fontWeight: 500, fontVariantNumeric: 'tabular-nums' }}>
                            {c.telefono.slice(0, 5)}...{c.telefono.slice(-4)}
                          </td>
                          <td style={{ padding: '12px', color: 'var(--color-text-muted)', maxWidth: 200, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                            {c.productos || '\u2014'}
                          </td>
                          <td style={{ padding: '12px', fontWeight: 600, color: '#3d6b4f' }}>
                            {c.order_total || '\u2014'}
                          </td>
                          <td style={{ padding: '12px' }}>
                            <span style={{
                              padding: '4px 12px', borderRadius: 20, fontSize: 11, fontWeight: 600,
                              background: fuente.bg, color: fuente.color,
                            }}>
                              {FUENTE_LABEL[c.fuente] ?? c.fuente}
                            </span>
                          </td>
                          <td style={{ padding: '12px', color: 'var(--color-text-muted)', textAlign: 'center' }}>
                            {c.dias_desde_chat === 0 ? 'mismo dia' : `${c.dias_desde_chat}d`}
                          </td>
                          <td style={{ padding: '12px', color: 'var(--color-text-muted)' }}>
                            {formatDate(c.timestamp)}
                          </td>
                        </tr>
                      )
                    })}
                  </tbody>
                </table>
              </div>
            </motion.div>
          )}

          {/* Chart */}
          <motion.div
            initial={{ opacity: 0, y: 16 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.3, ease: [0.25, 0.46, 0.45, 0.94] }}
            className="card p-6 mb-6"
          >
            <h2 className="heading-display text-lg mb-5" style={{ color: 'var(--color-text)' }}>
              Mensajes por dia
            </h2>
            {data.mensajes_por_dia.length > 0 ? (
              <ResponsiveContainer width="100%" height={220}>
                <LineChart data={data.mensajes_por_dia}>
                  <CartesianGrid strokeDasharray="3 3" stroke="var(--color-border)" />
                  <XAxis dataKey="fecha" tick={{ fontSize: 11, fill: '#a8a29e' }} />
                  <YAxis tick={{ fontSize: 11, fill: '#a8a29e' }} />
                  <Tooltip
                    contentStyle={{
                      borderRadius: 14, border: '1px solid var(--color-border)',
                      boxShadow: '0 8px 24px rgba(28,25,23,0.08)',
                      background: 'var(--color-card)',
                    }}
                  />
                  <Line
                    type="monotone"
                    dataKey="mensajes"
                    stroke="url(#warm-gradient)"
                    strokeWidth={2.5}
                    dot={{ fill: '#c2614b', r: 3.5, strokeWidth: 0 }}
                    activeDot={{ r: 5, fill: '#c2614b' }}
                  />
                  <defs>
                    <linearGradient id="warm-gradient" x1="0" y1="0" x2="1" y2="0">
                      <stop offset="0%" stopColor="#c2614b" />
                      <stop offset="100%" stopColor="#d4a574" />
                    </linearGradient>
                  </defs>
                </LineChart>
              </ResponsiveContainer>
            ) : (
              <p style={{ color: 'var(--color-text-muted)', textAlign: 'center', padding: '2rem' }}>
                Sin datos en este periodo
              </p>
            )}
          </motion.div>

          {/* Alerts */}
          <motion.div
            initial={{ opacity: 0, y: 16 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.4, ease: [0.25, 0.46, 0.45, 0.94] }}
            className="card p-6"
          >
            <h2 className="heading-display text-lg mb-5" style={{ color: 'var(--color-text)' }}>
              Respuestas que necesitan revision
            </h2>
            {data.alertas.length === 0 ? (
              <div className="p-4 rounded-xl text-sm font-medium" style={{ background: '#e8f0eb', color: '#3d6b4f', borderLeft: '3px solid #5a8a6e' }}>
                No se detectaron respuestas problematicas en este periodo.
              </div>
            ) : (
              <div className="space-y-2.5">
                {data.alertas.map((a, i) => (
                  <div key={i} className="p-3.5 rounded-xl text-sm" style={{ background: '#fef3e2', borderLeft: '3px solid #c49230' }}>
                    <span className="font-semibold" style={{ color: '#8b6914' }}>{formatDate(a.timestamp)}</span>
                    <span style={{ color: '#78350f' }}> — {a.content}</span>
                  </div>
                ))}
              </div>
            )}
          </motion.div>
        </>
      ) : null}
    </div>
  )
}
