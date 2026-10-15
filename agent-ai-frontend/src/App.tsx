import * as React from "react"
import { motion, AnimatePresence } from "framer-motion"
import { SidebarProvider, SidebarInset } from "@/components/ui/sidebar"
import { AppSidebar } from "@/components/app-sidebar"
import { SiteHeader } from "@/components/site-header"
import { Toaster } from "@/components/ui/sonner"
import { Skeleton } from "@/components/ui/skeleton"
import { api } from "@/services/api"

// Lazy-loaded views for optimal code-splitting and load performance
const DashboardView = React.lazy(() =>
  import("@/views/DashboardView").then((m) => ({ default: m.DashboardView }))
)
const ChatPlaygroundView = React.lazy(() =>
  import("@/views/ChatPlaygroundView").then((m) => ({ default: m.ChatPlaygroundView }))
)
const KnowledgeBaseView = React.lazy(() =>
  import("@/views/KnowledgeBaseView").then((m) => ({ default: m.KnowledgeBaseView }))
)
const PromptsView = React.lazy(() =>
  import("@/views/PromptsView").then((m) => ({ default: m.PromptsView }))
)
const ConnectorsView = React.lazy(() =>
  import("@/views/ConnectorsView").then((m) => ({ default: m.ConnectorsView }))
)
const EvaluationView = React.lazy(() =>
  import("@/views/EvaluationView").then((m) => ({ default: m.EvaluationView }))
)
const GraphWorkflowView = React.lazy(() =>
  import("@/views/GraphWorkflowView").then((m) => ({ default: m.GraphWorkflowView }))
)

const tabTitles: Record<string, string> = {
  dashboard: "Dashboard de Rendimiento",
  chat: "Simulador de Chat en Vivo",
  graph: "Flujo del Grafo LangGraph",
  kb: "Base de Conocimiento",
  prompts: "Prompts del Sistema",
  connectors: "Conectores e Integraciones",
  evaluation: "Evaluación y Propuestas",
}

function ViewFallback() {
  return (
    <div className="space-y-6 animate-pulse">
      <div className="flex justify-between items-center">
        <Skeleton className="h-8 w-64 rounded-xl" />
        <Skeleton className="h-8 w-32 rounded-xl" />
      </div>
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <Skeleton className="h-32 rounded-2xl" />
        <Skeleton className="h-32 rounded-2xl" />
        <Skeleton className="h-32 rounded-2xl" />
      </div>
      <Skeleton className="h-96 rounded-2xl" />
    </div>
  )
}

export function App() {
  const [currentTab, setCurrentTab] = React.useState("dashboard")
  const [backendOnline, setBackendOnline] = React.useState(false)

  const checkBackendHealth = React.useCallback(() => {
    api.getHealth()
      .then((res) => {
        setBackendOnline(res.status === "ok")
      })
      .catch(() => {
        setBackendOnline(false)
      })
  }, [])

  React.useEffect(() => {
    checkBackendHealth()
    const interval = setInterval(checkBackendHealth, 15000)
    return () => clearInterval(interval)
  }, [checkBackendHealth])

  return (
    <SidebarProvider>
      <div className="flex min-h-screen w-full bg-background text-foreground antialiased">
        <AppSidebar
          currentTab={currentTab}
          onSelectTab={setCurrentTab}
          backendOnline={backendOnline}
        />
        <SidebarInset className="flex flex-col flex-1 min-w-0">
          <SiteHeader
            title={tabTitles[currentTab] || "Panel de Control"}
            backendOnline={backendOnline}
            onCheckHealth={checkBackendHealth}
          />
          <main className="flex-1 p-4 lg:p-6 overflow-x-hidden">
            <React.Suspense fallback={<ViewFallback />}>
              <AnimatePresence mode="wait">
                <motion.div
                  key={currentTab}
                  initial={{ opacity: 0, y: 10 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0, y: -10 }}
                  transition={{ duration: 0.22, ease: "easeInOut" }}
                  className="w-full max-w-7xl mx-auto"
                >
                  {currentTab === "dashboard" && (
                    <DashboardView
                      onNavigateToChat={() => setCurrentTab("chat")}
                      backendOnline={backendOnline}
                    />
                  )}
                  {currentTab === "chat" && (
                    <ChatPlaygroundView backendOnline={backendOnline} />
                  )}
                  {currentTab === "graph" && (
                    <GraphWorkflowView />
                  )}
                  {currentTab === "kb" && (
                    <KnowledgeBaseView backendOnline={backendOnline} />
                  )}
                  {currentTab === "prompts" && (
                    <PromptsView backendOnline={backendOnline} />
                  )}
                  {currentTab === "connectors" && (
                    <ConnectorsView backendOnline={backendOnline} />
                  )}
                  {currentTab === "evaluation" && (
                    <EvaluationView backendOnline={backendOnline} />
                  )}
                </motion.div>
              </AnimatePresence>
            </React.Suspense>
          </main>
        </SidebarInset>
        <Toaster richColors position="top-right" />
      </div>
    </SidebarProvider>
  )
}

export default App
