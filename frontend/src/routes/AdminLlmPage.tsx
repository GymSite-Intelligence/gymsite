/**
 * Admin — troca o provedor do chat (NVIDIA / Ollama) sem editar .env.
 * Override em Redis; chaves de API nunca sobem pra UI.
 * Gemini: deprecated — não oferece na UI (só se .env ainda apontar).
 */
import { useEffect, useRef, useState } from 'react'
import { useNavigate } from '@tanstack/react-router'
import { Loader2, Cpu } from 'lucide-react'
import { useIsAdmin } from '@/hooks/useIsAdmin'
import {
  useLlmConfig,
  usePatchLlmConfig,
  type LlmProviderOption,
} from '@/hooks/useLlmConfig'
import { Button } from '@/components/ui/button'
import { cn } from '@/lib/utils'

const LABELS: Record<string, { title: string; hint: string }> = {
  nvidia: {
    title: 'NVIDIA',
    hint: 'NIM na nuvem — bom pra tools no chat',
  },
  ollama: {
    title: 'Ollama',
    hint: 'Local na sua máquina — só funciona se a API rodar aí',
  },
}

export function AdminLlmPage() {
  const isAdmin = useIsAdmin()
  const navigate = useNavigate()
  const redirectedRef = useRef(false)
  const { data, isLoading, error, refetch } = useLlmConfig()
  const patch = usePatchLlmConfig()
  const [picked, setPicked] = useState<string | null>(null)

  useEffect(() => {
    if (!isAdmin && !redirectedRef.current) {
      redirectedRef.current = true
      navigate({ to: '/dashboard', replace: true })
    }
  }, [isAdmin, navigate])

  useEffect(() => {
    if (data?.provider) setPicked(data.provider)
  }, [data?.provider])

  if (!isAdmin) return null

  const active = picked ?? data?.provider ?? 'nvidia'
  const saving = patch.isPending
  const geminiLegacy = data?.provider === 'gemini'

  return (
    <div className="mx-auto max-w-xl space-y-6 p-6">
      <div className="flex items-start gap-3">
        <Cpu className="mt-0.5 size-6 text-primary" aria-hidden />
        <div>
          <h1 className="text-xl font-semibold text-foreground">Provedor de IA do chat</h1>
          <p className="mt-1 text-sm text-muted-foreground">
            Troca NVIDIA ou Ollama sem editar o arquivo de ambiente. Chaves secretas
            ficam só no servidor. Gemini está descontinuado no chat.
          </p>
        </div>
      </div>

      {isLoading && (
        <div className="flex items-center gap-2 text-sm text-muted-foreground">
          <Loader2 className="size-4 animate-spin" />
          Carregando…
        </div>
      )}

      {error && (
        <p className="rounded-md border border-destructive/40 bg-destructive/10 px-3 py-2 text-sm text-destructive">
          {(error as Error).message}
        </p>
      )}

      {data && (
        <>
          <p className="text-sm text-muted-foreground">
            Ativo: <span className="text-foreground font-medium">{data.provider}</span>
            {' · '}
            modelo <span className="text-foreground">{data.model}</span>
            {' · '}
            origem {data.source === 'redis' ? 'override (Redis)' : '.env'}
            {data.nvidia_key_configured ? '' : ' · NVIDIA sem chave no servidor'}
          </p>

          {geminiLegacy && (
            <p className="rounded-md border border-border bg-muted/40 px-3 py-2 text-sm text-muted-foreground">
              Gemini ainda ativo via .env/override — descontinuado. Escolha NVIDIA ou
              Ollama abaixo.
            </p>
          )}

          <div className="space-y-2" role="radiogroup" aria-label="Provedor de IA">
            {data.options
              .filter((opt) => opt !== 'gemini')
              .map((opt) => {
              const meta = LABELS[opt] ?? { title: opt, hint: '' }
              const selected = active === opt
              return (
                <button
                  key={opt}
                  type="button"
                  role="radio"
                  aria-checked={selected}
                  disabled={saving}
                  onClick={() => setPicked(opt)}
                  className={cn(
                    'w-full rounded-md border px-4 py-3 text-left transition-colors',
                    selected
                      ? 'border-primary bg-primary/10'
                      : 'border-border bg-card hover:border-primary/50',
                  )}
                >
                  <div className="font-medium text-foreground">{meta.title}</div>
                  <div className="text-xs text-muted-foreground">{meta.hint}</div>
                </button>
              )
            })}
          </div>

          <div className="flex flex-wrap gap-2">
            <Button
              disabled={saving || !picked || picked === data.provider}
              onClick={() => {
                if (!picked) return
                patch.mutate(picked as LlmProviderOption, {
                  onSuccess: () => refetch(),
                })
              }}
            >
              {saving ? (
                <>
                  <Loader2 className="mr-2 size-4 animate-spin" />
                  Gravando…
                </>
              ) : (
                'Aplicar'
              )}
            </Button>
            <Button
              variant="outline"
              disabled={saving || data.source === 'env'}
              onClick={() =>
                patch.mutate('env', {
                  onSuccess: () => refetch(),
                })
              }
            >
              Voltar ao .env
            </Button>
          </div>

          {patch.isError && (
            <p className="text-sm text-destructive">{(patch.error as Error).message}</p>
          )}
          {patch.isSuccess && !patch.isPending && (
            <p className="text-sm text-primary">Provedor atualizado. Próximo chat já usa o novo.</p>
          )}
        </>
      )}
    </div>
  )
}

export default AdminLlmPage
