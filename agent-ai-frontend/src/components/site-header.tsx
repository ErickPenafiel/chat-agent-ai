import { Separator } from "@/components/ui/separator"
import { SidebarTrigger } from "@/components/ui/sidebar"
import { Button } from "@/components/ui/button"
import { SunIcon, MoonIcon, RefreshCwIcon } from "lucide-react"

interface SiteHeaderProps {
  title: string
  backendOnline: boolean
  onCheckHealth: () => void
}

export function SiteHeader({ title, backendOnline, onCheckHealth }: SiteHeaderProps) {
  const toggleTheme = () => {
    document.documentElement.classList.toggle("dark")
  }

  return (
    <header className="flex h-14 shrink-0 items-center gap-2 border-b bg-card/60 backdrop-blur-xs px-4 lg:px-6 sticky top-0 z-30 transition-[width,height] ease-linear">
      <div className="flex w-full items-center justify-between">
        <div className="flex items-center gap-2">
          <SidebarTrigger className="-ml-1" />
          <Separator orientation="vertical" className="mx-2 h-4" />
          <h1 className="text-base font-semibold tracking-tight">{title}</h1>
        </div>

        <div className="flex items-center gap-2">
          <Button
            variant="ghost"
            size="sm"
            onClick={onCheckHealth}
            className="h-8 gap-1.5 text-xs text-muted-foreground hover:text-foreground"
            title="Verificar conexión con backend"
          >
            <RefreshCwIcon className="size-3.5" />
            <span className="hidden sm:inline">
              {backendOnline ? "Conectado" : "Reconectar"}
            </span>
          </Button>

          <Button
            variant="ghost"
            size="icon"
            onClick={toggleTheme}
            className="size-8 text-muted-foreground hover:text-foreground"
            title="Alternar tema claro/oscuro"
          >
            <SunIcon className="size-4 rotate-0 scale-100 transition-all dark:-rotate-90 dark:scale-0" />
            <MoonIcon className="absolute size-4 rotate-90 scale-0 transition-all dark:rotate-0 dark:scale-100" />
            <span className="sr-only">Toggle theme</span>
          </Button>
        </div>
      </div>
    </header>
  )
}
