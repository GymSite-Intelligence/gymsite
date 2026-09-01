/**
 * Temas visuais do GymSite Intelligence — **escuro** + **claro**.
 *
 * - `escuro`: fundo canônico (#13161b), primary lime (#84cc01).
 * - `claro`: fundo claro (:root), mesma marca em primary/sidebar.
 */
import type { User } from '@supabase/supabase-js'
import { supabase } from '@/lib/supabase'
import { isSupabaseConfigured } from '@/lib/mock-auth'

export const APP_THEME_STORAGE_KEY = 'gymsite-theme'

export const APP_THEME_IDS = ['escuro', 'claro'] as const
export type AppThemeId = (typeof APP_THEME_IDS)[number]

export type AppThemeOption = {
  id: AppThemeId
  label: string
  icon: 'moon' | 'sun'
}

export const APP_THEME_OPTIONS: readonly AppThemeOption[] = [
  { id: 'escuro', label: 'Escuro', icon: 'moon' },
  { id: 'claro', label: 'Claro', icon: 'sun' },
] as const

export const DEFAULT_APP_THEME: AppThemeId = 'escuro'

const LEGACY_THEME_MAP: Record<string, AppThemeId> = {
  analitico: 'escuro',
  vectra: 'escuro',
  dark: 'escuro',
  escuro: 'escuro',
  geo: 'escuro',
  light: 'claro',
  claro: 'claro',
  system: 'escuro',
}

export function isAppThemeId(value: unknown): value is AppThemeId {
  return typeof value === 'string' && (APP_THEME_IDS as readonly string[]).includes(value)
}

/** Converte ids legados (analitico/vectra/geo/light/dark) para escuro | claro. */
export function migrateAppThemeId(value: unknown): AppThemeId {
  if (isAppThemeId(value)) return value
  if (typeof value === 'string' && value in LEGACY_THEME_MAP) {
    return LEGACY_THEME_MAP[value]
  }
  return DEFAULT_APP_THEME
}

export function normalizeAppThemeId(value: unknown): AppThemeId {
  return migrateAppThemeId(value)
}

export function isAppThemeDark(theme: AppThemeId): boolean {
  return theme === 'escuro'
}

export function readStoredAppTheme(): AppThemeId | null {
  try {
    const raw = localStorage.getItem(APP_THEME_STORAGE_KEY)
    if (raw == null) return null
    return migrateAppThemeId(raw)
  } catch {
    return null
  }
}

/** Aplica data-theme, classe .dark e color-scheme antes do React hidratar. */
export function applyAppThemeToDocument(theme: AppThemeId): void {
  const root = document.documentElement
  root.setAttribute('data-theme', theme)
  if (isAppThemeDark(theme)) {
    root.classList.add('dark')
    root.style.colorScheme = 'dark'
  } else {
    root.classList.remove('dark')
    root.style.colorScheme = 'light'
  }
}

export function readAppThemeFromUser(user: User | null | undefined): AppThemeId | null {
  if (!user) return null
  const meta = user.user_metadata?.app_theme
  if (meta == null) return null
  return migrateAppThemeId(meta)
}

/** Persiste no Supabase (fire-and-forget). localStorage é gerido pelo next-themes. */
export function persistAppThemeToUser(theme: AppThemeId, user: User | null | undefined): void {
  if (!user || !isSupabaseConfigured()) return
  void supabase.auth.updateUser({ data: { app_theme: theme } }).catch(() => {
    /* preferência local já salva; falha de rede não bloqueia UI */
  })
}
