/**
 * LoginPage — 2 abas: Senha e Código no email.
 *
 * Aba Senha (default):
 *   signInWithPassword({ email, password }) → JWT direto. Sessão persiste
 *   30 dias via refresh token (Supabase default). Mais conveniente pra
 *   testers e users que voltam frequentemente.
 *
 * Aba Código no email:
 *   signInWithOtp + verifyOtp com código de 6 ou 8 dígitos. Útil quando o
 *   user esqueceu a senha ou nunca definiu uma.
 *
 * Por que NÃO usamos magic link com redirect:
 *   O Supabase do CFN/Vectra é compartilhado e tem `app-vectracargo.com.br`
 *   como única URL permitida em Redirect URLs. `verifyOtp` dispensa redirect
 *   e funciona em qualquer host.
 */
import { useEffect, useRef, useState } from 'react'
import { Link, useNavigate, useRouterState } from '@tanstack/react-router'
import { supabase } from '@/lib/supabase'
import { useAuth } from '@/lib/auth'
import { notify } from '@/lib/notify'
import {
  isPasswordExpired,
  passwordExpiryErrorMessage,
} from '@/lib/password-expiry'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { cn } from '@/lib/utils'
import {
  Mail,
  KeyRound,
  Lock,
  Loader2,
  ArrowLeft,
  Eye,
  EyeOff,
} from 'lucide-react'

type Aba = 'senha' | 'codigo'

type CodigoStage =
  | { kind: 'email' }
  | { kind: 'requesting' }
  | { kind: 'awaiting_code'; email: string }
  | { kind: 'verifying'; email: string }
  | { kind: 'error'; message: string; previousEmail?: string }

function mensagemErroAmigavel(raw: string): string {
  const lower = raw.toLowerCase()
  if (lower.includes('invalid login credentials')) {
    return 'Email ou senha incorretos. Verifique e tente novamente.'
  }
  if (lower.includes('signups not allowed') || lower.includes('not found')) {
    return 'Email não cadastrado. O GymSite Intelligence é por convite — peça acesso ao administrador.'
  }
  if (lower.includes('invalid') || lower.includes('expired')) {
    return 'Código inválido ou expirado. Solicite um novo.'
  }
  if (lower.includes('email not confirmed')) {
    return 'Email ainda não confirmado. Verifique sua caixa de entrada ou peça pro admin confirmar.'
  }
  if (lower.includes('expirou') || lower.includes('expired')) {
    return 'Sua senha de teste expirou. Use "Código no email" ou peça nova senha ao administrador.'
  }
  return raw
}

export function LoginPage() {
  const { session, mockAuth, signInDev } = useAuth()
  const navigate = useNavigate()
  const pathname = useRouterState({ select: (s) => s.location.pathname })
  const redirectedRef = useRef(false)
  const [aba, setAba] = useState<Aba>('senha')

  // Estado aba "Senha"
  const [emailSenha, setEmailSenha] = useState('')
  const [senha, setSenha] = useState('')
  const [mostrarSenha, setMostrarSenha] = useState(false)
  const [loadingSenha, setLoadingSenha] = useState(false)
  const [erroSenha, setErroSenha] = useState<string | null>(null)

  // Estado aba "Código"
  const [stageCodigo, setStageCodigo] = useState<CodigoStage>({ kind: 'email' })
  const [emailCodigo, setEmailCodigo] = useState('')
  const [code, setCode] = useState('')

  // Sessão já existe → /relatorios (uma vez; evita loop com Transitioner)
  useEffect(() => {
    if (!session) {
      redirectedRef.current = false
      return
    }
    if (pathname !== '/login' || redirectedRef.current) return
    redirectedRef.current = true
    void navigate({ to: '/relatorios', replace: true })
  }, [session, pathname, navigate])

  async function entrarComSenha(e: React.FormEvent) {
    e.preventDefault()
    const email = emailSenha.trim().toLowerCase()
    if (!email || !senha) return
    setLoadingSenha(true)
    setErroSenha(null)
    const { data, error } = await supabase.auth.signInWithPassword({
      email,
      password: senha,
    })
    setLoadingSenha(false)
    if (error) {
      setErroSenha(mensagemErroAmigavel(error.message))
      return
    }
    if (data.user && isPasswordExpired(data.user)) {
      await supabase.auth.signOut()
      setErroSenha(passwordExpiryErrorMessage(data.user))
      setAba('codigo')
      return
    }
    // onAuthStateChange dispara useAuth → useEffect manda pra /relatorios
  }

  async function requestOtp(e: React.FormEvent) {
    e.preventDefault()
    const trimmed = emailCodigo.trim().toLowerCase()
    if (!trimmed) return
    setStageCodigo({ kind: 'requesting' })
    const { error } = await supabase.auth.signInWithOtp({
      email: trimmed,
      options: { shouldCreateUser: false },
    })
    if (error) {
      notify.error(error.message)
      setStageCodigo({
        kind: 'error',
        message: error.message,
        previousEmail: trimmed,
      })
      return
    }
    setStageCodigo({ kind: 'awaiting_code', email: trimmed })
  }

  async function verifyOtpForm(e: React.FormEvent) {
    e.preventDefault()
    if (stageCodigo.kind !== 'awaiting_code' && stageCodigo.kind !== 'error')
      return
    const targetEmail =
      stageCodigo.kind === 'awaiting_code'
        ? stageCodigo.email
        : stageCodigo.previousEmail
    if (!targetEmail) return
    const trimmed = code.replace(/\D+/g, '')
    if (trimmed.length < 6) return
    setStageCodigo({ kind: 'verifying', email: targetEmail })
    const { error } = await supabase.auth.verifyOtp({
      email: targetEmail,
      token: trimmed,
      type: 'email',
    })
    if (error) {
      notify.error(error.message)
      setStageCodigo({
        kind: 'error',
        message: error.message,
        previousEmail: targetEmail,
      })
      return
    }
  }

  function resetCodigo() {
    setCode('')
    setStageCodigo({ kind: 'email' })
  }

  function trocarParaCodigo(emailPreservado?: string) {
    if (emailPreservado) setEmailCodigo(emailPreservado)
    setStageCodigo({ kind: 'email' })
    setAba('codigo')
  }

  const sentToEmail =
    stageCodigo.kind === 'awaiting_code'
      ? stageCodigo.email
      : stageCodigo.kind === 'verifying'
        ? stageCodigo.email
        : stageCodigo.kind === 'error'
          ? stageCodigo.previousEmail
          : undefined

  return (
    <div className="min-h-screen flex items-center justify-center bg-background px-4">
      <div className="w-full max-w-sm space-y-6">
        <header className="space-y-2 text-center">
          <div aria-hidden className="text-4xl">🏋️</div>
          <h1 className="text-2xl font-semibold tracking-tight">
            GymSite Intelligence
          </h1>
        </header>

        {mockAuth && (
          <div className="space-y-3 rounded-lg border border-primary/30 bg-primary/5 p-4">
            <p className="text-xs text-muted-foreground text-center">
              Modo dev — Supabase não configurado. Sessão mock automática.
            </p>
            <Button
              type="button"
              className="w-full"
              onClick={() => {
                signInDev()
                navigate({ to: '/dashboard', replace: true })
              }}
            >
              Entrar como dev → Dashboard
            </Button>
            <Button
              type="button"
              variant="outline"
              className="w-full"
              onClick={() => {
                signInDev()
                navigate({ to: '/relatorios', replace: true })
              }}
            >
              Entrar como dev → Relatórios
            </Button>
          </div>
        )}

        {/* Tabs */}
        <div role="tablist" className="flex border-b border-border">
          <TabBtn ativo={aba === 'senha'} onClick={() => setAba('senha')}>
            <Lock size={13} />
            Senha
          </TabBtn>
          <TabBtn ativo={aba === 'codigo'} onClick={() => setAba('codigo')}>
            <Mail size={13} />
            Código no email
          </TabBtn>
        </div>

        {/* ── Aba Senha ─────────────────────────────────────── */}
        {aba === 'senha' && (
          <form onSubmit={entrarComSenha} className="space-y-3">
            <Input
              type="email"
              inputMode="email"
              autoComplete="email"
              required
              placeholder="voce@empresa.com"
              value={emailSenha}
              onChange={(e) => setEmailSenha(e.target.value)}
              disabled={loadingSenha}
            />
            <div className="relative">
              <Input
                type={mostrarSenha ? 'text' : 'password'}
                autoComplete="current-password"
                required
                placeholder="Sua senha"
                value={senha}
                onChange={(e) => setSenha(e.target.value)}
                disabled={loadingSenha}
                className="pr-10"
              />
              <button
                type="button"
                onClick={() => setMostrarSenha((v) => !v)}
                className="absolute right-2 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground p-1"
                aria-label={mostrarSenha ? 'Esconder senha' : 'Mostrar senha'}
                tabIndex={-1}
              >
                {mostrarSenha ? <EyeOff size={14} /> : <Eye size={14} />}
              </button>
            </div>
            <Button
              type="submit"
              className="w-full"
              disabled={loadingSenha || !emailSenha || !senha}
            >
              {loadingSenha ? (
                <>
                  <Loader2 size={14} className="animate-spin" />
                  Entrando…
                </>
              ) : (
                <>
                  <Lock size={14} />
                  Entrar
                </>
              )}
            </Button>
            {erroSenha && (
              <Alert variant="destructive">
                <AlertDescription>{erroSenha}</AlertDescription>
              </Alert>
            )}
            <p className="text-[11px] text-center text-muted-foreground leading-relaxed">
              Conta de teste? Primeiro acesso via{' '}
              <button
                type="button"
                onClick={() => trocarParaCodigo(emailSenha)}
                className="underline underline-offset-2 hover:text-foreground"
              >
                código no email
              </button>
              . Depois o admin libera senha temporária.
            </p>
            <button
              type="button"
              onClick={() => trocarParaCodigo(emailSenha)}
              className="block w-full text-center text-xs text-muted-foreground hover:text-foreground underline-offset-2 hover:underline"
            >
              Esqueci minha senha · usar código no email
            </button>
          </form>
        )}

        {/* ── Aba Código ──────────────────────────────────────── */}
        {aba === 'codigo' && (
          <>
            <p className="text-sm text-muted-foreground text-center">
              {stageCodigo.kind === 'awaiting_code' ||
              stageCodigo.kind === 'verifying'
                ? `Cole o código de 6 dígitos enviado para ${sentToEmail}.`
                : 'Receba um código no seu email pra entrar sem senha.'}
            </p>

            {(stageCodigo.kind === 'email' ||
              stageCodigo.kind === 'requesting' ||
              (stageCodigo.kind === 'error' && !stageCodigo.previousEmail)) && (
              <form onSubmit={requestOtp} className="space-y-3">
                <Input
                  type="email"
                  inputMode="email"
                  autoComplete="email"
                  required
                  placeholder="voce@empresa.com"
                  value={emailCodigo}
                  onChange={(e) => setEmailCodigo(e.target.value)}
                  disabled={stageCodigo.kind === 'requesting'}
                />
                <Button
                  type="submit"
                  className="w-full"
                  disabled={stageCodigo.kind === 'requesting' || !emailCodigo}
                >
                  {stageCodigo.kind === 'requesting' ? (
                    <>
                      <Loader2 size={14} className="animate-spin" />
                      Enviando…
                    </>
                  ) : (
                    <>
                      <Mail size={14} />
                      Enviar código de acesso
                    </>
                  )}
                </Button>
              </form>
            )}

            {(stageCodigo.kind === 'awaiting_code' ||
              stageCodigo.kind === 'verifying' ||
              (stageCodigo.kind === 'error' && !!stageCodigo.previousEmail)) && (
              <form onSubmit={verifyOtpForm} className="space-y-3">
                <Input
                  type="text"
                  inputMode="numeric"
                  autoComplete="one-time-code"
                  autoFocus
                  required
                  maxLength={8}
                  placeholder="000000"
                  value={code}
                  onChange={(e) =>
                    setCode(e.target.value.replace(/[^0-9]/g, '').slice(0, 8))
                  }
                  disabled={stageCodigo.kind === 'verifying'}
                  className="text-center text-2xl tracking-[0.4em] font-mono"
                />
                <Button
                  type="submit"
                  className="w-full"
                  disabled={stageCodigo.kind === 'verifying' || code.length < 6}
                >
                  {stageCodigo.kind === 'verifying' ? (
                    <>
                      <Loader2 size={14} className="animate-spin" />
                      Verificando…
                    </>
                  ) : (
                    <>
                      <KeyRound size={14} />
                      Entrar
                    </>
                  )}
                </Button>
                <Button
                  type="button"
                  variant="ghost"
                  size="sm"
                  className="w-full"
                  onClick={resetCodigo}
                  disabled={stageCodigo.kind === 'verifying'}
                >
                  <ArrowLeft size={14} />
                  Usar outro email
                </Button>
              </form>
            )}

            {stageCodigo.kind === 'error' && (
              <Alert variant="destructive">
                <AlertDescription>
                  {mensagemErroAmigavel(stageCodigo.message)}
                </AlertDescription>
              </Alert>
            )}
          </>
        )}

        <p className="text-xs text-muted-foreground text-center">
          Ao continuar, você concorda com a{' '}
          <Link
            to="/privacidade"
            className="underline hover:text-foreground transition-colors"
          >
            Política de Privacidade
          </Link>
          .
        </p>
      </div>
    </div>
  )
}

function TabBtn({
  ativo,
  onClick,
  children,
}: {
  ativo: boolean
  onClick: () => void
  children: React.ReactNode
}) {
  return (
    <button
      type="button"
      role="tab"
      aria-selected={ativo}
      onClick={onClick}
      className={cn(
        'flex-1 inline-flex items-center justify-center gap-1.5 py-2.5 text-sm transition-colors -mb-px border-b-2',
        ativo
          ? 'border-primary text-foreground'
          : 'border-transparent text-muted-foreground hover:text-foreground',
      )}
    >
      {children}
    </button>
  )
}
