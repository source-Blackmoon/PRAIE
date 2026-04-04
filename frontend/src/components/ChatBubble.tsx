import type { Mensaje } from '@/types'
import { formatDate } from '@/lib/utils'

const SEÑALES = ['no tengo esa información', 'déjame consultarlo', 'no entendí', 'no sé', 'disculpa']

export function ChatBubble({ mensaje }: { mensaje: Mensaje }) {
  const isUser = mensaje.role === 'user'
  const hasIssue = !isUser && SEÑALES.some((s) => mensaje.content.toLowerCase().includes(s))

  return (
    <div className={`flex ${isUser ? 'justify-end' : 'justify-start'} mb-3`}>
      <div
        style={{
          maxWidth: '75%',
          background: isUser
            ? 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)'
            : hasIssue
            ? '#fff8e1'
            : '#f3f0ff',
          color: isUser ? 'white' : '#1a1a2e',
          padding: '10px 14px',
          borderRadius: isUser ? '16px 16px 4px 16px' : '16px 16px 16px 4px',
          borderLeft: hasIssue ? '3px solid #f59e0b' : undefined,
          fontSize: 14,
          lineHeight: '1.5',
          boxShadow: '0 1px 4px rgba(0,0,0,0.08)',
        }}
      >
        <p>{mensaje.content}</p>
        <p
          style={{
            fontSize: 11,
            opacity: 0.65,
            marginTop: 4,
            textAlign: 'right',
          }}
        >
          {formatDate(mensaje.timestamp)} · {isUser ? 'Clienta' : `Laura ${hasIssue ? '⚠️' : '✅'}`}
        </p>
      </div>
    </div>
  )
}
