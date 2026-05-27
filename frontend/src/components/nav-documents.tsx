import { Link } from '@tanstack/react-router'
import {
  SidebarGroup,
  SidebarGroupLabel,
  SidebarMenu,
  SidebarMenuButton,
  SidebarMenuItem,
} from '@/components/ui/sidebar'
import {
  BarChart3Icon,
  GitCompareIcon,
  MapIcon,
  FileTextIcon,
} from 'lucide-react'

const items = [
  { name: 'Relatórios', to: '/relatorios', icon: <FileTextIcon /> },
  { name: 'Mapa', to: '/mapa', icon: <MapIcon /> },
  { name: 'Comparar', to: '/comparar', icon: <GitCompareIcon /> },
  { name: 'Custos', to: '/custos', icon: <BarChart3Icon /> },
]

export function NavDocuments({ showCustos }: { showCustos: boolean }) {
  const visible = showCustos ? items : items.filter((i) => i.to !== '/custos')

  return (
    <SidebarGroup className="group-data-[collapsible=icon]:hidden">
      <SidebarGroupLabel>Operação</SidebarGroupLabel>
      <SidebarMenu>
        {visible.map((item) => (
          <SidebarMenuItem key={item.name}>
            <SidebarMenuButton asChild>
              <Link to={item.to}>
                {item.icon}
                <span>{item.name}</span>
              </Link>
            </SidebarMenuButton>
          </SidebarMenuItem>
        ))}
      </SidebarMenu>
    </SidebarGroup>
  )
}
