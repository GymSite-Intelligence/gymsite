import { useTheme } from 'next-themes'
import {
  DropdownMenuLabel,
  DropdownMenuRadioGroup,
  DropdownMenuRadioItem,
  DropdownMenuSeparator,
} from '@/components/ui/dropdown-menu'
import {
  APP_THEME_OPTIONS,
  applyAppThemeToDocument,
  isAppThemeId,
  normalizeAppThemeId,
  persistAppThemeToUser,
} from '@/lib/app-theme'
import { useAuth } from '@/lib/auth'
import { BarChart3Icon, PaletteIcon } from 'lucide-react'

const THEME_ICONS = {
  'bar-chart-3': BarChart3Icon,
  palette: PaletteIcon,
} as const

export function ThemeMenuItems() {
  const { theme, setTheme } = useTheme()
  const { user } = useAuth()
  const active = normalizeAppThemeId(theme)

  function onSelect(next: string) {
    if (!isAppThemeId(next) || next === active) return
    applyAppThemeToDocument(next)
    setTheme(next)
    persistAppThemeToUser(next, user)
  }

  return (
    <>
      <DropdownMenuSeparator />
      <DropdownMenuLabel className="text-xs text-muted-foreground">
        Aparência
      </DropdownMenuLabel>
      <DropdownMenuRadioGroup value={active} onValueChange={onSelect}>
        {APP_THEME_OPTIONS.map((opt) => {
          const Icon = THEME_ICONS[opt.icon]
          return (
            <DropdownMenuRadioItem key={opt.id} value={opt.id}>
              <Icon />
              {opt.label}
            </DropdownMenuRadioItem>
          )
        })}
      </DropdownMenuRadioGroup>
    </>
  )
}
