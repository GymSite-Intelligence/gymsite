/**
 * lib/notify.ts — wrapper finíssimo em volta de `sonner`.
 *
 * Por que envolver:
 * - Define defaults consistentes (duração, posição) num lugar só.
 * - Permite trocar a lib no futuro sem catar `toast.x()` em N arquivos.
 * - Helpers semânticos pra erros vindos de Supabase/fetch (extrai mensagem).
 */
import { toast } from 'sonner'

const DEFAULT_DURATION = 4500

export const notify = {
  success(message: string, opts?: { description?: string; duration?: number }) {
    return toast.success(message, {
      description: opts?.description,
      duration: opts?.duration ?? DEFAULT_DURATION,
    })
  },

  info(message: string, opts?: { description?: string; duration?: number }) {
    return toast(message, {
      description: opts?.description,
      duration: opts?.duration ?? DEFAULT_DURATION,
    })
  },

  warning(message: string, opts?: { description?: string; duration?: number }) {
    return toast.warning(message, {
      description: opts?.description,
      duration: opts?.duration ?? DEFAULT_DURATION,
    })
  },

  /**
   * Mostra erro. Aceita Error | string | mensagem técnica vinda do Supabase.
   * Duração padrão maior (6s) — erros costumam ser longos e o user quer
   * tempo de ler.
   */
  error(err: unknown, opts?: { description?: string; duration?: number }) {
    const message = extractErrorMessage(err)
    return toast.error(message, {
      description: opts?.description,
      duration: opts?.duration ?? 6000,
    })
  },

  /**
   * Cria um toast "carregando…" e devolve `{ success, error, dismiss }` pra
   * atualizar in-place quando a promise terminar. Útil em operações lentas
   * (ex: dispara pipeline).
   */
  loading(message: string) {
    const id = toast.loading(message)
    return {
      success: (msg: string) =>
        toast.success(msg, { id, duration: DEFAULT_DURATION }),
      error: (err: unknown) =>
        toast.error(extractErrorMessage(err), { id, duration: 6000 }),
      dismiss: () => toast.dismiss(id),
    }
  },

  dismiss(id?: string | number) {
    toast.dismiss(id)
  },
}

export function extractErrorMessage(err: unknown): string {
  if (err instanceof Error) return err.message
  if (typeof err === 'string') return err
  if (err && typeof err === 'object') {
    const e = err as { message?: unknown; error?: unknown }
    if (typeof e.message === 'string') return e.message
    if (typeof e.error === 'string') return e.error
  }
  return 'Algo deu errado. Tente novamente.'
}
