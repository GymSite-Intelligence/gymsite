/**
 * Temas visuais do GymSite Intelligence (exatamente 2 variantes).
 *
 * Escolha de produto: **analitico** + **vectra** (ambos escuros).
 * - `analitico`: neutro escuro atual — leitura de dados / analytics.
 * - `vectra`: mesmo base escuro com acento teal/cyan da marca Vectra Cargo
 *   (mais contraste entre opções do que dois modos claro/escuro genéricos).
 *
 * `claro` (:root) permanece no CSS para eventual uso futuro, mas não é exposto no menu.
 */
import type { User } from '@supabase/supabase-js'
import { supabase } from '@/lib/supabase'
import { isSupabaseConfigured } from '@/lib/mock-auth'

export const APP_THEME_STORAGE_KEY = 'gymsite-theme'

export const APP_THEME_IDS = ['analitico', 'vectra'] as const
export type AppThemeId = (typeof APP_THEME_IDS)[number]

export type AppThemeOption = {
  id: AppThemeId
  label: string
  /** Ícone sugerido no menu (nome lucide). */
  icon: 'bar-chart-3' | 'palette'
}

export const APP_THEME_OPTIONS: readonly AppThemeOption[] = [
  { id: 'analitico', label: 'Analítico (escuro)', icon: 'bar-chart-3' },
  { id: 'vectra', label: 'Vectra (marca)', icon: 'palette' },
] as const

export const DEFAULT_APP_THEME: AppThemeId = 'analitico'

export function isAppThemeId(value: unknown): value is AppThemeId {
  return typeof value === 'string' && (APP_THEME_IDS as readonly string[]).includes(value)
}

/** Valores legados (light/dark/system) ou lixo no storage → tema válido. */
export function normalizeAppThemeId(value: unknown): AppThemeId {
  return isAppThemeId(value) ? value : DEFAULT_APP_THEME
}

export function readStoredAppTheme(): AppThemeId | null {
  try {
    const raw = localStorage.getItem(APP_THEME_STORAGE_KEY)
    return isAppThemeId(raw) ? raw : null
  } catch {
    return null
  }
}

/** Aplica classe escura, data-theme e color-scheme antes do React hidratar. */
export function applyAppThemeToDocument(theme: AppThemeId): void {
  const root = document.documentElement
  root.setAttribute('data-theme', theme)
  root.classList.add('dark')
  root.style.colorScheme = 'dark'
}

export function readAppThemeFromUser(user: User | null | undefined): AppThemeId | null {
  if (!user) return null
  const meta = user.user_metadata?.app_theme
  return isAppThemeId(meta) ? meta : null
}

/** Persiste no Supabase (fire-and-forget). localStorage é gerido pelo next-themes. */
export function persistAppThemeToUser(theme: AppThemeId, user: User | null | undefined): void {
  if (!user || !isSupabaseConfigured()) return
  void supabase.auth.updateUser({ data: { app_theme: theme } }).catch(() => {
    /* preferência local já salva; falha de rede não bloqueia UI */
  })
}
