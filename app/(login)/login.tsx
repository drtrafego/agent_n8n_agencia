'use client';

import Link from 'next/link';
import { useActionState } from 'react';
import { useSearchParams } from 'next/navigation';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Loader2, Bot, Zap, Shield } from 'lucide-react';
import { signIn, signUp } from './actions';
import { ActionState } from '@/lib/auth/middleware';

export function Login({ mode = 'signin' }: { mode?: 'signin' | 'signup' }) {
  const searchParams = useSearchParams();
  const redirect = searchParams.get('redirect');
  const priceId = searchParams.get('priceId');
  const inviteId = searchParams.get('inviteId');
  const [state, formAction, pending] = useActionState<ActionState, FormData>(
    mode === 'signin' ? signIn : signUp,
    { error: '' }
  );

  return (
    <div className="min-h-[100dvh] flex bg-zinc-950">

      {/* Painel esquerdo — visível só no desktop */}
      <div className="hidden lg:flex lg:w-1/2 relative flex-col items-center justify-center overflow-hidden">
        {/* Fundo com gradiente */}
        <div className="absolute inset-0 bg-gradient-to-br from-indigo-950 via-zinc-900 to-zinc-950" />
        {/* Grid sutil */}
        <div
          className="absolute inset-0 opacity-10"
          style={{
            backgroundImage:
              'linear-gradient(rgba(99,102,241,0.3) 1px, transparent 1px), linear-gradient(90deg, rgba(99,102,241,0.3) 1px, transparent 1px)',
            backgroundSize: '40px 40px',
          }}
        />
        {/* Orbe de luz */}
        <div className="absolute top-1/3 left-1/2 -translate-x-1/2 -translate-y-1/2 w-96 h-96 bg-indigo-600/20 rounded-full blur-3xl" />

        {/* Conteúdo */}
        <div className="relative z-10 flex flex-col items-center gap-8 px-12 text-center">
          {/* Logo */}
          <div className="flex h-16 w-16 items-center justify-center rounded-2xl bg-indigo-600 shadow-lg shadow-indigo-600/30">
            <Bot size={32} className="text-white" />
          </div>

          <div>
            <h1 className="text-4xl font-bold text-white tracking-tight">
              Agente 24 Horas
            </h1>
            <p className="mt-3 text-base text-zinc-400 max-w-xs leading-relaxed">
              Automação inteligente que atende, qualifica e agenda — sem parar.
            </p>
          </div>

          {/* Features */}
          <div className="flex flex-col gap-3 w-full max-w-xs">
            {[
              { icon: Zap, text: 'Respostas em segundos, 24h por dia' },
              { icon: Bot, text: 'Agente autônomo com IA generativa' },
              { icon: Shield, text: 'Controle total na palma da mão' },
            ].map(({ icon: Icon, text }) => (
              <div key={text} className="flex items-center gap-3 rounded-xl bg-white/5 px-4 py-3">
                <Icon size={16} className="text-indigo-400 shrink-0" />
                <span className="text-sm text-zinc-300">{text}</span>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Painel direito — formulário */}
      <div className="flex flex-1 flex-col items-center justify-center px-6 py-12 lg:px-12">
        {/* Logo mobile */}
        <div className="lg:hidden flex flex-col items-center mb-10">
          <div className="flex h-14 w-14 items-center justify-center rounded-2xl bg-indigo-600 shadow-lg shadow-indigo-600/30 mb-4">
            <Bot size={28} className="text-white" />
          </div>
          <h1 className="text-2xl font-bold text-white">Agente 24 Horas</h1>
          <p className="mt-1 text-sm text-zinc-500">Automação que nunca para</p>
        </div>

        <div className="w-full max-w-sm">
          <div className="mb-8">
            <h2 className="text-2xl font-bold text-white">
              {mode === 'signin' ? 'Bem-vindo de volta' : 'Criar conta'}
            </h2>
            <p className="mt-1 text-sm text-zinc-500">
              {mode === 'signin'
                ? 'Entre para acessar seu painel'
                : 'Comece a automatizar seu negócio'}
            </p>
          </div>

          <form className="space-y-4" action={formAction}>
            <input type="hidden" name="redirect" value={redirect || ''} />
            <input type="hidden" name="priceId" value={priceId || ''} />
            <input type="hidden" name="inviteId" value={inviteId || ''} />

            <div className="space-y-1.5">
              <Label htmlFor="email" className="text-sm font-medium text-zinc-300">
                Email
              </Label>
              <Input
                id="email"
                name="email"
                type="email"
                autoComplete="email"
                defaultValue={state.email}
                required
                maxLength={50}
                className="h-11 rounded-xl bg-zinc-800 border-zinc-700 text-zinc-100 placeholder:text-zinc-500 focus:border-indigo-500 focus:ring-indigo-500"
                placeholder="seu@email.com"
              />
            </div>

            <div className="space-y-1.5">
              <Label htmlFor="password" className="text-sm font-medium text-zinc-300">
                Senha
              </Label>
              <Input
                id="password"
                name="password"
                type="password"
                autoComplete={mode === 'signin' ? 'current-password' : 'new-password'}
                defaultValue={state.password}
                required
                minLength={8}
                maxLength={100}
                className="h-11 rounded-xl bg-zinc-800 border-zinc-700 text-zinc-100 placeholder:text-zinc-500 focus:border-indigo-500 focus:ring-indigo-500"
                placeholder="••••••••"
              />
            </div>

            {state?.error && (
              <div className="rounded-xl bg-red-500/10 border border-red-500/20 px-4 py-3 text-sm text-red-400">
                {state.error}
              </div>
            )}

            <Button
              type="submit"
              className="w-full h-11 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white font-medium text-sm transition-colors"
              disabled={pending}
            >
              {pending ? (
                <>
                  <Loader2 className="animate-spin mr-2 h-4 w-4" />
                  Carregando...
                </>
              ) : mode === 'signin' ? (
                'Entrar'
              ) : (
                'Criar conta'
              )}
            </Button>
          </form>

          <div className="mt-6 text-center">
            <span className="text-sm text-zinc-500">
              {mode === 'signin' ? 'Não tem conta? ' : 'Já tem conta? '}
            </span>
            <Link
              href={`${mode === 'signin' ? '/sign-up' : '/sign-in'}${redirect ? `?redirect=${redirect}` : ''}${priceId ? `&priceId=${priceId}` : ''}`}
              className="text-sm font-medium text-indigo-400 hover:text-indigo-300 transition-colors"
            >
              {mode === 'signin' ? 'Criar conta' : 'Entrar'}
            </Link>
          </div>
        </div>
      </div>
    </div>
  );
}
