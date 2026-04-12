import type { Carrito, Conversion, ConversacionResumen, KnowledgeFile, Mensaje, Metricas } from '@/types'

const BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

async function req<T>(path: string, opts?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    ...opts,
    headers: { 'Content-Type': 'application/json', ...opts?.headers },
  })
  if (!res.ok) throw new Error(`HTTP ${res.status}: ${await res.text()}`)
  return res.json() as Promise<T>
}

export const api = {
  // Dashboard
  metricas: (dias = 7) =>
    req<Metricas>(`/api/metricas?dias=${dias}`),

  // Carritos abandonados
  carritos: () =>
    req<Carrito[]>('/api/carritos'),
  enviarCarrito: (checkoutId: string) =>
    req<{ status: string }>(`/api/carritos/${checkoutId}/enviar`, { method: 'POST' }),

  // Conversiones (ventas cerradas por chat)
  conversiones: (dias = 30) =>
    req<Conversion[]>(`/api/conversiones?dias=${dias}`),

  // Conversaciones
  conversaciones: (dias = 7) =>
    req<ConversacionResumen[]>(`/api/conversaciones?dias=${dias}`),
  mensajesConversacion: (telefono: string) =>
    req<Mensaje[]>(`/api/conversaciones/${encodeURIComponent(telefono)}`),

  // Knowledge base
  knowledge: () =>
    req<KnowledgeFile[]>('/api/knowledge'),
  updateKnowledge: (filename: string, content: string) =>
    req<{ status: string }>(`/api/knowledge/${filename}`, {
      method: 'PUT',
      body: JSON.stringify({ content }),
    }),

  // Escalaciones
  escalaciones: (estado = 'pendiente') =>
    req<{ id: number; telefono: string; razon: string; resumen: string; estado: string; timestamp: string }[]>(
      `/api/escalaciones?estado=${estado}`
    ),
  resolverEscalacion: (id: number) =>
    req<{ status: string }>(`/api/escalaciones/${id}/resolver`, { method: 'PUT' }),

  // Shopify
  shopifyStatus: () =>
    req<{ valid: boolean; shop?: string }>('/api/shopify/status'),
  syncShopify: () =>
    req<{ status: string; nuevos: number }>('/api/shopify/sync', { method: 'POST' }),
  webhooks: () =>
    req<{ webhooks: { id: number; topic: string; address: string }[] }>('/api/shopify/webhooks'),
  registrarWebhooks: (baseUrl: string) =>
    req<{ status: string }>('/api/shopify/webhooks/registrar', {
      method: 'POST',
      body: JSON.stringify({ base_url: baseUrl }),
    }),
  eliminarWebhook: (id: number) =>
    req<{ status: string }>(`/api/shopify/webhooks/${id}`, { method: 'DELETE' }),
}
