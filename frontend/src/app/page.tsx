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
      setError('No se pudo conectar con el backend. Verifica que el servidor esté corriendo.')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { load() }, [dias])

  return (
    <div>
      {/* Header */}
      <div className="flex items-center justify-between mb-8">
        <div>
          <h1 className="text-3xl font-black gradient-text">Dashboard</h1>
          <p className="text-sm mt-1" style={{ color: 'var(--color-text-muted)' }}>
            Panel de control — Laura PRAIE
          </p>
        </div>
        <div className="flex items-center gap-3">
          <div className="flex gap-1 p-1 rounded-xl" style={{ background: 'var(--color-muted)' }}>
            {DIAS_OPTIONS.map((d) => (
              <button
                key={d}
                onClick={() => setDias(d)}
                style={{
                  background: dias === d ? 'white' : 'transparent',
                  color: dias === d ? 'var(--color-primary)' : 'var(--color-text-muted)',
                  fontWeight: dias === d ? 700 : 400,
                  padding: '6px 14px',
                  borderRadius: 10,
                  fontSize: 13,
                  border: 'none',
                  cursor: 'pointer',
                  boxShadow: dias === d ? '0 1px 4px rgba(0,0,0,0.1)' : undefined,
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
            style={{
              background: 'white',
              border: '1.5px solid var(--color-border)',
              borderRadius: 12,
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
        <div className="mb-6 p-4 rounded-xl" style={{ background: '#fff3f3', borderLeft: '4px solid #ef4444', color: '#7f1d1d', fontSize: 14 }}>
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
          {/* KPI Cards — Conversaciones */}
          <div className="grid grid-cols-2 gap-5 mb-5 lg:grid-cols-4">
            <MetricCard label="Conversaciones" value={data.conversaciones} icon={MessageSquare} delay={0} />
            <MetricCard label="Clientas únicas" value={data.clientas} icon={Users} delay={0.1} />
            <MetricCard label="Mensajes totales" value={data.mensajes} icon={BarChart3} delay={0.2} />
            <MetricCard
              label="Respuestas a mejorar"
              value={`${data.tasa_problema}%`}
              icon={AlertTriangle}
              delay={0.3}
              color={
                data.tasa_problema > 20
                  ? 'linear-gradient(135deg, #ef4444 0%, #b91c1c 100%)'
                  : 'linear-gradient(135deg, #10b981 0%, #059669 100%)'
              }
            />
          </div>

          {/* KPI Cards — Conversión de carritos */}
          <div className="grid grid-cols-2 gap-5 mb-8 lg:grid-cols-4">
            <MetricCard
              label="Carritos contactados"
              value={data.carritos_enviados}
              icon={ShoppingCart}
              delay={0.4}
              color="linear-gradient(135deg, #f59e0b 0%, #d97706 100%)"
            />
            <MetricCard
              label="Carritos recuperados"
              value={data.carritos_recuperados}
              icon={TrendingUp}
              delay={0.5}
              color={
                data.carritos_recuperados > 0
                  ? 'linear-gradient(135deg, #10b981 0%, #059669 100%)'
                  : 'linear-gradient(135deg, #6b7280 0%, #4b5563 100%)'
              }
            />
            <MetricCard
              label="Tasa de recuperación"
              value={`${data.tasa_recuperacion}%`}
              icon={BarChart3}
              delay={0.6}
              color={
                data.tasa_recuperacion > 30
                  ? 'linear-gradient(135deg, #10b981 0%, #059669 100%)'
                  : data.tasa_recuperacion > 0
                  ? 'linear-gradient(135deg, #f59e0b 0%, #d97706 100%)'
                  : 'linear-gradient(135deg, #6b7280 0%, #4b5563 100%)'
              }
            />
            <MetricCard
              label="Valor recuperado"
              value={data.valor_recuperado > 0 ? `$${data.valor_recuperado.toLocaleString('es-CO')}` : '$0'}
              icon={DollarSign}
              delay={0.7}
              color="linear-gradient(135deg, #8b5cf6 0%, #6d28d9 100%)"
            />
          </div>

          {/* KPI Cards — Ventas por chat */}
          {(() => {
            const ventas = data.ventas_por_chat ?? 0
            const total = data.ventas_cerradas_total ?? 0
            const tasa = data.clientas > 0 ? Math.round(ventas / data.clientas * 100) : 0
            const valorTotal = conversiones
              .filter(c => c.fuente === 'chat' || c.fuente === 'ambos')
              .reduce((sum, c) => sum + parseCOP(c.order_total), 0)
            return (
              <div className="grid grid-cols-2 gap-5 mb-5 lg:grid-cols-4">
                <MetricCard
                  label="Ventas cerradas por chat"
                  value={ventas}
                  icon={Handshake}
                  delay={0.8}
                  color={ventas > 0
                    ? 'linear-gradient(135deg, #10b981 0%, #059669 100%)'
                    : 'linear-gradient(135deg, #6b7280 0%, #4b5563 100%)'}
                />
                <MetricCard
                  label="Tasa chat → venta"
                  value={`${tasa}%`}
                  icon={TrendingUp}
                  delay={0.9}
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
                  delay={1.0}
                  color="linear-gradient(135deg, #764ba2 0%, #667eea 100%)"
                />
                <MetricCard
                  label="Valor generado por chat"
                  value={valorTotal > 0 ? `$${valorTotal.toLocaleString('es-CO')}` : '$0'}
                  icon={DollarSign}
                  delay={1.1}
                  color={valorTotal > 0
                    ? 'linear-gradient(135deg, #10b981 0%, #059669 100%)'
                    : 'linear-gradient(135deg, #6b7280 0%, #4b5563 100%)'}
                />
              </div>
            )
          })()}

          {/* Tabla de conversiones */}
          {conversiones.length > 0 && (
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.85 }}
              className="rounded-2xl p-6 mb-6"
              style={{ background: 'white', boxShadow: '0 2px 12px rgba(118,75,162,0.08)' }}
            >
              <h2 className="font-bold text-base mb-4" style={{ color: 'var(--color-text)' }}>
                Ventas cerradas gracias a Laura
              </h2>
              <div className="overflow-x-auto">
                <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 13 }}>
                  <thead>
                    <tr style={{ borderBottom: '2px solid var(--color-border)' }}>
                      {['Teléfono', 'Productos', 'Total', 'Origen', 'Días desde chat', 'Fecha'].map(h => (
                        <th key={h} style={{ textAlign: 'left', padding: '8px 12px', color: 'var(--color-text-muted)', fontWeight: 600 }}>{h}</th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {conversiones.slice(0, 10).map((c) => (
                      <tr key={c.id} style={{ borderBottom: '1px solid var(--color-border)' }}>
                        <td style={{ padding: '10px 12px', color: 'var(--color-text)', fontWeight: 500 }}>
                          {c.telefono.slice(0, 5)}···{c.telefono.slice(-4)}
                        </td>
                        <td style={{ padding: '10px 12px', color: 'var(--color-text-muted)', maxWidth: 200, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                          {c.productos || '—'}
                        </td>
                        <td style={{ padding: '10px 12px', fontWeight: 600, color: '#059669' }}>
                          {c.order_total || '—'}
                        </td>
                        <td style={{ padding: '10px 12px' }}>
                          <span style={{
                            padding: '3px 10px',
                            borderRadius: 20,
                            fontSize: 11,
                            fontWeight: 700,
                            background: c.fuente === 'ambos' ? '#ddd6fe' : c.fuente === 'chat' ? '#d1fae5' : '#fef3c7',
                            color: c.fuente === 'ambos' ? '#5b21b6' : c.fuente === 'chat' ? '#065f46' : '#92400e',
                          }}>
                            {FUENTE_LABEL[c.fuente] ?? c.fuente}
                          </span>
                        </td>
                        <td style={{ padding: '10px 12px', color: 'var(--color-text-muted)', textAlign: 'center' }}>
                          {c.dias_desde_chat === 0 ? 'mismo día' : `${c.dias_desde_chat}d`}
                        </td>
                        <td style={{ padding: '10px 12px', color: 'var(--color-text-muted)' }}>
                          {formatDate(c.timestamp)}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </motion.div>
          )}

          {/* Chart */}
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.4 }}
            className="rounded-2xl p-6 mb-6"
            style={{ background: 'white', boxShadow: '0 2px 12px rgba(118,75,162,0.08)' }}
          >
            <h2 className="font-bold text-base mb-5" style={{ color: 'var(--color-text)' }}>
              Mensajes por día
            </h2>
            {data.mensajes_por_dia.length > 0 ? (
              <ResponsiveContainer width="100%" height={220}>
                <LineChart data={data.mensajes_por_dia}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#f3f0ff" />
                  <XAxis dataKey="fecha" tick={{ fontSize: 12, fill: '#9ca3af' }} />
                  <YAxis tick={{ fontSize: 12, fill: '#9ca3af' }} />
                  <Tooltip
                    contentStyle={{ borderRadius: 12, border: 'none', boxShadow: '0 4px 20px rgba(0,0,0,0.12)' }}
                  />
                  <Line
                    type="monotone"
                    dataKey="mensajes"
                    stroke="url(#gradient)"
                    strokeWidth={3}
                    dot={{ fill: '#764ba2', r: 4 }}
                    activeDot={{ r: 6 }}
                  />
                  <defs>
                    <linearGradient id="gradient" x1="0" y1="0" x2="1" y2="0">
                      <stop offset="0%" stopColor="#667eea" />
                      <stop offset="100%" stopColor="#764ba2" />
                    </linearGradient>
                  </defs>
                </LineChart>
              </ResponsiveContainer>
            ) : (
              <p style={{ color: 'var(--color-text-muted)', textAlign: 'center', padding: '2rem' }}>
                Sin datos en este período
              </p>
            )}
          </motion.div>

          {/* Alertas */}
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.5 }}
            className="rounded-2xl p-6"
            style={{ background: 'white', boxShadow: '0 2px 12px rgba(118,75,162,0.08)' }}
          >
            <h2 className="font-bold text-base mb-4" style={{ color: 'var(--color-text)' }}>
              Respuestas que necesitan revisión
            </h2>
            {data.alertas.length === 0 ? (
              <div className="p-4 rounded-xl text-sm font-medium" style={{ background: '#d1fae5', color: '#065f46', borderLeft: '4px solid #10b981' }}>
                No se detectaron respuestas problemáticas en este período.
              </div>
            ) : (
              <div className="space-y-3">
                {data.alertas.map((a, i) => (
                  <div key={i} className="p-3 rounded-xl text-sm" style={{ background: '#fff8e1', borderLeft: '4px solid #f59e0b' }}>
                    <span className="font-semibold" style={{ color: '#92400e' }}>{formatDate(a.timestamp)}</span>
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
