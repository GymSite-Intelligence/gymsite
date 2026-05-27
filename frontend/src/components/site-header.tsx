import { Badge } from '@/components/ui/badge'
import { Separator } from '@/components/ui/separator'
import { SidebarTrigger } from '@/components/ui/sidebar'
import { useApiHealth } from '@/hooks/useApiHealth'
import { API_BASE } from '@/lib/supabase'
import { Loader2Icon, WifiIcon, WifiOffIcon } from 'lucide-react'

export function SiteHeader({ title = 'Dashboard' }: { title?: string }) {
  const { data: health, isLoading, isError } = useApiHealth()

  return (
    <header className="flex h-(--header-height) shrink-0 items-center gap-2 border-b transition-[width,height] ease-linear group-has-data-[collapsible=icon]/sidebar-wrapper:h-(--header-height)">
      <div className="flex w-full items-center gap-2 px-4 lg:gap-3 lg:px-6">
        <SidebarTrigger className="-ml-1" />
        <Separator
          orientation="vertical"
          className="mx-2 data-[orientation=vertical]:h-4"
        />
        <h1 className="min-w-0 flex-1 truncate text-base font-medium">{title}</h1>
        <ApiStatusBadge
          loading={isLoading}
          ok={!isError && health?.status === 'ok'}
          base={API_BASE}
        />
      </div>
    </header>
  )
}

function ApiStatusBadge({
  loading,
  ok,
  base,
}: {
  loading: boolean
  ok: boolean
  base: string
}) {
  if (loading) {
    return (
      <Badge variant="outline" className="gap-1 font-mono text-[10px]">
        <Loader2Icon className="size-3 animate-spin" />
        API…
      </Badge>
    )
  }

  if (ok) {
    return (
      <Badge variant="success" className="gap-1 font-mono text-[10px]" title={base}>
        <WifiIcon className="size-3" />
        API online
      </Badge>
    )
  }

  return (
    <Badge variant="destructive" className="gap-1 font-mono text-[10px]" title={base}>
      <WifiOffIcon className="size-3" />
      API offline
    </Badge>
  )
}
