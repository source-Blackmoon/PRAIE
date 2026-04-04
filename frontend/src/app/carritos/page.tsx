'use client'

import { useEffect, useState } from 'react'
import { motion } from 'framer-motion'
import { ShoppingCart, Send, RefreshCw, CheckCircle2, Clock, XCircle } from 'lucide-react'
import { api } from '@/lib/api'
import type { Carrito } from '@/types'
import { formatDate, formatPhone } from '@/lib/utils'

export default function CarritosPage() {
  const [carritos, setCarritos] = useState<Carrito[]>([])
  const [loading, setLoading] = useState(true)
  const [sending, setSending] = useState<string | null>(null)
  const [syncing, setSyncing] = useState(false)

  const load = async () => {
    setLoading(true)
    try { setCarritos(await api.carritos()) } catch { /* noop */ }
    finally { setLoading(false) }
  }

  const syncShopify = async () => {
    setSyncing(true)
    try {
      await api.syncShopify()
      await load()
    } catch { /* noop */ }
    finally { setSyncing(false) }
  }

  const enviar = async (checkoutId: string) => {
    setSending(checkoutId)
    try {
      await api.enviarCarrito(checkoutId)
      setCarritos((prev) =>
        prev.map((c) => c.checkout_id === checkoutId ? { ...c, mensaje_enviado: true } : c)
      )
    } catch { /* noop */ }
    finally { setSending(null) }
  }

  useEffect(() => { load() }, [])

  const pendientes = carritos.filter((c) => !c.mensaje_enviado && !c.completado)
  const enviados   = carritos.filter((c) => c.mensaje_enviado && !c.completado)
  const recuperados = carritos.filter((c) => c.completado)

  return (
    <div>
      <div className="flex items-center justify-between mb-8">
        <div>
          <h1 className="text-3xl font-black gradient-text">Carritos Abandonados</h1>
          <p className="text-sm mt-1" style={{ color: 'var(--color-text-muted)' }}>
            Recupera ventas con mensajes automáticos de Laura
          </p>
        </div>
        <div className="flex gap-3">
          <button
            onClick={syncShopify}
            disabled={syncing}
            className="flex items-center gap-2 px-4 py-2.5 rounded-xl text-sm font-semibold"
            style={{ background: 'white', border: '1.5px solid var(--color-border)', color: 'var(--color-primary)', cursor: 'pointer' }}
          >
            <RefreshCw size={15} className={syncing ? 'animate-spin' : ''} />
            Sincronizar Shopify
          </button>
        </div>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-3 gap-4 mb-8">
        {[
          { label: 'Pendientes', value: pendientes.length, color: '#f59e0b', icon: Clock },
          { label: 'Mensaje enviado', value: enviados.length, color: '#667eea', icon: Send },
          { label: 'Recuperados', value: recuperados.length, color: '#10b981', icon: CheckCircle2 },
        ].map(({ label, value, color, icon: Icon }, i) => (
          <motion.div
            key={label}
            initial={{ opacity: 0, y: 16 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: i * 0.1 }}
            className="rounded-2xl p-5"
            style={{ background: 'white', boxShadow: '0 2px 12px rgba(118,75,162,0.08)', borderTop: `3px solid ${color}` }}
          >
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm" style={{ color: 'var(--color-text-muted)' }}>{label}</p>
                <p className="text-4xl font-black mt-1" style={{ color }}>{value}</p>
              </div>
              <Icon size={28} style={{ color, opacity: 0.3 }} />
            </div>
          </motion.div>
        ))}
      </div>

      {/* Table */}
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ delay: 0.3 }}
        className="rounded-2xl overflow-hidden"
        style={{ background: 'white', boxShadow: '0 2px 12px rgba(118,75,162,0.08)' }}
      >
        {loading ? (
          <div className="p-12 text-center" style={{ color: 'var(--color-text-muted)' }}>Cargando...</div>
        ) : carritos.length === 0 ? (
          <div className="p-12 text-center">
            <ShoppingCart size={40} style={{ color: '#d1c4e9', margin: '0 auto 12px' }} />
            <p style={{ color: 'var(--color-text-muted)' }}>
              No hay carritos todavía. Sincroniza con Shopify para empezar.
            </p>
          </div>
        ) : (
          <table style={{ width: '100%', borderCollapse: 'collapse' }}>
            <thead>
              <tr style={{ background: 'var(--color-muted)' }}>
                {['Clienta', 'Productos', 'Total', 'Fecha', 'Estado', 'Acción'].map((h) => (
                  <th key={h} style={{ padding: '12px 16px', textAlign: 'left', fontSize: 12, fontWeight: 600, color: 'var(--color-text-muted)', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
                    {h}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {carritos.map((c, i) => (
                <motion.tr
                  key={c.id}
                  initial={{ opacity: 0, x: -10 }}
                  animate={{ opacity: 1, x: 0 }}
                  transition={{ delay: i * 0.04 }}
                  style={{ borderBottom: '1px solid var(--color-border)' }}
                >
                  <td style={{ padding: '14px 16px' }}>
                    <div>
                      <p className="font-semibold text-sm" style={{ color: 'var(--color-text)' }}>{c.nombre || 'Clienta'}</p>
                      <p className="text-xs mt-0.5" style={{ color: 'var(--color-text-muted)' }}>{formatPhone(c.telefono)}</p>
                    </div>
                  </td>
                  <td style={{ padding: '14px 16px', maxWidth: 200 }}>
                    <p className="text-sm" style={{ color: 'var(--color-text)', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                      {c.productos || '—'}
                    </p>
                  </td>
                  <td style={{ padding: '14px 16px' }}>
                    <p className="text-sm font-semibold" style={{ color: 'var(--color-primary)' }}>{c.total || '—'}</p>
                  </td>
                  <td style={{ padding: '14px 16px' }}>
                    <p className="text-sm" style={{ color: 'var(--color-text-muted)' }}>{formatDate(c.timestamp)}</p>
                  </td>
                  <td style={{ padding: '14px 16px' }}>
                    {c.completado ? (
                      <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-xs font-semibold" style={{ background: '#d1fae5', color: '#065f46' }}>
                        <CheckCircle2 size={11} /> Recuperado
                      </span>
                    ) : c.mensaje_enviado ? (
                      <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-xs font-semibold" style={{ background: '#ede9fe', color: '#5b21b6' }}>
                        <Send size={11} /> Enviado
                      </span>
                    ) : (
                      <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-xs font-semibold" style={{ background: '#fef3c7', color: '#92400e' }}>
                        <Clock size={11} /> Pendiente
                      </span>
                    )}
                  </td>
                  <td style={{ padding: '14px 16px' }}>
                    {!c.mensaje_enviado && !c.completado && (
                      <button
                        onClick={() => enviar(c.checkout_id)}
                        disabled={sending === c.checkout_id}
                        className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold gradient-bg text-white"
                        style={{ border: 'none', cursor: 'pointer', opacity: sending === c.checkout_id ? 0.6 : 1 }}
                      >
                        <Send size={12} />
                        {sending === c.checkout_id ? 'Enviando...' : 'Enviar'}
                      </button>
                    )}
                    {c.url_carrito && (
                      <a href={c.url_carrito} target="_blank" rel="noreferrer" className="text-xs ml-2" style={{ color: 'var(--color-primary)' }}>
                        Ver carrito
                      </a>
                    )}
                  </td>
                </motion.tr>
              ))}
            </tbody>
          </table>
        )}
      </motion.div>
    </div>
  )
}
