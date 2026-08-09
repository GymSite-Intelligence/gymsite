import { Check, Zap } from 'lucide-react'
import { SITE_ORIGIN } from './explorar-chrome'

const LOGIN = '/login'

const BENEFICIOS = [
  'Análise completa dos concorrentes',
  'Tendência CNPJ (Receita Federal)',
  'Conclusão estratégica do recorte',
  'Perfil da região com fonte carimbada',
  'Aluguel de viabilidade (modelo GymSite)',
] as const

export function ExplorarGateModal({
  open,
  mensagem,
  onClose,
}: {
  open: boolean
  mensagem?: string
  onClose: () => void
}) {
  if (!open) return null

  return (
    <div
      className="absolute inset-0 z-80 grid place-items-center p-4"
      role="dialog"
      aria-modal="true"
      aria-labelledby="explorar-app-gate-title"
    >
      <button
        type="button"
        className="absolute inset-0 border-0 bg-[#13161b]/75"
        aria-label="Fechar"
        onClick={onClose}
      />
      <div className="explorar-chrome relative z-10 w-full max-w-md rounded-2xl border p-6 shadow-2xl">
        <button
          type="button"
          className="absolute right-3 top-2 text-xl text-muted-foreground"
          onClick={onClose}
          aria-label="Fechar"
        >
          ×
        </button>
        <div className="mb-3 grid size-10 place-items-center rounded-full bg-primary/15 text-primary">
          <Zap className="size-5" />
        </div>
        <h2 id="explorar-app-gate-title" className="text-lg font-bold text-foreground">
          Sua pesquisa no mapa está pronta
        </h2>
        <p className="mt-2 text-sm text-muted-foreground">
          {mensagem ||
            'Na degustação do site você tem 1 recorte grátis. Crie sua conta para o relatório completo e mais recortes.'}
        </p>
        <ul className="mt-4 space-y-2 text-sm">
          {BENEFICIOS.map((b) => (
            <li key={b} className="flex gap-2">
              <Check className="mt-0.5 size-4 shrink-0 text-primary" />
              {b}
            </li>
          ))}
        </ul>
        <a
          href={LOGIN}
          className="explorar-cta mt-5 flex w-full items-center justify-center no-underline"
        >
          Criar conta grátis
        </a>
        <a
          href={`${SITE_ORIGIN}/degustacao`}
          className="mt-2 flex h-10 items-center justify-center text-sm font-semibold text-foreground no-underline"
        >
          Falar com um especialista
        </a>
        <p className="mt-3 text-center text-xs text-muted-foreground">
          Já tem conta?{' '}
          <a href={LOGIN} className="text-primary no-underline">
            Entrar
          </a>
        </p>
      </div>
    </div>
  )
}
