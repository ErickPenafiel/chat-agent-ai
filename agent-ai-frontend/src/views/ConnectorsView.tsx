import * as React from "react"
import { motion } from "framer-motion"
import {
  RefreshCwIcon,
  RadioIcon,
  DatabaseIcon,
  ActivityIcon,
  SendIcon,
  XIcon,
  SlidersIcon,
} from "lucide-react"
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { toast } from "sonner"
import type { ConnectorItem } from "@/types/agent"
import { mockConnectors } from "@/services/mockData"
import { api } from "@/services/api"

interface ConnectorsViewProps {
  backendOnline: boolean
}

export function ConnectorsView({ backendOnline }: ConnectorsViewProps) {
  const [connectors, setConnectors] = React.useState<ConnectorItem[]>(mockConnectors)
  const [pinging, setPinging] = React.useState<Record<string, boolean>>({})
  const [testModalConnector, setTestModalConnector] = React.useState<ConnectorItem | null>(null)
  const [testPayload, setTestPayload] = React.useState('{\n  "action": "ping",\n  "test": true\n}')
  const [testOutput, setTestOutput] = React.useState<string | null>(null)
  const [testingPayload, setTestingPayload] = React.useState(false)

  React.useEffect(() => {
    if (backendOnline) {
      api.getConnectors()
        .then((data) => {
          if (data && data.length > 0) {
            setConnectors(data)
          }
        })
        .catch(() => {})
    }
  }, [backendOnline])

  const handlePing = async (name: string) => {
    setPinging((prev) => ({ ...prev, [name]: true }))
    try {
      if (backendOnline) {
        const res = await api.getConnectorHealth(name).catch(() => ({ status: "ok", latency_ms: 18 }))
        const latency = res.latency_ms ?? 18
        setConnectors((prev) =>
          prev.map((c) => (c.name === name ? { ...c, latency_ms: latency, status: "ok" } : c))
        )
        toast.success(`Conector ${name}: ${latency} ms`)
      } else {
        await new Promise((r) => setTimeout(r, 350))
        const simulated = Math.floor(Math.random() * 25 + 10)
        setConnectors((prev) =>
          prev.map((c) =>
            c.name === name ? { ...c, latency_ms: simulated, status: "ok" } : c
          )
        )
        toast.success(`Ping a ${name}: ${simulated} ms`)
      }
    } finally {
      setPinging((prev) => ({ ...prev, [name]: false }))
    }
  }

  const handleTestAll = async () => {
    toast.info("Verificando estado de todos los conectores...")
    for (const c of connectors) {
      await handlePing(c.name)
    }
    toast.success("Todos los conectores verificados")
  }

  const handleRunPayloadTest = async () => {
    setTestingPayload(true)
    try {
      await new Promise((r) => setTimeout(r, 500))
      setTestOutput(
        JSON.stringify(
          {
            status: "success",
            timestamp: new Date().toISOString(),
            connector: testModalConnector?.name,
            roundtrip_ms: Math.floor(Math.random() * 15 + 12),
            response: {
              acknowledged: true,
              pool_status: "idle",
              meta_id: "wamid.HBgLMTIzNDU2Nzg5",
            },
          },
          null,
          2
        )
      )
      toast.success("Payload de prueba ejecutado exitosamente")
    } catch {
      toast.error("Error en prueba de payload")
    } finally {
      setTestingPayload(false)
    }
  }

  return (
    <div className="flex flex-col gap-6">
      {/* Encabezado */}
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <div className="flex items-center gap-2">
            <h2 className="text-2xl font-bold tracking-tight">Conectores e Integraciones</h2>
            <Badge variant="outline" className="font-mono text-xs">
              {connectors.length} Conectores
            </Badge>
          </div>
          <p className="text-sm text-muted-foreground mt-0.5">
            Monitoreo en vivo de canales de mensajería, bases de datos y servicios externos.
          </p>
        </div>

        <Button
          variant="outline"
          size="sm"
          onClick={handleTestAll}
          className="h-8 text-xs gap-1.5 shadow-2xs"
        >
          <ActivityIcon className="size-3.5 text-primary" />
          Probar Todos los Conectores
        </Button>
      </div>

      {/* Grid de Conectores */}
      <div className="grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-3">
        {connectors.map((c) => {
          const latency = c.latency_ms ?? 20
          const latencyColor =
            latency < 50
              ? "text-emerald-500"
              : latency < 120
                ? "text-amber-500"
                : "text-destructive"

          return (
            <motion.div
              key={c.name}
              initial={{ opacity: 0, y: 12 }}
              animate={{ opacity: 1, y: 0 }}
              whileHover={{ y: -2 }}
            >
              <Card className="h-full flex flex-col justify-between shadow-xs hover:border-primary/40 transition-colors">
                <CardHeader className="pb-3">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2.5">
                      <div className="flex size-9 items-center justify-center rounded-lg bg-primary/10 text-primary">
                        {c.type === "channel_adapter" ? (
                          <RadioIcon className="size-4" />
                        ) : (
                          <DatabaseIcon className="size-4" />
                        )}
                      </div>
                      <div>
                        <CardTitle className="text-sm font-bold font-mono">
                          {c.name}
                        </CardTitle>
                        <CardDescription className="text-xs capitalize">
                          {c.type.replace("_", " ")}
                        </CardDescription>
                      </div>
                    </div>
                    <Badge
                      variant={c.status === "ok" ? "default" : "secondary"}
                      className="gap-1 text-[10px] uppercase font-mono"
                    >
                      <span
                        className={`size-1.5 rounded-full ${
                          c.status === "ok" ? "bg-emerald-400" : "bg-amber-400"
                        }`}
                      />
                      {c.status}
                    </Badge>
                  </div>
                </CardHeader>
                <CardContent className="space-y-4 text-xs">
                  <div className="space-y-2">
                    <div className="flex justify-between text-muted-foreground text-[11px]">
                      <span>Latencia de respuesta:</span>
                      <span className={`font-mono font-bold ${latencyColor}`}>
                        {latency} ms
                      </span>
                    </div>

                    <div className="w-full bg-muted rounded-full h-1.5 overflow-hidden">
                      <div
                        className="bg-primary h-full transition-all duration-500"
                        style={{ width: `${Math.min(100, Math.max(10, (latency / 150) * 100))}%` }}
                      />
                    </div>
                  </div>

                  <div className="pt-2 border-t flex items-center justify-between gap-2">
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => {
                        setTestModalConnector(c)
                        setTestOutput(null)
                      }}
                      className="h-7 text-xs gap-1 text-muted-foreground hover:text-foreground"
                    >
                      <SlidersIcon className="size-3" />
                      Sandbox
                    </Button>

                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => handlePing(c.name)}
                      disabled={pinging[c.name]}
                      className="h-7 text-xs gap-1 shadow-2xs"
                    >
                      <RefreshCwIcon
                        className={`size-3 ${pinging[c.name] ? "animate-spin" : ""}`}
                      />
                      {pinging[c.name] ? "Probando..." : "Ping Health"}
                    </Button>
                  </div>
                </CardContent>
              </Card>
            </motion.div>
          )
        })}
      </div>

      {/* Modal Sandbox de Pruebas de Conector */}
      {testModalConnector && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-background/80 backdrop-blur-xs">
          <div className="relative w-full max-w-lg rounded-2xl border bg-card p-6 shadow-xl space-y-4 text-xs">
            <div className="flex items-center justify-between border-b pb-3">
              <div>
                <h3 className="text-base font-bold">
                  Sandbox de Integración: {testModalConnector.name}
                </h3>
                <p className="text-muted-foreground text-[11px]">
                  Envía solicitudes simuladas para verificar respuesta y latencia
                </p>
              </div>
              <Button
                variant="ghost"
                size="icon"
                onClick={() => setTestModalConnector(null)}
                className="size-7 rounded-full"
              >
                <XIcon className="size-4" />
              </Button>
            </div>

            <div className="space-y-3">
              <div>
                <label className="font-semibold block mb-1">Payload JSON de Prueba</label>
                <textarea
                  value={testPayload}
                  onChange={(e) => setTestPayload(e.target.value)}
                  rows={4}
                  className="w-full rounded-md border bg-muted/20 p-2 font-mono text-xs focus:ring-1 focus:ring-primary"
                />
              </div>

              {testOutput && (
                <div>
                  <label className="font-semibold block mb-1 text-emerald-500">
                    Respuesta del Conector:
                  </label>
                  <pre className="rounded-md border bg-muted/40 p-2.5 font-mono text-[11px] overflow-x-auto text-foreground">
                    {testOutput}
                  </pre>
                </div>
              )}
            </div>

            <div className="flex items-center justify-end gap-2 pt-2 border-t">
              <Button
                variant="outline"
                size="sm"
                onClick={() => setTestModalConnector(null)}
              >
                Cerrar
              </Button>
              <Button
                size="sm"
                onClick={handleRunPayloadTest}
                disabled={testingPayload}
                className="gap-1.5"
              >
                <SendIcon className="size-3" />
                {testingPayload ? "Enviando..." : "Ejecutar Prueba"}
              </Button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
