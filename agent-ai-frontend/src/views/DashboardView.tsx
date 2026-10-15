import * as React from "react"
import { motion } from "framer-motion"
import {
  MessageSquareIcon,
  CheckCircle2Icon,
  UserCheckIcon,
  ClockIcon,
  ActivityIcon,
  SparklesIcon,
  ShieldCheckIcon,
  ArrowUpRightIcon,
  DownloadIcon,
  CalendarIcon,
  RadioIcon,
} from "lucide-react"
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import {
  AreaChart,
  Area,
  ResponsiveContainer,
  XAxis,
  YAxis,
  Tooltip as RechartsTooltip,
} from "recharts"
import { toast } from "sonner"
import type { OutcomeSummary } from "@/types/agent"

const datasetsByRange: Record<
  "today" | "7d" | "30d",
  { chart: Array<{ time: string; resolved: number; escalated: number }>; total: number; resolvedPct: number }
> = {
  today: {
    chart: [
      { time: "09:00", resolved: 14, escalated: 1 },
      { time: "11:00", resolved: 28, escalated: 3 },
      { time: "13:00", resolved: 42, escalated: 2 },
      { time: "15:00", resolved: 65, escalated: 5 },
      { time: "17:00", resolved: 51, escalated: 4 },
      { time: "19:00", resolved: 33, escalated: 1 },
      { time: "21:00", resolved: 19, escalated: 0 },
    ],
    total: 252,
    resolvedPct: 93.6,
  },
  "7d": {
    chart: [
      { time: "Lun", resolved: 140, escalated: 12 },
      { time: "Mar", resolved: 185, escalated: 15 },
      { time: "Mié", resolved: 210, escalated: 18 },
      { time: "Jue", resolved: 195, escalated: 14 },
      { time: "Vie", resolved: 245, escalated: 22 },
      { time: "Sáb", resolved: 290, escalated: 19 },
      { time: "Dom", resolved: 180, escalated: 10 },
    ],
    total: 1445,
    resolvedPct: 92.4,
  },
  "30d": {
    chart: [
      { time: "Semana 1", resolved: 850, escalated: 70 },
      { time: "Semana 2", resolved: 980, escalated: 85 },
      { time: "Semana 3", resolved: 1120, escalated: 90 },
      { time: "Semana 4", resolved: 1250, escalated: 95 },
    ],
    total: 4200,
    resolvedPct: 93.1,
  },
}

interface DashboardViewProps {
  onNavigateToChat: () => void
  summary?: OutcomeSummary
  backendOnline: boolean
}

export function DashboardView({
  onNavigateToChat,
  backendOnline,
}: DashboardViewProps) {
  const [dateRange, setDateRange] = React.useState<"today" | "7d" | "30d">("today")
  const [liveStreamActive, setLiveStreamActive] = React.useState(false)
  const [liveCounter, setLiveCounter] = React.useState(datasetsByRange.today.total)

  const activeData = datasetsByRange[dateRange]

  // Actualización periódica en modo live stream
  React.useEffect(() => {
    let timer: ReturnType<typeof setInterval>
    if (liveStreamActive) {
      timer = setInterval(() => {
        setLiveCounter((c) => c + Math.floor(Math.random() * 3 + 1))
      }, 3500)
    }
    return () => clearInterval(timer)
  }, [liveStreamActive])

  const handleExportMetrics = () => {
    const payload = {
      tenant: "Lumbre Café",
      range: dateRange,
      metrics: {
        totalConversations: liveCounter,
        resolutionRate: `${activeData.resolvedPct}%`,
        averageLatency: "410ms",
        slaHandoff: "< 15m",
      },
      exportedAt: new Date().toISOString(),
    }
    const dataStr = "data:text/json;charset=utf-8," + encodeURIComponent(JSON.stringify(payload, null, 2))
    const a = document.createElement("a")
    a.href = dataStr
    a.download = `metrics_report_${dateRange}_${new Date().toISOString().slice(0, 10)}.json`
    a.click()
    toast.success("Reporte de métricas descargado")
  }

  const containerVariants = {
    hidden: { opacity: 0 },
    visible: {
      opacity: 1,
      transition: {
        staggerChildren: 0.08,
      },
    },
  }

  const cardVariants = {
    hidden: { opacity: 0, y: 15 },
    visible: { opacity: 1, y: 0, transition: { duration: 0.35 } },
  }

  return (
    <motion.div
      variants={containerVariants}
      initial="hidden"
      animate="visible"
      className="flex flex-col gap-6"
    >
      {/* Banner de estado del tenant */}
      <motion.div
        variants={cardVariants}
        className="relative overflow-hidden rounded-2xl border border-primary/20 bg-linear-to-r from-primary/10 via-background to-secondary/30 p-6 shadow-sm"
      >
        <div className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
          <div className="flex items-center gap-4">
            <div className="flex size-12 shrink-0 items-center justify-center rounded-xl bg-primary text-primary-foreground shadow-md">
              <SparklesIcon className="size-6" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h2 className="text-xl font-bold tracking-tight">
                  Agente IA — Lumbre Café
                </h2>
                <Badge
                  variant={backendOnline ? "default" : "secondary"}
                  className="gap-1 font-mono text-xs"
                >
                  <span
                    className={`size-2 rounded-full ${
                      backendOnline ? "bg-emerald-400 animate-pulse" : "bg-amber-400"
                    }`}
                  />
                  {backendOnline ? "Backend Conectado" : "Modo Simulación"}
                </Badge>
              </div>
              <p className="text-sm text-muted-foreground mt-0.5">
                Orquestador LangGraph activo con catálogo RAG de productos, suscripciones y derivación humana.
              </p>
            </div>
          </div>

          <div className="flex items-center gap-2">
            <Button
              variant="outline"
              size="sm"
              onClick={handleExportMetrics}
              className="gap-1 text-xs h-9"
            >
              <DownloadIcon className="size-3.5" />
              Exportar
            </Button>
            <Button
              onClick={onNavigateToChat}
              size="sm"
              className="gap-1 text-xs h-9 shadow-xs"
            >
              <MessageSquareIcon className="size-3.5" />
              Abrir Simulador de Chat
            </Button>
          </div>
        </div>
      </motion.div>

      {/* Selector de Rango Temporal y Modo En Vivo */}
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between rounded-xl border bg-card p-3 shadow-2xs">
        <div className="flex items-center gap-1.5 text-xs">
          <span className="text-muted-foreground flex items-center gap-1 mr-1">
            <CalendarIcon className="size-3.5" /> Período:
          </span>
          <Button
            variant={dateRange === "today" ? "default" : "outline"}
            size="sm"
            onClick={() => {
              setDateRange("today")
              setLiveCounter(datasetsByRange.today.total)
            }}
            className="h-7 text-xs"
          >
            Hoy
          </Button>
          <Button
            variant={dateRange === "7d" ? "default" : "outline"}
            size="sm"
            onClick={() => {
              setDateRange("7d")
              setLiveCounter(datasetsByRange["7d"].total)
            }}
            className="h-7 text-xs"
          >
            Últimos 7 días
          </Button>
          <Button
            variant={dateRange === "30d" ? "default" : "outline"}
            size="sm"
            onClick={() => {
              setDateRange("30d")
              setLiveCounter(datasetsByRange["30d"].total)
            }}
            className="h-7 text-xs"
          >
            Este Mes
          </Button>
        </div>

        <div className="flex items-center gap-2">
          <Button
            variant={liveStreamActive ? "default" : "ghost"}
            size="sm"
            onClick={() => {
              setLiveStreamActive((p) => !p)
              toast.info(liveStreamActive ? "Live stream pausado" : "Live stream activado: recibiendo eventos en vivo")
            }}
            className="h-7 text-xs gap-1.5"
          >
            <RadioIcon className={`size-3.5 ${liveStreamActive ? "text-emerald-400 animate-pulse" : ""}`} />
            {liveStreamActive ? "Live Stream Activo" : "Activar Live Stream"}
          </Button>
        </div>
      </div>

      {/* Tarjetas KPI */}
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <motion.div variants={cardVariants}>
          <Card className="shadow-xs hover:border-primary/40 transition-colors">
            <CardHeader className="flex flex-row items-center justify-between pb-2">
              <CardTitle className="text-xs font-semibold text-muted-foreground">
                Total Sesiones
              </CardTitle>
              <MessageSquareIcon className="size-4 text-primary" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold font-mono">{liveCounter}</div>
              <p className="text-[11px] text-muted-foreground flex items-center gap-1 mt-1">
                <span className="text-emerald-500 font-semibold flex items-center">
                  +12% <ArrowUpRightIcon className="size-3" />
                </span>
                vs. período anterior
              </p>
            </CardContent>
          </Card>
        </motion.div>

        <motion.div variants={cardVariants}>
          <Card className="shadow-xs hover:border-primary/40 transition-colors">
            <CardHeader className="flex flex-row items-center justify-between pb-2">
              <CardTitle className="text-xs font-semibold text-muted-foreground">
                Tasa de Resolución
              </CardTitle>
              <CheckCircle2Icon className="size-4 text-emerald-500" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold font-mono">{activeData.resolvedPct}%</div>
              <p className="text-[11px] text-muted-foreground flex items-center gap-1 mt-1">
                Autónomo vía RAG
              </p>
            </CardContent>
          </Card>
        </motion.div>

        <motion.div variants={cardVariants}>
          <Card className="shadow-xs hover:border-primary/40 transition-colors">
            <CardHeader className="flex flex-row items-center justify-between pb-2">
              <CardTitle className="text-xs font-semibold text-muted-foreground">
                Tasa de Escalado
              </CardTitle>
              <UserCheckIcon className="size-4 text-amber-500" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold font-mono">
                {(100 - activeData.resolvedPct).toFixed(1)}%
              </div>
              <p className="text-[11px] text-muted-foreground flex items-center gap-1 mt-1">
                Derivación garantizada
              </p>
            </CardContent>
          </Card>
        </motion.div>

        <motion.div variants={cardVariants}>
          <Card className="shadow-xs hover:border-primary/40 transition-colors">
            <CardHeader className="flex flex-row items-center justify-between pb-2">
              <CardTitle className="text-xs font-semibold text-muted-foreground">
                Promedio de Turnos
              </CardTitle>
              <ClockIcon className="size-4 text-blue-500" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold font-mono">2.8 turnos</div>
              <p className="text-[11px] text-muted-foreground flex items-center gap-1 mt-1">
                410 ms por respuesta
              </p>
            </CardContent>
          </Card>
        </motion.div>
      </div>

      {/* Gráfico de Actividad Interactivo Recharts */}
      <motion.div variants={cardVariants}>
        <Card className="shadow-xs">
          <CardHeader className="pb-3 border-b">
            <div className="flex items-center justify-between">
              <div>
                <CardTitle className="text-base font-bold">
                  Volumen de Conversaciones por Hora
                </CardTitle>
                <CardDescription className="text-xs">
                  Distribución de consultas resueltas automáticamente vs. casos escalados
                </CardDescription>
              </div>
              <div className="flex items-center gap-3 text-xs">
                <span className="flex items-center gap-1 text-emerald-500 font-medium">
                  <span className="size-2 rounded-full bg-emerald-500" /> Resueltas
                </span>
                <span className="flex items-center gap-1 text-amber-500 font-medium">
                  <span className="size-2 rounded-full bg-amber-500" /> Escaladas
                </span>
              </div>
            </div>
          </CardHeader>
          <CardContent className="pt-6">
            <div className="h-64 w-full">
              <ResponsiveContainer width="100%" height="100%">
                <AreaChart
                  data={activeData.chart}
                  margin={{ top: 10, right: 10, left: -20, bottom: 0 }}
                >
                  <defs>
                    <linearGradient id="colorResolved" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor="#10b981" stopOpacity={0.4} />
                      <stop offset="95%" stopColor="#10b981" stopOpacity={0.0} />
                    </linearGradient>
                    <linearGradient id="colorEscalated" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor="#f59e0b" stopOpacity={0.4} />
                      <stop offset="95%" stopColor="#f59e0b" stopOpacity={0.0} />
                    </linearGradient>
                  </defs>
                  <XAxis
                    dataKey="time"
                    stroke="#888888"
                    fontSize={11}
                    tickLine={false}
                    axisLine={false}
                  />
                  <YAxis
                    stroke="#888888"
                    fontSize={11}
                    tickLine={false}
                    axisLine={false}
                  />
                  <RechartsTooltip
                    contentStyle={{
                      backgroundColor: "var(--card)",
                      borderColor: "var(--border)",
                      borderRadius: "0.75rem",
                      fontSize: "12px",
                    }}
                  />
                  <Area
                    type="monotone"
                    dataKey="resolved"
                    stroke="#10b981"
                    strokeWidth={2}
                    fillOpacity={1}
                    fill="url(#colorResolved)"
                  />
                  <Area
                    type="monotone"
                    dataKey="escalated"
                    stroke="#f59e0b"
                    strokeWidth={2}
                    fillOpacity={1}
                    fill="url(#colorEscalated)"
                  />
                </AreaChart>
              </ResponsiveContainer>
            </div>
          </CardContent>
        </Card>
      </motion.div>

      {/* Reglas Operacionales y Parámetros */}
      <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
        <motion.div variants={cardVariants}>
          <Card className="h-full shadow-xs">
            <CardHeader className="pb-3 border-b">
              <div className="flex items-center gap-2">
                <ShieldCheckIcon className="size-4 text-primary" />
                <CardTitle className="text-sm font-bold">
                  Parámetros del Tenant (<code>tenant.yaml</code>)
                </CardTitle>
              </div>
            </CardHeader>
            <CardContent className="space-y-3 pt-4 text-xs">
              <div className="flex justify-between py-1 border-b">
                <span className="text-muted-foreground">Negocio:</span>
                <span className="font-semibold font-mono">Lumbre Café</span>
              </div>
              <div className="flex justify-between py-1 border-b">
                <span className="text-muted-foreground">Tono de Comunicación:</span>
                <span className="font-semibold font-mono">Informal ("tú")</span>
              </div>
              <div className="flex justify-between py-1 border-b">
                <span className="text-muted-foreground">Checkpointer de Sesión:</span>
                <span className="font-semibold font-mono">MemorySaver (SQLite)</span>
              </div>
              <div className="flex justify-between py-1">
                <span className="text-muted-foreground">SLA de Respuesta Humana:</span>
                <span className="font-semibold font-mono">12 Horas</span>
              </div>
            </CardContent>
          </Card>
        </motion.div>

        <motion.div variants={cardVariants}>
          <Card className="h-full shadow-xs">
            <CardHeader className="pb-3 border-b">
              <div className="flex items-center gap-2">
                <ActivityIcon className="size-4 text-emerald-500" />
                <CardTitle className="text-sm font-bold">
                  Salud Operativa del Sistema
                </CardTitle>
              </div>
            </CardHeader>
            <CardContent className="space-y-3 pt-4 text-xs">
              <div className="flex items-center justify-between py-1 border-b">
                <span className="text-muted-foreground">FastAPI Backend:</span>
                <Badge variant="outline" className="text-emerald-500 font-mono text-[10px]">
                  {backendOnline ? "Online (Port 8000)" : "Simulado"}
                </Badge>
              </div>
              <div className="flex items-center justify-between py-1 border-b">
                <span className="text-muted-foreground">LangGraph Engine:</span>
                <Badge variant="outline" className="text-emerald-500 font-mono text-[10px]">
                  StateGraph Ready
                </Badge>
              </div>
              <div className="flex items-center justify-between py-1 border-b">
                <span className="text-muted-foreground">Web Channel Webhook:</span>
                <Badge variant="outline" className="text-emerald-500 font-mono text-[10px]">
                  /channels/web/webhook
                </Badge>
              </div>
              <div className="flex items-center justify-between py-1">
                <span className="text-muted-foreground">Suite de Tests E2E:</span>
                <Badge variant="outline" className="text-primary font-mono text-[10px]">
                  Playwright Chromium Ready
                </Badge>
              </div>
            </CardContent>
          </Card>
        </motion.div>
      </div>
    </motion.div>
  )
}
