'use client'

import { useState, useEffect } from 'react'
import { motion } from 'framer-motion'
import { Sparkles, Play, DollarSign, FileText, TrendingDown, FlaskConical, Pause, Plus } from 'lucide-react'

interface FunnelStep {
  paso: string
  eventos: number
  clientas_unicas: number
}

interface FunnelData {
  periodo: { inicio: string; fin: string }
  funnel: FunnelStep[]
  valor_total_compras: number
}

interface ABTest {
  id: number
  nombre: string
  variante_a: string
  variante_b: string
  activo: boolean
  fecha_inicio: string
  total_envios: number
  significancia: boolean
  variantes: {
    a: { envios: number; conversiones: number }
    b: { envios: number; conversiones: number }
  }
}

const STEP_LABELS: Record<string, string> = {
  mensaje_recibido: 'Mensajes recibidos',
  producto_consultado: 'Productos consultados',
  carrito_creado: 'Carritos creados',
  compra_realizada: 'Compras realizadas',
}

const STEP_COLORS = ['#c2614b', '#d4735e', '#d4a574', '#c49230']

function FunnelChart({ data }: { data: FunnelData }) {
  const maxEventos = Math.max(...data.funnel.map(s => s.eventos), 1)

  return (
    <div className="space-y-3">
      {data.funnel.map((step, i) => {
        const width = Math.max((step.eventos / maxEventos) * 100, 8)
        const prevEventos = i > 0 ? data.funnel[i - 1].eventos : null
        const dropoff = prevEventos && prevEventos > 0
          ? Math.round((1 - step.eventos / prevEventos) * 100)
          : null

        return (
          <div key={step.paso}>
            <div className="flex items-center justify-between mb-1">
              <span className="text-sm font-semibold" style={{ color: 'var(--color-text)' }}>
                {STEP_LABELS[step.paso] || step.paso}
              </span>
              <div className="flex items-center gap-3">
                <span className="text-sm font-bold" style={{ color: STEP_COLORS[i] || '#c2614b' }}>
                  {step.eventos}
                </span>
                <span className="text-xs" style={{ color: 'var(--color-text-muted)' }}>
                  ({step.clientas_unicas} clientas)
                </span>
                {dropoff !== null && dropoff > 0 && (
                  <span className="text-xs font-medium px-1.5 py-0.5 rounded"
                    style={{ background: '#fef2f0', color: '#a34e3b' }}>
                    -{dropoff}%
                  </span>
                )}
              </div>
            </div>
            <div className="h-8 rounded-lg overflow-hidden" style={{ background: 'var(--color-muted)' }}>
              <motion.div
                initial={{ width: 0 }}
                animate={{ width: `${width}%` }}
                transition={{ duration: 0.6, delay: i * 0.1 }}
                className="h-full rounded-lg"
                style={{ background: STEP_COLORS[i] || '#c2614b' }}
              />
            </div>
          </div>
        )
      })}

      {data.valor_total_compras > 0 && (
        <div className="mt-4 p-3 rounded-xl" style={{ background: '#e8f0eb' }}>
          <p className="text-sm font-bold" style={{ color: '#3d6b4f' }}>
            Valor total compras: ${data.valor_total_compras.toLocaleString('es-CO')} COP
          </p>
        </div>
      )}
    </div>
  )
}

export default function AnalisisPage() {
  const [dias, setDias] = useState(7)
  const [funnelData, setFunnelData] = useState<FunnelData | null>(null)
  const [funnelLoading, setFunnelLoading] = useState(true)
  const [aplicar, setAplicar] = useState(true)
  const [running, setRunning] = useState(false)
  const [result, setResult] = useState<{ ok: boolean; msg: string } | null>(null)
  const [abTests, setAbTests] = useState<ABTest[]>([])
  const [abLoading, setAbLoading] = useState(true)
  const [showAbForm, setShowAbForm] = useState(false)
  const [abForm, setAbForm] = useState({ nombre: '', variante_a: '', variante_b: '' })

  useEffect(() => {
    const fetchFunnel = async () => {
      setFunnelLoading(true)
      try {
        const BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'
        const apiKey = process.env.NEXT_PUBLIC_API_KEY || ''
        const res = await fetch(`${BASE}/api/funnel?dias=${dias}`, {
          headers: apiKey ? { 'x-api-key': apiKey } : {},
        })
        if (res.ok) {
          setFunnelData(await res.json())
        }
      } catch {
        // silently fail, funnel section just won't show
      } finally {
        setFunnelLoading(false)
      }
    }
    fetchFunnel()
  }, [dias])

  const fetchAbTests = async () => {
    setAbLoading(true)
    try {
      const BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'
      const apiKey = process.env.NEXT_PUBLIC_API_KEY || ''
      const res = await fetch(`${BASE}/api/ab-tests`, {
        headers: apiKey ? { 'x-api-key': apiKey } : {},
      })
      if (res.ok) setAbTests(await res.json())
    } catch { /* silently fail */ } finally { setAbLoading(false) }
  }

  useEffect(() => { fetchAbTests() }, [])

  const crearAbTest = async () => {
    if (!abForm.nombre || !abForm.variante_a || !abForm.variante_b) return
    try {
      const BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'
      const apiKey = process.env.NEXT_PUBLIC_API_KEY || ''
      await fetch(`${BASE}/api/ab-tests`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', ...(apiKey ? { 'x-api-key': apiKey } : {}) },
        body: JSON.stringify(abForm),
      })
      setShowAbForm(false)
      setAbForm({ nombre: '', variante_a: '', variante_b: '' })
      fetchAbTests()
    } catch { /* silently fail */ }
  }

  const pausarAbTest = async (id: number) => {
    try {
      const BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'
      const apiKey = process.env.NEXT_PUBLIC_API_KEY || ''
      await fetch(`${BASE}/api/ab-tests/${id}/pausar`, {
        method: 'PUT',
        headers: apiKey ? { 'x-api-key': apiKey } : {},
      })
      fetchAbTests()
    } catch { /* silently fail */ }
  }

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
        <motion.h1
          initial={{ opacity: 0, x: -10 }}
          animate={{ opacity: 1, x: 0 }}
          className="heading-display gradient-text"
          style={{ fontSize: '2.25rem' }}
        >
          Analisis con IA
        </motion.h1>
        <p className="text-sm mt-2" style={{ color: 'var(--color-text-muted)' }}>
          Claude analiza las conversaciones reales y sugiere mejoras concretas
        </p>
      </div>

      {/* Funnel de Conversion */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        className="card p-6 mb-6"
      >
        <div className="flex items-center justify-between mb-6">
          <div className="flex items-center gap-3">
            <div className="p-2.5 rounded-xl gradient-bg">
              <TrendingDown size={18} className="text-white" />
            </div>
            <div>
              <h2 className="font-bold text-base" style={{ color: 'var(--color-text)' }}>
                Funnel de conversion
              </h2>
              <p className="text-xs" style={{ color: 'var(--color-text-muted)' }}>
                Ultimos {dias} dias
              </p>
            </div>
          </div>
        </div>

        {funnelLoading ? (
          <div className="flex items-center justify-center py-12">
            <div className="w-6 h-6 rounded-full border-2 animate-spin" style={{ borderColor: 'var(--color-muted)', borderTopColor: 'var(--color-primary)' }} />
          </div>
        ) : funnelData && funnelData.funnel.some(s => s.eventos > 0) ? (
          <FunnelChart data={funnelData} />
        ) : (
          <div className="text-center py-12">
            <p className="text-sm" style={{ color: 'var(--color-text-muted)' }}>
              Sin datos de funnel para este periodo. Los eventos se registran automaticamente cuando las clientas interactuan con Laura.
            </p>
          </div>
        )}
      </motion.div>

      <div className="grid grid-cols-2 gap-6">
        {/* Config card */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          className="card p-6"
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
                background: result.ok ? '#e8f0eb' : '#fef2f0',
                color: result.ok ? '#3d6b4f' : '#a34e3b',
                borderLeft: `4px solid ${result.ok ? '#5a8a6e' : '#c2614b'}`,
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
          <div className="card p-6">
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

          <div className="card p-6"
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

      {/* A/B Testing */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.2 }}
        className="card p-6 mt-6"
      >
        <div className="flex items-center justify-between mb-6">
          <div className="flex items-center gap-3">
            <div className="p-2.5 rounded-xl gradient-bg">
              <FlaskConical size={18} className="text-white" />
            </div>
            <div>
              <h2 className="font-bold text-base" style={{ color: 'var(--color-text)' }}>
                A/B Testing de carritos
              </h2>
              <p className="text-xs" style={{ color: 'var(--color-text-muted)' }}>
                Prueba diferentes mensajes de recuperacion para optimizar conversion
              </p>
            </div>
          </div>
          <button
            onClick={() => setShowAbForm(!showAbForm)}
            className="flex items-center gap-1.5 px-3 py-2 rounded-xl text-sm font-semibold gradient-bg text-white"
            style={{ border: 'none', cursor: 'pointer' }}
          >
            <Plus size={14} /> Nuevo test
          </button>
        </div>

        {showAbForm && (
          <motion.div
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: 'auto' }}
            className="mb-6 p-4 rounded-xl"
            style={{ background: 'var(--color-muted)', border: '1.5px solid var(--color-border)' }}
          >
            <div className="space-y-3">
              <div>
                <label className="block text-xs font-semibold mb-1" style={{ color: 'var(--color-text)' }}>
                  Nombre del test
                </label>
                <input
                  value={abForm.nombre}
                  onChange={(e) => setAbForm({ ...abForm, nombre: e.target.value })}
                  placeholder="ej: Tono casual vs urgente"
                  className="w-full px-3 py-2 rounded-lg text-sm"
                  style={{ border: '1.5px solid var(--color-border)', outline: 'none' }}
                />
              </div>
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-semibold mb-1" style={{ color: 'var(--color-text)' }}>
                    Variante A (template)
                  </label>
                  <textarea
                    value={abForm.variante_a}
                    onChange={(e) => setAbForm({ ...abForm, variante_a: e.target.value })}
                    placeholder="Usa {nombre}, {productos}, {total}, {total_str}, {url_carrito}"
                    rows={4}
                    className="w-full px-3 py-2 rounded-lg text-sm"
                    style={{ border: '1.5px solid var(--color-border)', outline: 'none', resize: 'vertical' }}
                  />
                </div>
                <div>
                  <label className="block text-xs font-semibold mb-1" style={{ color: 'var(--color-text)' }}>
                    Variante B (template)
                  </label>
                  <textarea
                    value={abForm.variante_b}
                    onChange={(e) => setAbForm({ ...abForm, variante_b: e.target.value })}
                    placeholder="Usa {nombre}, {productos}, {total}, {total_str}, {url_carrito}"
                    rows={4}
                    className="w-full px-3 py-2 rounded-lg text-sm"
                    style={{ border: '1.5px solid var(--color-border)', outline: 'none', resize: 'vertical' }}
                  />
                </div>
              </div>
              <div className="flex gap-2 justify-end">
                <button
                  onClick={() => setShowAbForm(false)}
                  className="px-4 py-2 rounded-lg text-sm"
                  style={{ border: '1.5px solid var(--color-border)', background: 'white', cursor: 'pointer' }}
                >
                  Cancelar
                </button>
                <button
                  onClick={crearAbTest}
                  className="px-4 py-2 rounded-lg text-sm font-semibold gradient-bg text-white"
                  style={{ border: 'none', cursor: 'pointer' }}
                >
                  Crear test
                </button>
              </div>
            </div>
          </motion.div>
        )}

        {abLoading ? (
          <div className="flex items-center justify-center py-8">
            <div className="w-6 h-6 rounded-full border-2 animate-spin" style={{ borderColor: 'var(--color-muted)', borderTopColor: 'var(--color-primary)' }} />
          </div>
        ) : abTests.length === 0 ? (
          <div className="text-center py-8">
            <p className="text-sm" style={{ color: 'var(--color-text-muted)' }}>
              No hay tests A/B creados. Crea uno para probar diferentes mensajes de carrito abandonado.
            </p>
          </div>
        ) : (
          <div className="space-y-4">
            {abTests.map((test) => {
              const rateA = test.variantes.a.envios > 0
                ? Math.round((test.variantes.a.conversiones / test.variantes.a.envios) * 100)
                : 0
              const rateB = test.variantes.b.envios > 0
                ? Math.round((test.variantes.b.conversiones / test.variantes.b.envios) * 100)
                : 0
              return (
                <div
                  key={test.id}
                  className="p-4 rounded-xl"
                  style={{
                    background: 'var(--color-muted)',
                    borderLeft: test.activo ? '4px solid var(--color-primary)' : '4px solid var(--color-border)',
                  }}
                >
                  <div className="flex items-center justify-between mb-3">
                    <div className="flex items-center gap-2">
                      <span className="font-bold text-sm" style={{ color: 'var(--color-text)' }}>
                        {test.nombre}
                      </span>
                      <span
                        className="text-xs px-2 py-0.5 rounded-full font-medium"
                        style={{
                          background: test.activo ? '#e8f0eb' : '#f5efe8',
                          color: test.activo ? '#3d6b4f' : '#6b7280',
                        }}
                      >
                        {test.activo ? 'Activo' : 'Pausado'}
                      </span>
                      {!test.significancia && test.total_envios > 0 && (
                        <span className="text-xs px-2 py-0.5 rounded-full font-medium"
                          style={{ background: '#fef3c7', color: '#92400e' }}>
                          &lt;100 envios
                        </span>
                      )}
                    </div>
                    {test.activo && (
                      <button
                        onClick={() => pausarAbTest(test.id)}
                        className="flex items-center gap-1 px-3 py-1.5 rounded-lg text-xs font-medium"
                        style={{ background: '#fef2f0', color: '#a34e3b', border: 'none', cursor: 'pointer' }}
                      >
                        <Pause size={12} /> Pausar
                      </button>
                    )}
                  </div>

                  <div className="grid grid-cols-2 gap-4">
                    <div className="p-3 rounded-lg" style={{ background: 'var(--color-card)' }}>
                      <p className="text-xs font-semibold mb-1" style={{ color: '#c2614b' }}>Variante A</p>
                      <div className="flex items-baseline gap-2">
                        <span className="text-2xl font-black" style={{ color: 'var(--color-text)' }}>{rateA}%</span>
                        <span className="text-xs" style={{ color: 'var(--color-text-muted)' }}>
                          ({test.variantes.a.conversiones}/{test.variantes.a.envios})
                        </span>
                      </div>
                    </div>
                    <div className="p-3 rounded-lg" style={{ background: 'var(--color-card)' }}>
                      <p className="text-xs font-semibold mb-1" style={{ color: '#d4a574' }}>Variante B</p>
                      <div className="flex items-baseline gap-2">
                        <span className="text-2xl font-black" style={{ color: 'var(--color-text)' }}>{rateB}%</span>
                        <span className="text-xs" style={{ color: 'var(--color-text-muted)' }}>
                          ({test.variantes.b.conversiones}/{test.variantes.b.envios})
                        </span>
                      </div>
                    </div>
                  </div>
                </div>
              )
            })}
          </div>
        )}
      </motion.div>
    </div>
  )
}
