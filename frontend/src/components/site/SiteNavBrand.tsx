import { Menu } from 'lucide-react'
import {
  Sheet,
  SheetContent,
  SheetHeader,
  SheetTitle,
  SheetTrigger,
} from '@/components/ui/sheet'
import { GYMSITE_PALETTE } from '@/config/gymsite-design-system'
import { cn } from '@/lib/utils'

export type SiteNavLink = { href: string; label: string }

export const LANDING_NAV: SiteNavLink[] = [
  { href: '#fontes', label: 'Fontes' },
  { href: '#beneficios', label: 'Benefícios' },
  { href: '#metodo', label: 'Método' },
  { href: '/agentes', label: 'Especialistas' },
  { href: '/explorar', label: 'Explorar' },
  { href: '/blog', label: 'Blog' },
  { href: '#lgpd', label: 'LGPD' },
  { href: '/login', label: 'Entrar' },
]

export const AGENTES_NAV: SiteNavLink[] = [
  { href: '/#fontes', label: 'Fontes' },
  { href: '/#metodo', label: 'Método' },
  { href: '/explorar', label: 'Explorar' },
  { href: '/blog', label: 'Blog' },
  { href: '/#lgpd', label: 'LGPD' },
]

export const BLOG_NAV: SiteNavLink[] = [
  { href: '/#fontes', label: 'Fontes' },
  { href: '/agentes', label: 'Especialistas' },
  { href: '/explorar', label: 'Explorar' },
  { href: '/blog', label: 'Blog' },
  { href: '/degustacao', label: 'Degustação' },
]

export const DEGUSTACAO_NAV: SiteNavLink[] = [
  { href: '/agentes', label: 'Especialistas' },
  { href: '/explorar', label: 'Explorar' },
  { href: '/', label: 'Início' },
]

export const DEGUSTACAO_SANDBOX_NAV: SiteNavLink[] = [
  { href: '/agentes', label: 'Especialistas' },
  { href: '/explorar', label: 'Explorar' },
  { href: '/sandbox-ollama.html', label: 'Sandbox HTML' },
  { href: '/degustacao', label: 'Degustação' },
  { href: '/', label: 'Início' },
]

export const EXPLORAR_SITE_NAV: SiteNavLink[] = [
  { href: '/agentes', label: 'Especialistas' },
  { href: '/degustacao', label: 'Degustação' },
  { href: '/', label: 'Início' },
]

/** Pin + wordmark for dark site chrome. Height only on the mark — never stretch. */
export function SiteNavBrand() {
  return (
    <>
      <img
        className="mark"
        src="/gymsite-pin-white.png"
        alt=""
        draggable={false}
      />
      <span>
        GymSite <span className="hl">Intelligence</span>
      </span>
    </>
  )
}

export function SitePublicMenu({
  links,
  activeHref,
  className,
}: {
  links: SiteNavLink[]
  activeHref?: string
  className?: string
}) {
  return (
    <div className={cn('flex items-center', className)}>
      <nav className="hidden md:flex md:items-center md:gap-6" aria-label="Principal">
        {links.map((l) => (
          <a
            key={l.href + l.label}
            href={l.href}
            className={cn(
              'text-sm font-medium text-muted-foreground hover:text-foreground',
              activeHref === l.href && 'text-foreground',
            )}
          >
            {l.label}
          </a>
        ))}
      </nav>
      <Sheet>
        <SheetTrigger
          className="inline-flex size-11 items-center justify-center rounded-md border border-border md:hidden"
          aria-label="Abrir menu"
        >
          <Menu className="h-5 w-5" />
        </SheetTrigger>
        <SheetContent
          side="right"
          className="left-auto w-64 max-w-[72vw] border-0 shadow-2xl"
          style={{ backgroundColor: GYMSITE_PALETTE.card2, color: GYMSITE_PALETTE.fg }}
        >
          <SheetHeader>
            <SheetTitle>Menu</SheetTitle>
          </SheetHeader>
          <nav className="mt-4 flex flex-col gap-1" aria-label="Principal">
            {links.map((l) => (
              <a
                key={`m-${l.href}${l.label}`}
                href={l.href}
                className="flex min-h-11 items-center rounded-md px-3 text-base hover:bg-accent"
              >
                {l.label}
              </a>
            ))}
          </nav>
        </SheetContent>
      </Sheet>
    </div>
  )
}

