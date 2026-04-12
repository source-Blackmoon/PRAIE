'use client'

import Link from 'next/link'
import { usePathname } from 'next/navigation'
import { motion } from 'framer-motion'
import {
  LayoutDashboard,
  ShoppingCart,
  MessageSquare,
  BookOpen,
  Sparkles,
  Settings,
  AlertTriangle,
} from 'lucide-react'
import { cn } from '@/lib/utils'

const nav = [
  { href: '/',               icon: LayoutDashboard, label: 'Dashboard'       },
  { href: '/carritos',       icon: ShoppingCart,    label: 'Carritos'        },
  { href: '/conversaciones', icon: MessageSquare,   label: 'Conversaciones'  },
  { href: '/knowledge',      icon: BookOpen,        label: 'Knowledge Base'  },
  { href: '/escalaciones',   icon: AlertTriangle,   label: 'Escalaciones'    },
  { href: '/analisis',       icon: Sparkles,        label: 'Analisis'        },
  { href: '/configuracion',  icon: Settings,        label: 'Configuracion'   },
]

export function Sidebar() {
  const pathname = usePathname()

  return (
    <aside
      className="flex flex-col h-full flex-shrink-0"
      style={{
        width: 260,
        background: 'var(--color-sidebar)',
        borderRight: '1px solid rgba(255,255,255,0.06)',
      }}
    >
      {/* Logo */}
      <div className="px-6 py-7">
        <div className="flex items-center gap-3.5">
          <div
            className="w-10 h-10 rounded-2xl flex items-center justify-center text-white font-black text-sm"
            style={{
              background: 'linear-gradient(145deg, #c2614b, #d4a574)',
              boxShadow: '0 4px 16px rgba(194, 97, 75, 0.3)',
            }}
          >
            P
          </div>
          <div>
            <p
              className="font-bold text-base leading-none tracking-wide"
              style={{ color: '#faf6f1', fontFamily: 'var(--font-display)' }}
            >
              PRAIE
            </p>
            <p className="text-xs mt-1" style={{ color: '#a8a29e', letterSpacing: '0.12em', textTransform: 'uppercase', fontSize: 10 }}>
              Panel Laura
            </p>
          </div>
        </div>
      </div>

      {/* Divider */}
      <div className="mx-5 mb-3" style={{ height: 1, background: 'rgba(255,255,255,0.06)' }} />

      {/* Nav */}
      <nav className="flex-1 px-3 space-y-0.5">
        {nav.map(({ href, icon: Icon, label }) => {
          const active = pathname === href
          return (
            <Link key={href} href={href}>
              <motion.div
                whileHover={{ x: 2 }}
                transition={{ duration: 0.12 }}
                className={cn(
                  'flex items-center gap-3 px-4 py-2.5 rounded-xl text-sm transition-all duration-150',
                  active
                    ? 'font-semibold'
                    : 'font-medium hover:bg-white/[0.04]',
                )}
                style={active ? {
                  color: '#faf6f1',
                  background: 'rgba(194, 97, 75, 0.12)',
                  borderLeft: '3px solid #c2614b',
                  paddingLeft: 13,
                } : {
                  color: '#a8a29e',
                }}
              >
                <Icon size={17} className="flex-shrink-0" style={active ? { color: '#d4a574' } : {}} />
                {label}
              </motion.div>
            </Link>
          )
        })}
      </nav>

      {/* Footer */}
      <div className="px-5 py-5" style={{ borderTop: '1px solid rgba(255,255,255,0.06)' }}>
        <div className="flex items-center gap-3">
          <div
            className="w-9 h-9 rounded-full flex items-center justify-center text-xs font-bold"
            style={{
              background: 'linear-gradient(145deg, #c2614b, #d4a574)',
              color: '#faf6f1',
            }}
          >
            L
          </div>
          <div>
            <p className="text-sm font-semibold" style={{ color: '#faf6f1' }}>Laura</p>
            <p className="text-xs" style={{ color: '#a8a29e' }}>Agente activo</p>
          </div>
          <div
            className="ml-auto w-2 h-2 rounded-full pulse-warm"
            style={{ background: '#5a8a6e' }}
          />
        </div>
      </div>
    </aside>
  )
}
