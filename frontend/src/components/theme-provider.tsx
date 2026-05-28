import { useEffect, useRef } from 'react'
import { ThemeProvider as NextThemesProvider, useTheme } from 'next-themes'
import {
  APP_THEME_STORAGE_KEY,
  DEFAULT_APP_THEME,
  applyAppThemeToDocument,
  isAppThemeId,
  normalizeAppThemeId,
  readAppThemeFromUser,
  readStoredAppTheme,
} from '@/lib/app-theme'
import { useAuth } from '@/lib/auth'

export function ThemeProvider({ children }: { children: React.ReactNode }) {
  return (
    <NextThemesProvider
      attribute="data-theme"
      defaultTheme={DEFAULT_APP_THEME}
      themes={['escuro', 'claro']}
      enableSystem={false}
      storageKey={APP_THEME_STORAGE_KEY}
      disableTransitionOnChange
    >
      <ThemeStorageSanitizer />
      <ThemeDocumentSync />
      {children}
    </NextThemesProvider>
  )
}

/** Corrige localStorage legado (ex.: "dark") antes do next-themes aplicar atributo inválido. */
function ThemeStorageSanitizer() {
  const { setTheme } = useTheme()

  useEffect(() => {
    try {
      const raw = localStorage.getItem(APP_THEME_STORAGE_KEY)
      const fixed = normalizeAppThemeId(raw)
      if (raw !== fixed) {
        localStorage.setItem(APP_THEME_STORAGE_KEY, fixed)
      }
      applyAppThemeToDocument(fixed)
      if (!isAppThemeId(raw) || raw !== fixed) {
        setTheme(fixed)
      }
    } catch {
      applyAppThemeToDocument(DEFAULT_APP_THEME)
      setTheme(DEFAULT_APP_THEME)
    }
  }, [setTheme])

  return null
}

/** Garante .dark + data-theme no <html> a cada mudança (next-themes só persiste o atributo). */
function ThemeDocumentSync() {
  const { theme } = useTheme()

  useEffect(() => {
    if (!isAppThemeId(theme)) return
    applyAppThemeToDocument(theme)
  }, [theme])

  return null
}

/** Em dispositivo novo: usa user_metadata.app_theme se não houver preferência local. Montar dentro de AuthProvider. */
export function ThemeUserSync() {
  const { user, loading } = useAuth()
  const { setTheme } = useTheme()
  const lastUserIdRef = useRef<string | null>(null)

  useEffect(() => {
    if (loading) return
    if (!user) {
      lastUserIdRef.current = null
      return
    }
    if (lastUserIdRef.current === user.id) return
    lastUserIdRef.current = user.id

    const local = readStoredAppTheme()
    if (local) return

    const fromUser = readAppThemeFromUser(user)
    if (fromUser) {
      setTheme(fromUser)
    }
  }, [user, loading, setTheme])

  return null
}
