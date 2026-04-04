import type { Metadata } from 'next'
import { Inter } from 'next/font/google'
import './globals.css'
import { Sidebar } from '@/components/layout/Sidebar'

const inter = Inter({ subsets: ['latin'] })

export const metadata: Metadata = {
  title: 'PRAIE — Panel Laura',
  description: 'Dashboard de administración del agente WhatsApp Laura',
}

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="es">
      <body className={inter.className} style={{ background: 'var(--color-surface)' }}>
        <div style={{ display: 'flex', height: '100vh' }}>
          <Sidebar />
          <main style={{ flex: 1, overflow: 'auto', padding: '2rem' }}>
            {children}
          </main>
        </div>
      </body>
    </html>
  )
}
