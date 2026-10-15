import * as React from "react"
import {
  Sidebar,
  SidebarContent,
  SidebarFooter,
  SidebarHeader,
  SidebarMenu,
  SidebarMenuButton,
  SidebarMenuItem,
  SidebarGroup,
  SidebarGroupLabel,
  SidebarGroupContent,
} from "@/components/ui/sidebar"
import {
  LayoutDashboardIcon,
  MessageSquareIcon,
  BookOpenIcon,
  FileTextIcon,
  PlugIcon,
  AwardIcon,
  NetworkIcon,
  CoffeeIcon,
  BotIcon,
  ExternalLinkIcon,
} from "lucide-react"
import { Badge } from "@/components/ui/badge"

interface AppSidebarProps extends React.ComponentProps<typeof Sidebar> {
  currentTab: string
  onSelectTab: (tab: string) => void
  backendOnline: boolean
}

export function AppSidebar({
  currentTab,
  onSelectTab,
  backendOnline,
  ...props
}: AppSidebarProps) {
  const navItems = [
    {
      id: "dashboard",
      title: "Dashboard",
      icon: <LayoutDashboardIcon className="size-4" />,
      badge: null,
    },
    {
      id: "chat",
      title: "Simulador de Chat",
      icon: <MessageSquareIcon className="size-4" />,
      badge: "En vivo",
    },
    {
      id: "graph",
      title: "Flujo del Grafo",
      icon: <NetworkIcon className="size-4" />,
      badge: "Flow",
    },
    {
      id: "kb",
      title: "Base de Conocimiento",
      icon: <BookOpenIcon className="size-4" />,
      badge: null,
    },
    {
      id: "prompts",
      title: "Prompts del Sistema",
      icon: <FileTextIcon className="size-4" />,
      badge: null,
    },
    {
      id: "connectors",
      title: "Conectores",
      icon: <PlugIcon className="size-4" />,
      badge: null,
    },
    {
      id: "evaluation",
      title: "Evaluación & Métricas",
      icon: <AwardIcon className="size-4" />,
      badge: null,
    },
  ]

  return (
    <Sidebar collapsible="offcanvas" {...props}>
      <SidebarHeader className="border-b p-4">
        <SidebarMenu>
          <SidebarMenuItem>
            <SidebarMenuButton
              size="lg"
              className="gap-3 hover:bg-transparent cursor-default"
            >
              <div className="flex size-9 items-center justify-center rounded-xl bg-primary text-primary-foreground shadow-sm">
                <CoffeeIcon className="size-5" />
              </div>
              <div className="flex flex-col gap-0.5 leading-none">
                <span className="font-bold text-sm tracking-tight">Lumbre Café</span>
                <span className="text-[11px] text-muted-foreground flex items-center gap-1">
                  <BotIcon className="size-3" /> Agente IA Multi-canal
                </span>
              </div>
            </SidebarMenuButton>
          </SidebarMenuItem>
        </SidebarMenu>
      </SidebarHeader>

      <SidebarContent className="p-3">
        <SidebarGroup>
          <SidebarGroupLabel className="text-[11px] font-semibold uppercase tracking-wider text-muted-foreground/80 px-2 mb-1">
            Plataforma del Agente
          </SidebarGroupLabel>
          <SidebarGroupContent>
            <SidebarMenu className="gap-1">
              {navItems.map((item) => {
                const isActive = currentTab === item.id
                return (
                  <SidebarMenuItem key={item.id}>
                    <SidebarMenuButton
                      isActive={isActive}
                      onClick={() => onSelectTab(item.id)}
                      className={`h-9.5 px-3 rounded-lg font-medium transition-all ${
                        isActive
                          ? "bg-primary text-primary-foreground font-semibold shadow-xs"
                          : "text-muted-foreground hover:text-foreground hover:bg-muted/60"
                      }`}
                    >
                      {item.icon}
                      <span className="text-sm">{item.title}</span>
                      {item.badge && (
                        <Badge
                          variant={isActive ? "secondary" : "outline"}
                          className="ml-auto text-[10px] py-0 px-1.5 font-normal"
                        >
                          {item.badge}
                        </Badge>
                      )}
                    </SidebarMenuButton>
                  </SidebarMenuItem>
                )
              })}
            </SidebarMenu>
          </SidebarGroupContent>
        </SidebarGroup>

        <SidebarGroup className="mt-auto">
          <SidebarGroupLabel className="text-[11px] font-semibold uppercase tracking-wider text-muted-foreground/80 px-2 mb-1">
            Recursos
          </SidebarGroupLabel>
          <SidebarGroupContent>
            <SidebarMenu className="gap-1">
              <SidebarMenuItem>
                <SidebarMenuButton
                  render={
                    <a
                      href="http://127.0.0.1:8000/docs"
                      target="_blank"
                      rel="noreferrer"
                      className="flex items-center gap-2 text-xs text-muted-foreground hover:text-foreground"
                    />
                  }
                >
                  <ExternalLinkIcon className="size-3.5" />
                  <span>Documentación OpenAPI (/docs)</span>
                </SidebarMenuButton>
              </SidebarMenuItem>
            </SidebarMenu>
          </SidebarGroupContent>
        </SidebarGroup>
      </SidebarContent>

      <SidebarFooter className="border-t p-3">
        <div className="flex items-center justify-between rounded-lg bg-muted/40 p-2.5 text-xs">
          <div className="flex items-center gap-2">
            <span
              className={`size-2 rounded-full ${
                backendOnline ? "bg-emerald-500 animate-pulse" : "bg-amber-500"
              }`}
            />
            <span className="font-mono text-[11px] text-muted-foreground">
              {backendOnline ? "FastAPI Online" : "Simulador Local"}
            </span>
          </div>
          <span className="text-[10px] text-muted-foreground">v1.0</span>
        </div>
      </SidebarFooter>
    </Sidebar>
  )
}
