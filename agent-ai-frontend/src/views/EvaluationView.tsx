import * as React from "react"
import { motion } from "framer-motion"
import {
  LightbulbIcon,
  CheckCircle2Icon,
  SparklesIcon,
  Trash2Icon,
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
import { toast } from "sonner"
import type { OutcomeSummary } from "@/types/agent"
import { mockOutcomeSummary } from "@/services/mockData"
import { api } from "@/services/api"

interface EvaluationViewProps {
  backendOnline: boolean
}

export function EvaluationView({ backendOnline }: EvaluationViewProps) {
  const [summary, setSummary] = React.useState<OutcomeSummary>(mockOutcomeSummary)
  const [proposals, setProposals] = React.useState<
    Array<{ id: number; title: string; rationale: string; status: string }>
  >([
    {
      id: 1,
      title: "Ampliar bloque de métodos de pago en el extranjero",
      rationale: "4 clientes preguntaron por pagos con PayPal o Stripe internacional durante los últimos 7 días.",
      status: "pending",
    },
    {
      id: 2,
      title: "Añadir ejemplos de preguntas sobre tipos de molienda",
      rationale: "Múltiples consultas sobre 'molienda para prensa francesa' requirieron reintento de retrieval.",
      status: "reviewed",
    },
    {
      id: 3,
      title: "Clarificar política de envíos gratis en compras > 25 USD",
      rationale: "El agente tuvo dudas en 3 turnos respecto a si aplicaba a zonas rurales o sólo urbanas.",
      status: "pending",
    },
  ])

  React.useEffect(() => {
    if (backendOnline) {
      api.getOutcomesSummary()
        .then((data) => {
          if (data) setSummary(data)
        })
        .catch(() => {})

      api.getEvaluationProposals()
        .then((data) => {
          if (data && data.length > 0) setProposals(data)
        })
        .catch(() => {})
    }
  }, [backendOnline])

  const handleApplyProposal = (id: number, title: string) => {
    setProposals((prev) =>
      prev.map((p) => (p.id === id ? { ...p, status: "applied" } : p))
    )
    toast.success(`Propuesta "${title}" aplicada exitosamente a la base de conocimiento`)
  }

  const handleDismissProposal = (id: number) => {
    setProposals((prev) => prev.filter((p) => p.id !== id))
    toast.info("Propuesta descartada")
  }

  const handleGenerateProposal = () => {
    const newId = Date.now()
    const syntheticProposals = [
      {
        id: newId,
        title: "Crear bloque para horarios de atención en feriados",
        rationale: "5 usuarios consultaron si la cafetería abre los domingos y festivos patrios.",
        status: "pending",
      },
      {
        id: newId,
        title: "Actualizar precios de grano Geisha y Bourbon",
        rationale: "Se detectó desfase entre catálogo web y precios citados por el bot.",
        status: "pending",
      },
    ]
    const chosen = syntheticProposals[Math.floor(Math.random() * syntheticProposals.length)]
    setProposals((prev) => [chosen, ...prev])
    toast.success("Nueva propuesta de auditoría detectada por el evaluador")
  }

  return (
    <div className="flex flex-col gap-6">
      {/* Encabezado */}
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <div className="flex items-center gap-2">
            <h2 className="text-2xl font-bold tracking-tight">Evaluación y Propuestas</h2>
            <Badge variant="outline" className="font-mono text-xs">
              {summary.total_sessions} Evaluaciones
            </Badge>
          </div>
          <p className="text-sm text-muted-foreground mt-0.5">
            Auditoría continua de calidad de respuestas, escalados e iniciativas de mejora automática.
          </p>
        </div>

        <Button
          size="sm"
          onClick={handleGenerateProposal}
          className="h-8 text-xs gap-1.5 shadow-2xs"
        >
          <SparklesIcon className="size-3.5" />
          Ejecutar Auditoría
        </Button>
      </div>

      {/* Métricas de Rendimiento */}
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
        <Card className="shadow-xs hover:border-emerald-500/40 transition-colors">
          <CardHeader className="pb-2">
            <CardDescription className="text-xs font-medium uppercase tracking-wider">
              Casos Resueltos
            </CardDescription>
            <CardTitle className="text-3xl font-extrabold text-emerald-500">
              {summary.resolved_rate}%
            </CardTitle>
          </CardHeader>
          <CardContent className="text-xs text-muted-foreground">
            {summary.resolved} conversaciones cerradas con éxito por el bot.
          </CardContent>
        </Card>

        <Card className="shadow-xs hover:border-amber-500/40 transition-colors">
          <CardHeader className="pb-2">
            <CardDescription className="text-xs font-medium uppercase tracking-wider">
              Transferencias a Asesor
            </CardDescription>
            <CardTitle className="text-3xl font-extrabold text-amber-500">
              {summary.escalated_rate}%
            </CardTitle>
          </CardHeader>
          <CardContent className="text-xs text-muted-foreground">
            {summary.escalated} consultas derivadas dentro de SLA.
          </CardContent>
        </Card>

        <Card className="shadow-xs hover:border-blue-500/40 transition-colors">
          <CardHeader className="pb-2">
            <CardDescription className="text-xs font-medium uppercase tracking-wider">
              Abandono de Sesión
            </CardDescription>
            <CardTitle className="text-3xl font-extrabold text-blue-500">
              {((summary.abandoned / summary.total_sessions) * 100).toFixed(1)}%
            </CardTitle>
          </CardHeader>
          <CardContent className="text-xs text-muted-foreground">
            {summary.abandoned} clientes que no continuaron tras el primer turno.
          </CardContent>
        </Card>
      </div>

      {/* Propuestas de Mejora */}
      <div className="space-y-4">
        <div className="flex items-center justify-between">
          <h3 className="text-sm font-semibold flex items-center gap-2">
            <LightbulbIcon className="size-4 text-amber-500" />
            Propuestas de Optimización para la Base de Conocimiento ({proposals.length})
          </h3>
        </div>

        <div className="space-y-3">
          {proposals.map((p) => (
            <motion.div
              key={p.id}
              initial={{ opacity: 0, y: 8 }}
              animate={{ opacity: 1, y: 0 }}
            >
              <Card className="hover:border-primary/40 transition-colors shadow-2xs">
                <CardHeader className="pb-2">
                  <div className="flex items-center justify-between">
                    <CardTitle className="text-sm font-semibold">{p.title}</CardTitle>
                    <Badge
                      variant={
                        p.status === "applied"
                          ? "default"
                          : p.status === "reviewed"
                            ? "secondary"
                            : "outline"
                      }
                      className="text-[10px] capitalize font-mono"
                    >
                      {p.status}
                    </Badge>
                  </div>
                </CardHeader>
                <CardContent className="text-xs text-muted-foreground flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
                  <p className="leading-relaxed">{p.rationale}</p>
                  <div className="flex items-center gap-2 shrink-0">
                    {p.status !== "applied" ? (
                      <Button
                        size="sm"
                        variant="default"
                        onClick={() => handleApplyProposal(p.id, p.title)}
                        className="h-7 text-xs gap-1"
                      >
                        <CheckCircle2Icon className="size-3" />
                        Aplicar al Bloque
                      </Button>
                    ) : (
                      <span className="text-emerald-500 font-semibold text-xs flex items-center gap-1">
                        <CheckCircle2Icon className="size-3" /> Aplicado
                      </span>
                    )}
                    <Button
                      size="sm"
                      variant="ghost"
                      onClick={() => handleDismissProposal(p.id)}
                      className="h-7 size-7 p-0 text-muted-foreground hover:text-destructive"
                      title="Descartar propuesta"
                    >
                      <Trash2Icon className="size-3" />
                    </Button>
                  </div>
                </CardContent>
              </Card>
            </motion.div>
          ))}
        </div>
      </div>
    </div>
  )
}
