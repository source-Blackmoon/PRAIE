import type { Metadata } from 'next'
import { DM_Sans, Playfair_Display } from 'next/font/google'
import './globals.css'
import { Sidebar } from '@/components/layout/Sidebar'

const dmSans = DM_Sans({
  subsets: ['latin'],
  variable: '--font-dm-sans',
  weight: ['400', '500', '600', '700'],
})

const playfair = Playfair_Display({
  subsets: ['latin'],
  variable: '--font-playfair',
  weight: ['400', '500', '600', '700'],
})

export const metadata: Metadata = {
  title: 'PRAIE — Panel Laura',
  description: 'Dashboard de administración del agente WhatsApp Laura',
}

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="es" className={`${dmSans.variable} ${playfair.variable}`}>
      <body className={dmSans.className} style={{ background: 'var(--color-surface)' }}>
        <div style={{ display: 'flex', height: '100vh' }}>
          <Sidebar />
          <main style={{ flex: 1, overflow: 'auto', padding: '2.5rem 3rem' }}>
            {children}
          </main>
        </div>
      </body>
    </html>
  )
}
