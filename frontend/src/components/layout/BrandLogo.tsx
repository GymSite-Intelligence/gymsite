import { useTheme } from 'next-themes'
import { isAppThemeDark, normalizeAppThemeId } from '@/lib/app-theme'
import { cn } from '@/lib/utils'

interface BrandLogoProps {
  className?: string
}

export function BrandLogo({ className }: BrandLogoProps) {
  const { theme } = useTheme()
  const dark = isAppThemeDark(normalizeAppThemeId(theme))
  const src = dark ? '/gymsite-logo-white.png' : '/gymsite-logo.png'

  return (
    <img
      src={src}
      alt="GymSite Intelligence"
      draggable={false}
      className={cn('h-9 w-auto object-contain', className)}
    />
  )
}
