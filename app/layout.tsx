import './globals.css';
import type { Metadata, Viewport } from 'next';
import { Manrope } from 'next/font/google';
import { StackProvider, StackTheme } from '@stackframe/stack';
import { stackServerApp } from '@/lib/stack';

export const metadata: Metadata = {
  title: 'DR.TRÁFEGO — WhatsApp Inbox',
  description: 'Painel de atendimento WhatsApp para agência de tráfego pago.'
};

export const viewport: Viewport = {
  maximumScale: 1
};

const manrope = Manrope({ subsets: ['latin'] });

export default function RootLayout({
  children
}: {
  children: React.ReactNode;
}) {
  return (
    <html
      lang="pt-BR"
      className={`dark ${manrope.className}`}
    >
      <body className="min-h-[100dvh] bg-zinc-950 text-zinc-100">
        <StackProvider app={stackServerApp}>
          <StackTheme>
            {children}
          </StackTheme>
        </StackProvider>
      </body>
    </html>
  );
}
