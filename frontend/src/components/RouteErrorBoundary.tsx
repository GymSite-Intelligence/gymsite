import { Component, type ErrorInfo, type ReactNode } from 'react'
import { Link } from '@tanstack/react-router'
import { Button } from '@/components/ui/button'

interface Props {
  children: ReactNode
  /** Título curto exibido no fallback. */
  title?: string
}

interface State {
  error: Error | null
}

/** Captura erros de render (ex.: React #310) e evita tela branca. */
export class RouteErrorBoundary extends Component<Props, State> {
  state: State = { error: null }

  static getDerivedStateFromError(error: Error): State {
    return { error }
  }

  componentDidCatch(error: Error, info: ErrorInfo) {
    console.error('[RouteErrorBoundary]', error, info.componentStack)
  }

  render() {
    if (!this.state.error) return this.props.children

    const msg = this.state.error.message
    const isHooks =
      msg.includes('310') ||
      msg.includes('Rendered more hooks') ||
      msg.includes('Rendered fewer hooks')

    return (
      <div className="rounded-lg border border-veredito-reprovado/40 bg-veredito-reprovado/5 p-6 space-y-3 max-w-xl">
        <h2 className="font-semibold text-veredito-reprovado">
          {this.props.title ?? 'Erro ao carregar esta página'}
        </h2>
        <p className="text-sm text-muted-foreground">
          {isHooks
            ? 'O navegador pode estar com uma versão antiga do app em cache. Tente Ctrl+Shift+R ou abra em aba anônima.'
            : 'Algo impediu a renderização. Detalhe técnico abaixo.'}
        </p>
        <p className="text-xs font-mono text-muted-foreground break-all">{msg}</p>
        <div className="flex flex-wrap gap-2">
          <Button type="button" variant="outline" size="sm" onClick={() => window.location.reload()}>
            Recarregar
          </Button>
          <Button variant="ghost" size="sm" asChild>
            <Link to="/relatorios">Voltar aos relatórios</Link>
          </Button>
        </div>
      </div>
    )
  }
}
