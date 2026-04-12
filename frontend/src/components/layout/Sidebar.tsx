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
  { href: '/analisis',       icon: Sparkles,        label: 'Análisis con IA' },
  { href: '/configuracion',  icon: Settings,        label: 'Configuración'   },
]

export function Sidebar() {
  const pathname = usePathname()

  return (
    <aside
      style={{ width: 260, background: 'var(--color-sidebar)' }}
      className="flex flex-col h-full flex-shrink-0"
    >
      {/* Logo */}
      <div className="px-6 py-7">
        <div className="flex items-center gap-3">
          <div
            className="w-9 h-9 rounded-xl flex items-center justify-center text-white font-black text-sm gradient-bg"
          >
            P
          </div>
          <div>
            <p className="text-white font-bold text-base leading-none">PRAIE</p>
            <p className="text-purple-300 text-xs mt-0.5">Panel Laura</p>
          </div>
        </div>
      </div>

      {/* Nav */}
      <nav className="flex-1 px-3 space-y-1">
        {nav.map(({ href, icon: Icon, label }) => {
          const active = pathname === href
          return (
            <Link key={href} href={href}>
              <motion.div
                whileHover={{ x: 3 }}
                transition={{ duration: 0.15 }}
                className={cn(
                  'flex items-center gap-3 px-4 py-2.5 rounded-xl text-sm font-medium transition-colors duration-150',
                  active
                    ? 'text-white gradient-bg shadow-lg'
                    : 'text-purple-200 hover:text-white hover:bg-white/10',
                )}
              >
                <Icon size={18} className="flex-shrink-0" />
                {label}
              </motion.div>
            </Link>
          )
        })}
      </nav>

      {/* Footer */}
      <div className="px-6 py-5 border-t border-white/10">
        <div className="flex items-center gap-2.5">
          <div className="w-8 h-8 rounded-full gradient-bg flex items-center justify-center text-white text-xs font-bold">
            L
          </div>
          <div>
            <p className="text-white text-sm font-medium">Laura</p>
            <p className="text-purple-300 text-xs">Agente activo</p>
          </div>
          <div className="ml-auto w-2 h-2 rounded-full bg-green-400 animate-pulse" />
        </div>
      </div>
    </aside>
  )
}
