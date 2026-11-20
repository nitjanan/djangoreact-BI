import { ChevronsUpDown, LogOut, Truck, Wrench } from 'lucide-react'
import { Link, Outlet, useLocation, useNavigate } from 'react-router'

import { useLogout } from '@/api/hooks'
import { Avatar, AvatarFallback } from '@/components/ui/avatar'
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu'
import {
  Sidebar,
  SidebarContent,
  SidebarFooter,
  SidebarGroup,
  SidebarGroupLabel,
  SidebarHeader,
  SidebarInset,
  SidebarMenu,
  SidebarMenuButton,
  SidebarMenuItem,
  SidebarProvider,
  SidebarTrigger,
} from '@/components/ui/sidebar'
import { Separator } from '@/components/ui/separator'

import { CompanyTabs } from './CompanyTabs'
import { useCurrentUser } from './RequireAuth'

// เมนูตามแท็บที่ admin เปิดให้ผู้ใช้เห็น (BaseVisible) — เพิ่มหน้าใหม่ที่นี่
const MENU = [{ tab: 'Maintenance', label: 'Maintenance', to: '/', icon: Wrench }]

export function AppLayout() {
  const me = useCurrentUser()
  const location = useLocation()
  const navigate = useNavigate()
  const logout = useLogout()

  const menu = MENU.filter((m) => me.visible_tabs.some((t) => t.includes(m.tab)))
  const displayName =
    [me.user.first_name, me.user.last_name].filter(Boolean).join(' ') || me.user.username

  return (
    <SidebarProvider>
      <Sidebar collapsible="icon">
        <SidebarHeader>
          <SidebarMenu>
            <SidebarMenuItem>
              <SidebarMenuButton size="lg" asChild>
                <Link to="/">
                  <span className="flex aspect-square size-8 items-center justify-center rounded-md bg-signal text-signal-foreground">
                    <Truck className="size-4" />
                  </span>
                  <span className="grid leading-tight">
                    <span className="font-heading text-base font-semibold text-white">
                      STG Dashboard
                    </span>
                    <span className="text-xs text-plate-muted">งานซ่อมบำรุงรถและเครื่องจักร</span>
                  </span>
                </Link>
              </SidebarMenuButton>
            </SidebarMenuItem>
          </SidebarMenu>
        </SidebarHeader>

        <SidebarContent>
          <SidebarGroup>
            <SidebarGroupLabel className="text-plate-muted">เมนู</SidebarGroupLabel>
            <SidebarMenu>
              {menu.map((item) => (
                <SidebarMenuItem key={item.to}>
                  <SidebarMenuButton
                    asChild
                    isActive={location.pathname === item.to}
                    tooltip={item.label}
                    className="relative data-[active=true]:bg-sidebar-accent data-[active=true]:font-medium data-[active=true]:text-white data-[active=true]:before:absolute data-[active=true]:before:inset-y-1.5 data-[active=true]:before:left-0 data-[active=true]:before:w-1 data-[active=true]:before:rounded-full data-[active=true]:before:bg-signal"
                  >
                    <Link to={{ pathname: item.to, search: location.search }}>
                      <item.icon />
                      <span>{item.label}</span>
                    </Link>
                  </SidebarMenuButton>
                </SidebarMenuItem>
              ))}
            </SidebarMenu>
          </SidebarGroup>
        </SidebarContent>

        <SidebarFooter>
          <SidebarMenu>
            <SidebarMenuItem>
              <DropdownMenu>
                <DropdownMenuTrigger asChild>
                  <SidebarMenuButton size="lg">
                    <Avatar className="size-8 rounded-md">
                      <AvatarFallback className="rounded-md bg-sidebar-accent font-heading text-white">
                        {displayName.slice(0, 1).toUpperCase()}
                      </AvatarFallback>
                    </Avatar>
                    <span className="grid flex-1 text-left text-sm leading-tight">
                      <span className="truncate font-medium text-white">{displayName}</span>
                      <span className="truncate text-xs text-plate-muted">
                        {me.user.email || me.user.username}
                      </span>
                    </span>
                    <ChevronsUpDown className="ml-auto size-4" />
                  </SidebarMenuButton>
                </DropdownMenuTrigger>
                <DropdownMenuContent side="top" align="start" className="w-56">
                  <DropdownMenuLabel>{me.user.username}</DropdownMenuLabel>
                  <DropdownMenuSeparator />
                  <DropdownMenuItem
                    onSelect={() =>
                      logout.mutate(undefined, {
                        onSettled: () => navigate('/login', { replace: true }),
                      })
                    }
                  >
                    <LogOut />
                    ออกจากระบบ
                  </DropdownMenuItem>
                </DropdownMenuContent>
              </DropdownMenu>
            </SidebarMenuItem>
          </SidebarMenu>
        </SidebarFooter>
      </Sidebar>

      <SidebarInset className="min-w-0">
        <header className="sticky top-0 z-20 flex h-14 shrink-0 items-center gap-3 border-b bg-card/95 px-4 backdrop-blur md:px-6">
          <SidebarTrigger className="-ml-1.5" aria-label="เปิด/ปิดเมนู" />
          <Separator orientation="vertical" className="data-[orientation=vertical]:h-5" />
          <CompanyTabs />
        </header>
        <Outlet />
      </SidebarInset>
    </SidebarProvider>
  )
}
