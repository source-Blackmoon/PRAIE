'use client'

import { useState } from 'react'
import { motion } from 'framer-motion'
import { Sparkles, Play, DollarSign, FileText } from 'lucide-react'

export default function AnalisisPage() {
  const [dias, setDias] = useState(7)
  const [aplicar, setAplicar] = useState(true)
  const [running, setRunning] = useState(false)
  const [result, setResult] = useState<{ ok: boolean; msg: string } | null>(null)

  const ejecutar = async () => {
    setRunning(true)
    setResult(null)
    try {
      const BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'
      const res = await fetch(`${BASE}/api/analisis`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ dias, aplicar }),
      })
      if (res.ok) {
        setResult({ ok: true, msg: aplicar ? 'Análisis completado. Knowledge base actualizado. Reinicia el servidor para aplicar los cambios.' : 'Análisis completado.' })
      } else {
        setResult({ ok: false, msg: 'Error al ejecutar el análisis. Verifica los logs del servidor.' })
      }
    } catch {
      setResult({ ok: false, msg: 'No se pudo conectar con el servidor.' })
    } finally {
      setRunning(false)
    }
  }

  return (
    <div>
      <div className="mb-8">
        <h1 className="text-3xl font-black gradient-text">Análisis con IA</h1>
        <p className="text-sm mt-1" style={{ color: 'var(--color-text-muted)' }}>
          Claude analiza las conversaciones reales y sugiere mejoras concretas
        </p>
      </div>

      <div className="grid grid-cols-2 gap-6">
        {/* Config card */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          className="rounded-2xl p-6"
          style={{ background: 'white', boxShadow: '0 2px 12px rgba(118,75,162,0.08)' }}
        >
          <h2 className="font-bold text-base mb-6" style={{ color: 'var(--color-text)' }}>
            Configurar análisis
          </h2>

          <div className="mb-5">
            <label className="block text-sm font-semibold mb-2" style={{ color: 'var(--color-text)' }}>
              Período a analizar
            </label>
            <div className="flex gap-2">
              {[3, 7, 14, 30].map((d) => (
                <button
                  key={d}
                  onClick={() => setDias(d)}
                  style={{
                    flex: 1,
                    padding: '10px 0',
                    borderRadius: 10,
                    border: dias === d ? '2px solid var(--color-primary)' : '2px solid var(--color-border)',
                    background: dias === d ? 'var(--color-muted)' : 'white',
                    color: dias === d ? 'var(--color-primary)' : 'var(--color-text-muted)',
                    fontWeight: dias === d ? 700 : 400,
                    fontSize: 14,
                    cursor: 'pointer',
                    transition: 'all 0.15s',
                  }}
                >
                  {d} días
                </button>
              ))}
            </div>
          </div>

          <div className="mb-6">
            <label className="flex items-center gap-3 cursor-pointer">
              <div
                onClick={() => setAplicar(!aplicar)}
                style={{
                  width: 44,
                  height: 24,
                  borderRadius: 12,
                  background: aplicar ? 'var(--color-primary)' : '#d1d5db',
                  position: 'relative',
                  cursor: 'pointer',
                  transition: 'background 0.2s',
                }}
              >
                <div
                  style={{
                    position: 'absolute',
                    top: 2,
                    left: aplicar ? 22 : 2,
                    width: 20,
                    height: 20,
                    borderRadius: '50%',
                    background: 'white',
                    boxShadow: '0 1px 4px rgba(0,0,0,0.2)',
                    transition: 'left 0.2s',
                  }}
                />
              </div>
              <div>
                <p className="text-sm font-semibold" style={{ color: 'var(--color-text)' }}>
                  Aplicar mejoras automáticamente
                </p>
                <p className="text-xs" style={{ color: 'var(--color-text-muted)' }}>
                  Actualiza el knowledge base con las sugerencias
                </p>
              </div>
            </label>
          </div>

          <button
            onClick={ejecutar}
            disabled={running}
            className="w-full flex items-center justify-center gap-2 py-3 rounded-xl text-white font-semibold gradient-bg"
            style={{ border: 'none', cursor: running ? 'default' : 'pointer', opacity: running ? 0.7 : 1, fontSize: 15 }}
          >
            {running ? (
              <>
                <div className="w-4 h-4 rounded-full border-2 border-white/40 border-t-white animate-spin" />
                Claude está analizando...
              </>
            ) : (
              <>
                <Play size={16} /> Ejecutar análisis ahora
              </>
            )}
          </button>

          {result && (
            <motion.div
              initial={{ opacity: 0, y: 8 }}
              animate={{ opacity: 1, y: 0 }}
              className="mt-4 p-3 rounded-xl text-sm font-medium"
              style={{
                background: result.ok ? '#d1fae5' : '#fee2e2',
                color: result.ok ? '#065f46' : '#7f1d1d',
                borderLeft: `4px solid ${result.ok ? '#10b981' : '#ef4444'}`,
              }}
            >
              {result.ok ? '✅ ' : '❌ '}{result.msg}
            </motion.div>
          )}
        </motion.div>

        {/* Info card */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.1 }}
          className="space-y-4"
        >
          <div
            className="rounded-2xl p-6"
            style={{ background: 'white', boxShadow: '0 2px 12px rgba(118,75,162,0.08)' }}
          >
            <div className="flex items-center gap-3 mb-4">
              <div className="p-2.5 rounded-xl gradient-bg">
                <DollarSign size={18} className="text-white" />
              </div>
              <div>
                <p className="font-bold" style={{ color: 'var(--color-text)' }}>Costo estimado</p>
                <p className="text-xl font-black gradient-text">~$0.05 USD</p>
              </div>
            </div>
            <p className="text-xs" style={{ color: 'var(--color-text-muted)' }}>
              El análisis usa Claude API para revisar las conversaciones y generar sugerencias de mejora para Laura.
            </p>
          </div>

          <div
            className="rounded-2xl p-6"
            style={{ background: 'white', boxShadow: '0 2px 12px rgba(118,75,162,0.08)' }}
          >
            <div className="flex items-center gap-2 mb-3">
              <Sparkles size={16} style={{ color: 'var(--color-primary)' }} />
              <p className="font-bold text-sm" style={{ color: 'var(--color-text)' }}>¿Qué analiza?</p>
            </div>
            <ul className="space-y-2 text-sm" style={{ color: 'var(--color-text-muted)' }}>
              {[
                'Preguntas que Laura no supo responder bien',
                'Patrones de conversaciones exitosas',
                'Oportunidades de mejora en el knowledge base',
                'Sugerencias de respuestas más naturales',
              ].map((item, i) => (
                <li key={i} className="flex items-start gap-2">
                  <span style={{ color: 'var(--color-primary)', marginTop: 1 }}>•</span>
                  {item}
                </li>
              ))}
            </ul>
          </div>

          <div
            className="rounded-2xl p-5"
            style={{ background: 'var(--color-muted)', border: '1.5px dashed var(--color-border)' }}
          >
            <div className="flex items-center gap-2 mb-2">
              <FileText size={15} style={{ color: 'var(--color-primary)' }} />
              <p className="text-sm font-semibold" style={{ color: 'var(--color-text)' }}>Reportes</p>
            </div>
            <p className="text-xs" style={{ color: 'var(--color-text-muted)' }}>
              Los reportes se guardan en <code style={{ background: 'white', padding: '1px 5px', borderRadius: 4 }}>tools/reportes/</code> en el servidor. Puedes consultarlos directamente en esa carpeta.
            </p>
          </div>
        </motion.div>
      </div>
    </div>
  )
}
