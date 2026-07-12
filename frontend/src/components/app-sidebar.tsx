import * as React from 'react'
import { Link } from '@tanstack/react-router'
import { NavMain } from '@/components/nav-main'
import { NavUser } from '@/components/nav-user'
import { BrandLogo } from '@/components/layout/BrandLogo'
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
              className="h-auto data-[slot=sidebar-menu-button]:p-1.5!"
            >
              <Link to="/dashboard" aria-label="GymSite Intelligence — início">
                <BrandLogo className="h-8 w-auto py-0.5" />
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
