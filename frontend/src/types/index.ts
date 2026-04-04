export interface Metricas {
  conversaciones: number
  clientas: number
  mensajes: number
  tasa_problema: number
  mensajes_por_dia: { fecha: string; mensajes: number }[]
  alertas: { timestamp: string; content: string }[]
  carritos_enviados: number
  carritos_recuperados: number
  tasa_recuperacion: number
  valor_recuperado: number
  valor_pendiente: number
}

export interface Carrito {
  id: number
  checkout_id: string
  telefono: string
  nombre: string
  productos: string
  total: string
  url_carrito: string
  mensaje_enviado: boolean
  completado: boolean
  timestamp: string
}

export interface ConversacionResumen {
  telefono: string
  mensajes: number
  ultimo: string
  preview: string
}

export interface Mensaje {
  id: number
  role: 'user' | 'assistant'
  content: string
  timestamp: string
}

export interface KnowledgeFile {
  name: string
  path: string
  size: number
  content: string
}
