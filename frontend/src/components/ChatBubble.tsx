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
            ? 'linear-gradient(145deg, #c2614b, #d4a574)'
            : hasIssue
            ? '#fef3e2'
            : 'var(--color-muted)',
          color: isUser ? '#faf6f1' : 'var(--color-text)',
          padding: '11px 15px',
          borderRadius: isUser ? '18px 18px 4px 18px' : '18px 18px 18px 4px',
          borderLeft: hasIssue ? '3px solid #c49230' : undefined,
          fontSize: 14,
          lineHeight: '1.55',
          boxShadow: isUser
            ? '0 2px 8px rgba(194, 97, 75, 0.2)'
            : '0 1px 3px rgba(28, 25, 23, 0.04)',
        }}
      >
        <p style={{ whiteSpace: 'pre-wrap' }}>{mensaje.content}</p>
        <p
          style={{
            fontSize: 10,
            opacity: 0.6,
            marginTop: 5,
            textAlign: 'right',
            letterSpacing: '0.02em',
          }}
        >
          {formatDate(mensaje.timestamp)} · {isUser ? 'Clienta' : `Laura ${hasIssue ? '!' : ''}`}
        </p>
      </div>
    </div>
  )
}
