import * as React from 'react'
import { Link } from '@tanstack/react-router'
import { NavMain } from '@/components/nav-main'
import { NavUser } from '@/components/nav-user'
import { useMembership } from '@/hooks/useMembership'
import { getSidebarNavItems } from '@/lib/nav-items'
import {
  Sidebar,
  SidebarContent,
  SidebarFooter,
  SidebarHeader,
  SidebarMenu,
  SidebarMenuButton,
  SidebarMenuItem,
} from '@/components/ui/sidebar'

export function AppSidebar({ ...props }: React.ComponentProps<typeof Sidebar>) {
  const { isOwnerOrAdmin } = useMembership()
  const navItems = getSidebarNavItems(isOwnerOrAdmin)

  return (
    <Sidebar collapsible="offcanvas" {...props}>
      <SidebarHeader>
        <SidebarMenu>
          <SidebarMenuItem>
            <SidebarMenuButton
              asChild
              className="data-[slot=sidebar-menu-button]:p-1.5!"
            >
              <Link to="/dashboard">
                <span aria-hidden className="text-lg">
                  🏋️
                </span>
                <span className="text-base font-semibold">GymSite Intelligence</span>
              </Link>
            </SidebarMenuButton>
          </SidebarMenuItem>
        </SidebarMenu>
      </SidebarHeader>
      <SidebarContent>
        <NavMain items={navItems} />
      </SidebarContent>
      <SidebarFooter>
        <NavUser />
      </SidebarFooter>
    </Sidebar>
  )
}
