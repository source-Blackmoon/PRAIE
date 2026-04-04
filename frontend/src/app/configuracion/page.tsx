'use client'

import { useEffect, useState } from 'react'
import { motion } from 'framer-motion'
import { Settings, Webhook, RefreshCw, CheckCircle2, XCircle, Trash2, Link2 } from 'lucide-react'
import { api } from '@/lib/api'

interface Webhook {
  id: number
  topic: string
  address: string
}

export default function ConfiguracionPage() {
  const [shopifyStatus, setShopifyStatus] = useState<{ valid: boolean; shop?: string } | null>(null)
  const [webhooks, setWebhooks] = useState<Webhook[]>([])
  const [baseUrl, setBaseUrl] = useState('')
  const [loadingStatus, setLoadingStatus] = useState(true)
  const [syncing, setSyncing] = useState(false)
  const [registrando, setRegistrando] = useState(false)
  const [deletingId, setDeletingId] = useState<number | null>(null)
  const [syncResult, setSyncResult] = useState<string | null>(null)

  const loadStatus = async () => {
    setLoadingStatus(true)
    try {
      const [status, wh] = await Promise.all([api.shopifyStatus(), api.webhooks()])
      setShopifyStatus(status)
      setWebhooks(wh.webhooks)
    } catch { /* noop */ }
    finally { setLoadingStatus(false) }
  }

  useEffect(() => { loadStatus() }, [])

  const sync = async () => {
    setSyncing(true)
    setSyncResult(null)
    try {
      const r = await api.syncShopify()
      setSyncResult(`✅ Sincronizado: ${r.nuevos} carritos nuevos importados`)
    } catch {
      setSyncResult('❌ Error al sincronizar. Verifica las credenciales de Shopify.')
    } finally {
      setSyncing(false)
    }
  }

  const registrarWebhooks = async () => {
    if (!baseUrl) return
    setRegistrando(true)
    try {
      await api.registrarWebhooks(baseUrl)
      await loadStatus()
    } finally {
      setRegistrando(false)
    }
  }

  const eliminarWebhook = async (id: number) => {
    setDeletingId(id)
    try {
      await api.eliminarWebhook(id)
      setWebhooks((prev) => prev.filter((w) => w.id !== id))
    } finally {
      setDeletingId(null)
    }
  }

  return (
    <div>
      <div className="mb-8">
        <h1 className="text-3xl font-black gradient-text">Configuración</h1>
        <p className="text-sm mt-1" style={{ color: 'var(--color-text-muted)' }}>
          Integraciones y configuración del agente
        </p>
      </div>

      <div className="grid grid-cols-2 gap-6">
        {/* Shopify status */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          className="rounded-2xl p-6"
          style={{ background: 'white', boxShadow: '0 2px 12px rgba(118,75,162,0.08)' }}
        >
          <div className="flex items-center gap-2 mb-5">
            <Settings size={18} style={{ color: 'var(--color-primary)' }} />
            <h2 className="font-bold" style={{ color: 'var(--color-text)' }}>Estado de Shopify</h2>
          </div>

          {loadingStatus ? (
            <div className="text-sm" style={{ color: 'var(--color-text-muted)' }}>Verificando...</div>
          ) : shopifyStatus ? (
            <div className="mb-5">
              <div className="flex items-center gap-2 mb-3">
                {shopifyStatus.valid ? (
                  <><CheckCircle2 size={18} style={{ color: '#10b981' }} />
                  <p className="font-semibold text-sm" style={{ color: '#065f46' }}>Conectado</p></>
                ) : (
                  <><XCircle size={18} style={{ color: '#ef4444' }} />
                  <p className="font-semibold text-sm" style={{ color: '#7f1d1d' }}>Sin conectar</p></>
                )}
              </div>
              {shopifyStatus.shop && (
                <p className="text-sm" style={{ color: 'var(--color-text-muted)' }}>
                  Tienda: <strong>{shopifyStatus.shop}</strong>
                </p>
              )}
            </div>
          ) : null}

          <button
            onClick={sync}
            disabled={syncing}
            className="w-full flex items-center justify-center gap-2 py-2.5 rounded-xl text-sm font-semibold gradient-bg text-white"
            style={{ border: 'none', cursor: syncing ? 'default' : 'pointer', opacity: syncing ? 0.7 : 1 }}
          >
            <RefreshCw size={14} className={syncing ? 'animate-spin' : ''} />
            {syncing ? 'Sincronizando...' : 'Sincronizar carritos ahora'}
          </button>

          {syncResult && (
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              className="mt-3 p-3 rounded-xl text-sm"
              style={{
                background: syncResult.startsWith('✅') ? '#d1fae5' : '#fee2e2',
                color: syncResult.startsWith('✅') ? '#065f46' : '#7f1d1d',
              }}
            >
              {syncResult}
            </motion.div>
          )}
        </motion.div>

        {/* Webhooks */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.1 }}
          className="rounded-2xl p-6"
          style={{ background: 'white', boxShadow: '0 2px 12px rgba(118,75,162,0.08)' }}
        >
          <div className="flex items-center gap-2 mb-5">
            <Webhook size={18} style={{ color: 'var(--color-primary)' }} />
            <h2 className="font-bold" style={{ color: 'var(--color-text)' }}>Webhooks de Shopify</h2>
          </div>

          <div className="mb-4">
            <label className="block text-xs font-semibold mb-1.5" style={{ color: 'var(--color-text-muted)', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
              URL base del servidor
            </label>
            <div className="flex gap-2">
              <input
                value={baseUrl}
                onChange={(e) => setBaseUrl(e.target.value)}
                placeholder="https://mi-agente.railway.app"
                style={{
                  flex: 1,
                  padding: '9px 12px',
                  borderRadius: 10,
                  border: '1.5px solid var(--color-border)',
                  fontSize: 13,
                  outline: 'none',
                }}
              />
              <button
                onClick={registrarWebhooks}
                disabled={!baseUrl || registrando}
                className="flex items-center gap-1.5 px-3 py-2 rounded-xl text-sm font-semibold text-white gradient-bg"
                style={{ border: 'none', cursor: baseUrl ? 'pointer' : 'default', opacity: baseUrl ? 1 : 0.5, whiteSpace: 'nowrap' }}
              >
                <Link2 size={13} />
                {registrando ? 'Registrando...' : 'Registrar'}
              </button>
            </div>
          </div>

          <div className="space-y-2">
            {webhooks.length === 0 ? (
              <p className="text-sm" style={{ color: 'var(--color-text-muted)' }}>No hay webhooks registrados</p>
            ) : (
              webhooks.map((w) => (
                <div
                  key={w.id}
                  className="flex items-center justify-between p-3 rounded-xl"
                  style={{ background: 'var(--color-muted)' }}
                >
                  <div style={{ minWidth: 0 }}>
                    <p className="text-xs font-semibold" style={{ color: 'var(--color-primary)' }}>{w.topic}</p>
                    <p className="text-xs mt-0.5 truncate" style={{ color: 'var(--color-text-muted)' }}>{w.address}</p>
                  </div>
                  <button
                    onClick={() => eliminarWebhook(w.id)}
                    disabled={deletingId === w.id}
                    style={{ background: 'none', border: 'none', cursor: 'pointer', color: '#ef4444', opacity: deletingId === w.id ? 0.5 : 1, padding: '4px', borderRadius: 6 }}
                  >
                    <Trash2 size={14} />
                  </button>
                </div>
              ))
            )}
          </div>
        </motion.div>

        {/* Agent info */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.2 }}
          className="col-span-2 rounded-2xl p-6"
          style={{ background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)', color: 'white' }}
        >
          <div className="flex items-center gap-4">
            <div className="w-14 h-14 rounded-2xl bg-white/20 flex items-center justify-center text-2xl font-black">
              L
            </div>
            <div>
              <p className="text-2xl font-black">Laura — Agente PRAIE</p>
              <p className="text-white/70 text-sm mt-0.5">
                Agente de WhatsApp con IA · Atención al cliente de vestidos de baño
              </p>
            </div>
            <div className="ml-auto flex items-center gap-2">
              <div className="w-2.5 h-2.5 rounded-full bg-green-400 animate-pulse" />
              <p className="text-sm font-semibold">Activo</p>
            </div>
          </div>
          <div className="grid grid-cols-3 gap-4 mt-6">
            {[
              { label: 'Proveedor WhatsApp', value: 'Whapi.cloud' },
              { label: 'Modelo IA', value: 'claude-sonnet-4-6' },
              { label: 'Plataforma', value: 'FastAPI + Railway' },
            ].map(({ label, value }) => (
              <div key={label} className="p-3 rounded-xl" style={{ background: 'rgba(255,255,255,0.15)' }}>
                <p className="text-xs text-white/60">{label}</p>
                <p className="text-sm font-bold mt-0.5">{value}</p>
              </div>
            ))}
          </div>
        </motion.div>
      </div>
    </div>
  )
}
