'use client'

import { useEffect, useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { MessageSquare, Search } from 'lucide-react'
import { api } from '@/lib/api'
import type { ConversacionResumen, Mensaje } from '@/types'
import { ChatBubble } from '@/components/ChatBubble'
import { formatDate, formatPhone } from '@/lib/utils'

export default function ConversacionesPage() {
  const [lista, setLista] = useState<ConversacionResumen[]>([])
  const [seleccionado, setSeleccionado] = useState<string | null>(null)
  const [mensajes, setMensajes] = useState<Mensaje[]>([])
  const [query, setQuery] = useState('')
  const [dias, setDias] = useState(7)
  const [loading, setLoading] = useState(true)
  const [loadingMsgs, setLoadingMsgs] = useState(false)

  useEffect(() => {
    setLoading(true)
    api.conversaciones(dias)
      .then(setLista)
      .finally(() => setLoading(false))
  }, [dias])

  const selectConversacion = async (telefono: string) => {
    setSeleccionado(telefono)
    setLoadingMsgs(true)
    try {
      setMensajes(await api.mensajesConversacion(telefono))
    } finally {
      setLoadingMsgs(false)
    }
  }

  const filtrada = lista.filter(
    (c) => c.telefono.includes(query) || c.preview.toLowerCase().includes(query.toLowerCase())
  )

  return (
    <div>
      <div className="mb-8">
        <h1 className="text-3xl font-black gradient-text">Conversaciones</h1>
        <p className="text-sm mt-1" style={{ color: 'var(--color-text-muted)' }}>
          Historial de chats de WhatsApp con las clientas
        </p>
      </div>

      <div className="flex gap-5" style={{ height: 'calc(100vh - 180px)' }}>
        {/* Lista */}
        <div
          className="rounded-2xl flex flex-col"
          style={{
            width: 320,
            flexShrink: 0,
            background: 'white',
            boxShadow: '0 2px 12px rgba(118,75,162,0.08)',
            overflow: 'hidden',
          }}
        >
          {/* Search + filter */}
          <div className="p-4 border-b" style={{ borderColor: 'var(--color-border)' }}>
            <div className="relative">
              <Search size={15} style={{ position: 'absolute', left: 12, top: '50%', transform: 'translateY(-50%)', color: 'var(--color-text-muted)' }} />
              <input
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                placeholder="Buscar conversación..."
                style={{
                  width: '100%',
                  paddingLeft: 34,
                  paddingRight: 12,
                  paddingTop: 8,
                  paddingBottom: 8,
                  borderRadius: 10,
                  border: '1.5px solid var(--color-border)',
                  fontSize: 13,
                  outline: 'none',
                }}
              />
            </div>
            <div className="flex gap-1 mt-3">
              {[3, 7, 14, 30].map((d) => (
                <button
                  key={d}
                  onClick={() => setDias(d)}
                  style={{
                    flex: 1,
                    padding: '5px 0',
                    borderRadius: 8,
                    fontSize: 12,
                    border: 'none',
                    cursor: 'pointer',
                    background: dias === d ? 'var(--color-primary)' : 'var(--color-muted)',
                    color: dias === d ? 'white' : 'var(--color-text-muted)',
                    fontWeight: dias === d ? 600 : 400,
                  }}
                >
                  {d}d
                </button>
              ))}
            </div>
          </div>

          {/* Conversation list */}
          <div style={{ flex: 1, overflowY: 'auto' }}>
            {loading ? (
              <div className="p-6 text-center text-sm" style={{ color: 'var(--color-text-muted)' }}>Cargando...</div>
            ) : filtrada.length === 0 ? (
              <div className="p-6 text-center">
                <MessageSquare size={32} style={{ color: '#d1c4e9', margin: '0 auto 8px' }} />
                <p className="text-sm" style={{ color: 'var(--color-text-muted)' }}>Sin conversaciones</p>
              </div>
            ) : (
              filtrada.map((c, i) => (
                <motion.button
                  key={c.telefono}
                  initial={{ opacity: 0, x: -10 }}
                  animate={{ opacity: 1, x: 0 }}
                  transition={{ delay: i * 0.03 }}
                  onClick={() => selectConversacion(c.telefono)}
                  style={{
                    width: '100%',
                    textAlign: 'left',
                    padding: '14px 16px',
                    background: seleccionado === c.telefono ? 'var(--color-muted)' : 'transparent',
                    borderBottom: '1px solid var(--color-border)',
                    cursor: 'pointer',
                    borderLeft: seleccionado === c.telefono ? '3px solid var(--color-primary)' : '3px solid transparent',
                    transition: 'all 0.15s',
                    border: 'none',
                    borderLeftWidth: 3,
                    borderLeftStyle: 'solid',
                    borderLeftColor: seleccionado === c.telefono ? 'var(--color-primary)' : 'transparent',
                    borderBottomWidth: 1,
                    borderBottomStyle: 'solid',
                    borderBottomColor: 'var(--color-border)',
                  }}
                >
                  <div className="flex items-start gap-3">
                    <div className="w-9 h-9 rounded-full gradient-bg flex items-center justify-center text-white text-xs font-bold flex-shrink-0">
                      {c.telefono.slice(-2)}
                    </div>
                    <div style={{ flex: 1, minWidth: 0 }}>
                      <div className="flex items-center justify-between">
                        <p className="text-sm font-semibold" style={{ color: 'var(--color-text)' }}>
                          {formatPhone(c.telefono)}
                        </p>
                        <p className="text-xs" style={{ color: 'var(--color-text-muted)' }}>
                          {formatDate(c.ultimo)}
                        </p>
                      </div>
                      <p className="text-xs mt-0.5" style={{ color: 'var(--color-text-muted)', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                        {c.preview}
                      </p>
                      <span className="inline-block mt-1 px-1.5 py-0.5 rounded text-xs" style={{ background: 'var(--color-muted)', color: 'var(--color-primary)', fontWeight: 600 }}>
                        {c.mensajes} msgs
                      </span>
                    </div>
                  </div>
                </motion.button>
              ))
            )}
          </div>
        </div>

        {/* Chat panel */}
        <div
          className="rounded-2xl flex flex-col flex-1"
          style={{ background: 'white', boxShadow: '0 2px 12px rgba(118,75,162,0.08)', overflow: 'hidden' }}
        >
          {!seleccionado ? (
            <div className="flex-1 flex flex-col items-center justify-center" style={{ color: 'var(--color-text-muted)' }}>
              <MessageSquare size={48} style={{ color: '#d1c4e9', marginBottom: 12 }} />
              <p className="font-semibold">Selecciona una conversación</p>
              <p className="text-sm mt-1">Elige un chat de la lista de la izquierda</p>
            </div>
          ) : (
            <>
              {/* Chat header */}
              <div className="px-6 py-4 border-b" style={{ borderColor: 'var(--color-border)' }}>
                <div className="flex items-center gap-3">
                  <div className="w-10 h-10 rounded-full gradient-bg flex items-center justify-center text-white font-bold">
                    {seleccionado.slice(-2)}
                  </div>
                  <div>
                    <p className="font-bold" style={{ color: 'var(--color-text)' }}>{seleccionado}</p>
                    <p className="text-xs" style={{ color: 'var(--color-text-muted)' }}>
                      {mensajes.length} mensajes
                    </p>
                  </div>
                </div>
              </div>

              {/* Messages */}
              <div style={{ flex: 1, overflowY: 'auto', padding: '20px' }}>
                {loadingMsgs ? (
                  <div className="text-center text-sm" style={{ color: 'var(--color-text-muted)', marginTop: 32 }}>Cargando mensajes...</div>
                ) : (
                  <AnimatePresence>
                    {mensajes.map((m, i) => (
                      <motion.div
                        key={m.id}
                        initial={{ opacity: 0, y: 10 }}
                        animate={{ opacity: 1, y: 0 }}
                        transition={{ delay: i * 0.02 }}
                      >
                        <ChatBubble mensaje={m} />
                      </motion.div>
                    ))}
                  </AnimatePresence>
                )}
              </div>
            </>
          )}
        </div>
      </div>
    </div>
  )
}
