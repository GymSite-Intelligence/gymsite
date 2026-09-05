import type { LucideIcon } from 'lucide-react'
import {
  BarChart3Icon,
  BotIcon,
  ClipboardListIcon,
  Building2Icon,
  CompassIcon,
  CpuIcon,
  FileTextIcon,
  GitCompareIcon,
  HexagonIcon,
  InboxIcon,
  LayoutDashboardIcon,
  TargetIcon,
} from 'lucide-react'

export type SidebarNavItem = {
  title: string
  to: string
  icon?: LucideIcon
}

export const appNavItems: SidebarNavItem[] = [
  {
    title: 'Dashboard',
    to: '/dashboard',
    icon: LayoutDashboardIcon,
  },
  {
    title: 'Relatórios',
    to: '/relatorios',
    icon: FileTextIcon,
  },
  {
    title: 'CRM',
    to: '/crm',
    icon: ClipboardListIcon,
  },
  {
    title: 'Explorar',
    to: '/explorar',
    icon: CompassIcon,
  },
  {
    title: 'Comparar',
    to: '/comparar',
    icon: GitCompareIcon,
  },
  {
    title: 'Prospecção',
    to: '/prospeccao',
    icon: TargetIcon,
  },
  {
    title: 'Captação de Leads',
    to: '/prospect',
    icon: InboxIcon,
  },
  {
    title: 'Consultor',
    to: '/consultor',
    icon: BotIcon,
  },
  {
    title: 'Obras CNO',
    to: '/cno-obras',
    icon: Building2Icon,
  },
  {
    title: 'Hex CARTO',
    to: '/carto-hex',
    icon: HexagonIcon,
  },
]

export const custosNavItem: SidebarNavItem = {
  title: 'Custos',
  to: '/custos',
  icon: BarChart3Icon,
}

export const llmAdminNavItem: SidebarNavItem = {
  title: 'Provedor de IA',
  to: '/admin/llm',
  icon: CpuIcon,
}

export function getSidebarNavItems(isOwnerOrAdmin: boolean): SidebarNavItem[] {
  if (!isOwnerOrAdmin) return appNavItems
  return [...appNavItems, custosNavItem]
}
