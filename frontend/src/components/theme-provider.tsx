import { useEffect, useRef } from 'react'
import { ThemeProvider as NextThemesProvider, useTheme } from 'next-themes'
import {
  APP_THEME_STORAGE_KEY,
  DEFAULT_APP_THEME,
  applyAppThemeToDocument,
  isAppThemeId,
  readAppThemeFromUser,
  readStoredAppTheme,
} from '@/lib/app-theme'
import { useAuth } from '@/lib/auth'

export function ThemeProvider({ children }: { children: React.ReactNode }) {
  return (
    <NextThemesProvider
      attribute="data-theme"
      defaultTheme={DEFAULT_APP_THEME}
      themes={['analitico', 'vectra']}
      enableSystem={false}
      storageKey={APP_THEME_STORAGE_KEY}
      disableTransitionOnChange
    >
      <ThemeDocumentSync />
      {children}
    </NextThemesProvider>
  )
}

/** Garante .dark + color-scheme mesmo com temas custom (não light/dark do next-themes). */
function ThemeDocumentSync() {
  const { resolvedTheme, theme } = useTheme()
  const active = resolvedTheme ?? theme

  useEffect(() => {
    if (!isAppThemeId(active)) return
    applyAppThemeToDocument(active)
  }, [active])

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
