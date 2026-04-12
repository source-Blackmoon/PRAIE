'use client'

import { useEffect, useState } from 'react'
import { motion } from 'framer-motion'
import { BookOpen, Save, RotateCcw, Plus } from 'lucide-react'
import { api } from '@/lib/api'
import type { KnowledgeFile } from '@/types'

export default function KnowledgePage() {
  const [files, setFiles] = useState<KnowledgeFile[]>([])
  const [selected, setSelected] = useState<string | null>(null)
  const [content, setContent] = useState('')
  const [original, setOriginal] = useState('')
  const [saving, setSaving] = useState(false)
  const [saved, setSaved] = useState(false)
  const [loading, setLoading] = useState(true)
  const [newQ, setNewQ] = useState('')
  const [newA, setNewA] = useState('')

  const load = async () => {
    setLoading(true)
    try {
      const data = await api.knowledge()
      setFiles(data)
      if (data.length > 0 && !selected) {
        const first = data[0]
        setSelected(first.name)
        setContent(first.content)
        setOriginal(first.content)
      }
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { load() }, [])

  const selectFile = (name: string) => {
    const f = files.find((f) => f.name === name)!
    setSelected(name)
    setContent(f.content)
    setOriginal(f.content)
    setSaved(false)
  }

  const save = async () => {
    if (!selected) return
    setSaving(true)
    try {
      await api.updateKnowledge(selected, content)
      setOriginal(content)
      setFiles((prev) => prev.map((f) => f.name === selected ? { ...f, content } : f))
      setSaved(true)
      setTimeout(() => setSaved(false), 3000)
    } finally {
      setSaving(false)
    }
  }

  const addEntry = () => {
    if (!newQ || !newA || selected !== 'preguntas_reales.txt') return
    const entry = `\n${newQ} → ${newA}`
    setContent((prev) => prev + entry)
    setNewQ('')
    setNewA('')
  }

  const isDirty = content !== original

  return (
    <div>
      <div className="mb-8">
        <motion.h1
          initial={{ opacity: 0, x: -10 }}
          animate={{ opacity: 1, x: 0 }}
          className="heading-display gradient-text"
          style={{ fontSize: '2.25rem' }}
        >
          Knowledge Base
        </motion.h1>
        <p className="text-sm mt-2" style={{ color: 'var(--color-text-muted)' }}>
          Edita lo que Laura sabe — los cambios aplican al reiniciar el servidor
        </p>
      </div>

      <div className="flex gap-5" style={{ height: 'calc(100vh - 180px)' }}>
        {/* File list */}
        <div
          className="card p-4"
          style={{ width: 220, flexShrink: 0 }}
        >
          <p className="text-xs font-semibold uppercase tracking-wider mb-3" style={{ color: 'var(--color-text-muted)', letterSpacing: '0.08em' }}>
            Archivos
          </p>
          {loading ? (
            <div className="flex items-center gap-2 py-4">
              <div className="w-4 h-4 rounded-full border-2 animate-spin" style={{ borderColor: 'var(--color-muted)', borderTopColor: 'var(--color-primary)' }} />
              <span className="text-sm" style={{ color: 'var(--color-text-muted)' }}>Cargando...</span>
            </div>
          ) : (
            <div className="space-y-1">
              {files.map((f) => (
                <button
                  key={f.name}
                  onClick={() => selectFile(f.name)}
                  style={{
                    width: '100%',
                    textAlign: 'left',
                    padding: '10px 12px',
                    borderRadius: 10,
                    fontSize: 13,
                    border: 'none',
                    cursor: 'pointer',
                    background: selected === f.name ? 'var(--color-muted)' : 'transparent',
                    borderLeft: selected === f.name ? '3px solid var(--color-primary)' : '3px solid transparent',
                    color: selected === f.name ? 'var(--color-primary)' : 'var(--color-text)',
                    fontWeight: selected === f.name ? 700 : 400,
                    transition: 'all 0.15s',
                  }}
                >
                  <BookOpen size={13} style={{ display: 'inline', marginRight: 8, opacity: 0.6 }} />
                  {f.name}
                  <br />
                  <span style={{ fontSize: 11, color: 'var(--color-text-muted)', fontWeight: 400 }}>
                    {(f.size / 1024).toFixed(1)} KB
                  </span>
                </button>
              ))}
            </div>
          )}
        </div>

        {/* Editor */}
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          className="card flex flex-col flex-1"
          style={{ overflow: 'hidden' }}
        >
          {/* Toolbar */}
          <div className="flex items-center justify-between px-6 py-4" style={{ borderBottom: '1px solid var(--color-border)' }}>
            <div>
              <p className="font-bold" style={{ color: 'var(--color-text)' }}>{selected || 'Selecciona un archivo'}</p>
              {isDirty && <p className="text-xs mt-0.5" style={{ color: '#c49230' }}>Cambios sin guardar</p>}
              {saved && <p className="text-xs mt-0.5" style={{ color: '#5a8a6e' }}>Guardado correctamente</p>}
            </div>
            <div className="flex gap-2">
              <button
                onClick={() => { setContent(original); setSaved(false) }}
                disabled={!isDirty}
                className="flex items-center gap-1.5 px-3 py-2 rounded-xl text-sm font-semibold"
                style={{
                  border: '1.5px solid var(--color-border)',
                  background: 'transparent',
                  color: isDirty ? 'var(--color-text-muted)' : 'var(--color-border)',
                  cursor: isDirty ? 'pointer' : 'default',
                }}
              >
                <RotateCcw size={13} /> Restaurar
              </button>
              <button
                onClick={save}
                disabled={!isDirty || saving}
                className="flex items-center gap-1.5 px-4 py-2 rounded-xl text-sm font-semibold text-white gradient-bg"
                style={{ border: 'none', cursor: isDirty ? 'pointer' : 'default', opacity: !isDirty || saving ? 0.5 : 1 }}
              >
                <Save size={13} /> {saving ? 'Guardando...' : 'Guardar'}
              </button>
            </div>
          </div>

          {/* Text area */}
          <textarea
            value={content}
            onChange={(e) => setContent(e.target.value)}
            style={{
              flex: 1,
              resize: 'none',
              border: 'none',
              outline: 'none',
              padding: '20px 24px',
              fontFamily: 'monospace',
              fontSize: 13,
              lineHeight: 1.7,
              color: 'var(--color-text)',
              background: 'transparent',
            }}
            placeholder="Selecciona un archivo para editar..."
          />

          {/* Quick add (only for preguntas_reales.txt) */}
          {selected === 'preguntas_reales.txt' && (
            <div className="px-6 py-4" style={{ borderTop: '1px solid var(--color-border)', background: 'var(--color-muted)' }}>
              <p className="text-xs font-semibold mb-3" style={{ color: 'var(--color-text-muted)', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
                Agregar pregunta rapida
              </p>
              <div className="flex gap-2">
                <input
                  value={newQ}
                  onChange={(e) => setNewQ(e.target.value)}
                  placeholder="Pregunta de clienta"
                  style={{ flex: 1, padding: '8px 12px', borderRadius: 10, border: '1.5px solid var(--color-border)', fontSize: 13, outline: 'none', background: 'var(--color-card)' }}
                />
                <input
                  value={newA}
                  onChange={(e) => setNewA(e.target.value)}
                  placeholder="Respuesta de Laura"
                  style={{ flex: 1, padding: '8px 12px', borderRadius: 10, border: '1.5px solid var(--color-border)', fontSize: 13, outline: 'none', background: 'var(--color-card)' }}
                />
                <button
                  onClick={addEntry}
                  disabled={!newQ || !newA}
                  className="flex items-center gap-1.5 px-3 py-2 rounded-xl text-sm font-semibold text-white gradient-bg"
                  style={{ border: 'none', cursor: newQ && newA ? 'pointer' : 'default', opacity: newQ && newA ? 1 : 0.5, whiteSpace: 'nowrap' }}
                >
                  <Plus size={14} /> Agregar
                </button>
              </div>
            </div>
          )}
        </motion.div>
      </div>
    </div>
  )
}
