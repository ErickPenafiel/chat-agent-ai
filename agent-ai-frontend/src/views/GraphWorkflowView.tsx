import * as React from "react"
import {
  ReactFlow,
  MiniMap,
  Controls,
  Background,
  Panel,
  useNodesState,
  useEdgesState,
  type Node,
  type Edge,
  BackgroundVariant,
  MarkerType,
  Handle,
  Position,
  type NodeProps,
  useReactFlow,
  ReactFlowProvider,
} from "@xyflow/react"
import "@xyflow/react/dist/style.css"
import {
  SparklesIcon,
  LayersIcon,
  PlayIcon,
  PauseIcon,
  StepForwardIcon,
  CheckCircle2Icon,
  InfoIcon,
  CpuIcon,
  BookOpenIcon,
  PhoneForwardedIcon,
  PlugIcon,
  SendIcon,
  UserCheckIcon,
  RadioIcon,
  RotateCcwIcon,
  ClockIcon,
  GaugeIcon,
  FileCodeIcon,
  Maximize2Icon,
  ArrowRightLeftIcon,
  DownloadIcon,
  SearchIcon,
  EditIcon,
  XIcon,
} from "lucide-react"
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { toast } from "sonner"

export interface AgentNodeData extends Record<string, unknown> {
  label: string
  subtitle: string
  module: string
  description: string
  category: "channel" | "classifier" | "retriever" | "llm" | "handoff" | "integration" | "identity"
  accentColor: string
  iconName: string
  inputs: string[]
  outputs: string[]
  metricLabel?: string
  metricValue?: string
  promptSnippet?: string
  status?: "ready" | "active" | "idle"
  orientation?: "vertical" | "horizontal"
  isStepActive?: boolean
}

// Componente de Nodo Personalizado con diseño moderno tipo tarjeta
function CustomAgentNode({ data, selected }: NodeProps<Node<AgentNodeData>>) {
  const isHorizontal = data.orientation === "horizontal"

  const getIcon = (iconName: string) => {
    switch (iconName) {
      case "radio":
        return <RadioIcon className="size-4" />
      case "identity":
        return <UserCheckIcon className="size-4" />
      case "cpu":
        return <CpuIcon className="size-4" />
      case "book":
        return <BookOpenIcon className="size-4" />
      case "plug":
        return <PlugIcon className="size-4" />
      case "phone":
        return <PhoneForwardedIcon className="size-4" />
      case "send":
        return <SendIcon className="size-4" />
      default:
        return <CpuIcon className="size-4" />
    }
  }

  const slug = data.label.split(" ")[0].toLowerCase()

  return (
    <div
      data-testid={`rf__node-${slug}`}
      className={`relative rounded-2xl border transition-all duration-300 w-[275px] select-none ${
        data.isStepActive
          ? "ring-4 ring-primary shadow-2xl scale-[1.05] border-primary animate-pulse"
          : selected
            ? "ring-2 ring-primary shadow-2xl scale-[1.02] border-primary"
            : "border-border/90 shadow-md hover:shadow-xl hover:border-primary/60"
      } bg-card/95 backdrop-blur-md overflow-hidden`}
    >
      {/* Barra de Acento Superior con Gradiente */}
      <div
        className="h-1.5 w-full"
        style={{
          background: `linear-gradient(90deg, ${data.accentColor}, ${data.accentColor}88)`,
        }}
      />

      {/* Puerto de Entrada */}
      <Handle
        type="target"
        position={isHorizontal ? Position.Left : Position.Top}
        className="size-3.5 rounded-full border-2 border-background shadow-xs !bg-primary transition-transform hover:scale-125"
      />

      <div className="p-3.5 space-y-2.5">
        {/* Cabecera del Nodo */}
        <div className="flex items-center justify-between gap-2">
          <div className="flex items-center gap-2 min-w-0">
            <div
              className="flex size-8 shrink-0 items-center justify-center rounded-xl shadow-xs"
              style={{
                backgroundColor: `${data.accentColor}25`,
                color: data.accentColor,
              }}
            >
              {getIcon(data.iconName)}
            </div>
            <div className="min-w-0">
              <h4 className="font-bold text-xs leading-none truncate">{data.label}</h4>
              <p className="text-[10px] text-muted-foreground mt-0.5 truncate">
                {data.subtitle}
              </p>
            </div>
          </div>

          <div className="flex items-center gap-1 shrink-0">
            <span
              className={`size-2 rounded-full ${data.isStepActive ? "animate-ping" : "animate-pulse"}`}
              style={{ backgroundColor: data.accentColor }}
            />
            <span className="text-[10px] font-mono text-muted-foreground uppercase">
              {data.isStepActive ? "Active" : data.status || "Ready"}
            </span>
          </div>
        </div>

        {/* Descripción Breve */}
        <p className="text-[11px] text-muted-foreground line-clamp-2 leading-relaxed">
          {data.description}
        </p>

        {/* Metadatos y Métricas del Nodo */}
        <div className="flex items-center justify-between pt-2 border-t text-[10px]">
          <span className="font-mono text-muted-foreground truncate max-w-[140px]">
            {data.module.replace("src/", "")}
          </span>
          {data.metricValue && (
            <Badge
              variant="secondary"
              className="text-[9px] px-1.5 py-0 font-mono font-medium gap-1"
            >
              <ClockIcon className="size-2.5" />
              {data.metricValue}
            </Badge>
          )}
        </div>
      </div>

      {/* Puerto de Salida */}
      <Handle
        type="source"
        position={isHorizontal ? Position.Right : Position.Bottom}
        className="size-3.5 rounded-full border-2 border-background shadow-xs !bg-primary transition-transform hover:scale-125"
      />
    </div>
  )
}

const nodeTypes = {
  agentNode: CustomAgentNode,
}

// Coordenadas Verticales Espaciosas (Zero Overlap)
const verticalPositions: Record<string, { x: number; y: number }> = {
  START: { x: 450, y: 30 },
  identity: { x: 450, y: 230 },
  intent: { x: 450, y: 430 },
  retrieval: { x: 50, y: 670 },
  capture: { x: 450, y: 670 },
  handoff: { x: 850, y: 670 },
  connector: { x: -300, y: 670 },
  response: { x: 250, y: 910 },
  END: { x: 550, y: 1240 },
  media: { x: 50, y: 230 },
  verify: { x: 250, y: 1040 },
}

// Coordenadas Horizontales Espaciosas (Pipeline Left-to-Right)
const horizontalPositions: Record<string, { x: number; y: number }> = {
  START: { x: 50, y: 320 },
  identity: { x: 400, y: 320 },
  intent: { x: 750, y: 320 },
  handoff: { x: 1150, y: 80 },
  retrieval: { x: 1150, y: 320 },
  capture: { x: 1150, y: 560 },
  connector: { x: 1150, y: 780 },
  response: { x: 1550, y: 420 },
  END: { x: 2300, y: 250 },
  media: { x: 400, y: 80 },
  verify: { x: 1900, y: 420 },
}

function buildNodes(
  orientation: "vertical" | "horizontal" = "vertical",
  activeStepNodeId: string | null = null
): Node<AgentNodeData>[] {
  const pos = orientation === "vertical" ? verticalPositions : horizontalPositions

  return [
    {
      id: "START",
      type: "agentNode",
      position: pos.START,
      data: {
        label: "START (Webhook)",
        subtitle: "Canal Entrante",
        module: "src/channels/web.py",
        description: "Recibe el webhook del canal activo (WhatsApp Cloud API o canal web mock) y lo normaliza a un evento interno.",
        category: "channel",
        accentColor: "#3b82f6",
        iconName: "radio",
        inputs: ["HTTP POST /webhook"],
        outputs: ["InboundEvent(text, user_id)"],
        status: "ready",
        orientation,
        isStepActive: activeStepNodeId === "START",
      },
    },
    {
      id: "media",
      type: "agentNode",
      position: pos.media,
      data: {
        label: "media (opcional)",
        subtitle: "Adjuntos",
        module: "src/nodes/media.py",
        description: "Solo corre con media_enabled: true en tenant.yaml. Hoy es un placeholder: aún no transcribe ni describe adjuntos.",
        category: "channel",
        accentColor: "#94a3b8",
        iconName: "radio",
        inputs: ["state.media"],
        outputs: ["state.transcript"],
        status: "idle",
        orientation,
        isStepActive: activeStepNodeId === "media",
      },
    },
    {
      id: "identity",
      type: "agentNode",
      position: pos.identity,
      data: {
        label: "identity",
        subtitle: "Resolución de Entidad",
        module: "src/nodes/identity.py",
        description: "Resuelve a qué entidad del negocio (pedido, cuenta, turno…) corresponde el mensaje, con un resolver inyectable. Sin resolver no asocia ninguna.",
        category: "identity",
        accentColor: "#64748b",
        iconName: "identity",
        inputs: ["user_id", "identity_entity_type"],
        outputs: ["state.entity"],
        status: "ready",
        orientation,
        isStepActive: activeStepNodeId === "identity",
      },
    },
    {
      id: "intent",
      type: "agentNode",
      position: pos.intent,
      data: {
        label: "intent (Clasificador)",
        subtitle: "Clasificación con LLM",
        module: "src/nodes/intent.py",
        description: "Clasifica la consulta entre las intenciones habilitadas en tenant.yaml (ej. support, sales, info, chat, escalate) con el prompt versionado intent_classifier. Sin LLM responde chat.",
        category: "classifier",
        accentColor: "#8b5cf6",
        iconName: "cpu",
        inputs: ["last_user_message", "intents (tenant.yaml)"],
        outputs: ["state.intent", "state.detected_issue"],
        promptSnippet: "Prompt versionado: intent_classifier (editable en la sección Prompts).",
        status: "ready",
        orientation,
        isStepActive: activeStepNodeId === "intent",
      },
    },
    {
      id: "retrieval",
      type: "agentNode",
      position: pos.retrieval,
      data: {
        label: "retrieval (KB Search)",
        subtitle: "Búsqueda Semántica",
        module: "src/nodes/retrieval.py",
        description: "Recupera hasta 3 bloques publicados de la KB por coincidencia léxica de palabras; keywords y preguntas de ejemplo pesan más que el cuerpo.",
        category: "retriever",
        accentColor: "#10b981",
        iconName: "book",
        inputs: ["last_user_message", "state.intent"],
        outputs: ["state.retrieved", "state.response_parts"],
        metricLabel: "Top K",
        metricValue: "k=3",
        status: "ready",
        orientation,
        isStepActive: activeStepNodeId === "retrieval",
      },
    },
    {
      id: "capture",
      type: "agentNode",
      position: pos.capture,
      data: {
        label: "capture (Datos)",
        subtitle: "Captura Estructurada",
        module: "src/nodes/capture.py",
        description: "Pide uno a uno los campos definidos para la intención en tenant.yaml (capture_fields) y los guarda. capture_before_answer decide si va antes o después de responder.",
        category: "integration",
        accentColor: "#f59e0b",
        iconName: "plug",
        inputs: ["capture_fields (tenant.yaml)", "last_user_message"],
        outputs: ["state.capture", "state.awaiting_capture_field"],
        status: "ready",
        orientation,
        isStepActive: activeStepNodeId === "capture",
      },
    },
    {
      id: "handoff",
      type: "agentNode",
      position: pos.handoff,
      data: {
        label: "handoff (Escalado)",
        subtitle: "Derivación a Humano",
        module: "src/nodes/handoff.py",
        description: "Marca la conversación para atención humana y agrega un aviso para el cliente. La creación de ticket y la alerta interna aún no están implementadas.",
        category: "handoff",
        accentColor: "#ef4444",
        iconName: "phone",
        inputs: ["state.intent == 'escalate'"],
        outputs: ["state.handoff = True", "state.response_parts"],
        status: "ready",
        orientation,
        isStepActive: activeStepNodeId === "handoff",
      },
    },
    {
      id: "connector",
      type: "agentNode",
      position: pos.connector,
      data: {
        label: "connector (API/DB)",
        subtitle: "Llamada Externa",
        module: "src/nodes/connector.py",
        description: "Busca en el registro de conectores activos el que coincide con la intención y el issue detectado y consulta su backend. El template trae solo uno de ejemplo con datos simulados.",
        category: "integration",
        accentColor: "#06b6d4",
        iconName: "plug",
        inputs: ["state.intent", "state.detected_issue", "state.entity"],
        outputs: ["state.connector_results"],
        status: "ready",
        orientation,
        isStepActive: activeStepNodeId === "connector",
      },
    },
    {
      id: "response",
      type: "agentNode",
      position: pos.response,
      data: {
        label: "response (Generador)",
        subtitle: "Generación de Respuesta",
        module: "src/nodes/response.py",
        description: "Redacta la respuesta final con el tono del negocio a partir de la KB, los datos de conectores y la captura. Si el LLM falla, responde con el texto en crudo.",
        category: "llm",
        accentColor: "#ec4899",
        iconName: "cpu",
        inputs: ["state.retrieved", "state.connector_results", "state.capture_prompt"],
        outputs: ["state.reply", "state.reply_mode"],
        promptSnippet: "Prompts versionados: tone + agent_<intención> (editables en la sección Prompts).",
        status: "ready",
        orientation,
        isStepActive: activeStepNodeId === "response",
      },
    },
    {
      id: "verify",
      type: "agentNode",
      position: pos.verify,
      data: {
        label: "verify (opcional)",
        subtitle: "Guardrail Anti-alucinación",
        module: "src/nodes/verify.py",
        description: "Solo con verify_responses: true. Un LLM compara el borrador con la KB y los datos de conectores; si afirma algo sin respaldo, lo reemplaza por una respuesta segura. No verifica handoff ni charla sin hechos.",
        category: "llm",
        accentColor: "#14b8a6",
        iconName: "cpu",
        inputs: ["state.reply", "state.retrieved", "state.connector_results"],
        outputs: ["state.verification", "state.unsupported_claims", "state.reply"],
        promptSnippet: "Prompt versionado: verifier (protegido: el corrector nocturno no lo modifica).",
        status: "idle",
        orientation,
        isStepActive: activeStepNodeId === "verify",
      },
    },
    {
      id: "END",
      type: "agentNode",
      position: pos.END,
      data: {
        label: "END (Respuesta Enviada)",
        subtitle: "Canal Saliente (Outbox)",
        module: "src/core/dispatcher.py",
        description: "El dispatcher envía la respuesta por el mismo canal por el que llegó el mensaje y registra el resultado del turno.",
        category: "channel",
        accentColor: "#10b981",
        iconName: "send",
        inputs: ["state.reply"],
        outputs: ["channel.send_text()"],
        status: "ready",
        orientation,
        isStepActive: activeStepNodeId === "END",
      },
    },
  ]
}

const initialEdges: Edge[] = [
  {
    id: "e-start-identity",
    source: "START",
    target: "identity",
    type: "smoothstep",
    label: "media_enabled: false",
    animated: true,
    markerEnd: { type: MarkerType.ArrowClosed },
    style: { stroke: "#3b82f6", strokeWidth: 2.5 },
  },
  {
    id: "e-start-media",
    source: "START",
    target: "media",
    type: "smoothstep",
    label: "media_enabled: true",
    markerEnd: { type: MarkerType.ArrowClosed },
    style: { stroke: "#94a3b8", strokeWidth: 2.5, strokeDasharray: "4", opacity: 0.6 },
  },
  {
    id: "e-media-identity",
    source: "media",
    target: "identity",
    type: "smoothstep",
    markerEnd: { type: MarkerType.ArrowClosed },
    style: { stroke: "#94a3b8", strokeWidth: 2.5, strokeDasharray: "4", opacity: 0.6 },
  },
  {
    id: "e-identity-intent",
    source: "identity",
    target: "intent",
    type: "smoothstep",
    animated: true,
    markerEnd: { type: MarkerType.ArrowClosed },
    style: { stroke: "#8b5cf6", strokeWidth: 2.5 },
  },
  {
    id: "e-intent-retrieval",
    source: "intent",
    target: "retrieval",
    type: "smoothstep",
    label: "info / support / sales",
    animated: true,
    markerEnd: { type: MarkerType.ArrowClosed },
    style: { stroke: "#10b981", strokeWidth: 2.5 },
  },
  {
    id: "e-intent-connector",
    source: "intent",
    target: "connector",
    type: "smoothstep",
    label: "hay conector para el issue",
    markerEnd: { type: MarkerType.ArrowClosed },
    style: { stroke: "#06b6d4", strokeWidth: 2.5 },
  },
  {
    id: "e-intent-capture",
    source: "intent",
    target: "capture",
    type: "smoothstep",
    label: "captura antes / intención custom",
    markerEnd: { type: MarkerType.ArrowClosed },
    style: { stroke: "#f59e0b", strokeWidth: 2.5, strokeDasharray: "4", opacity: 0.6 },
  },
  {
    id: "e-intent-response",
    source: "intent",
    target: "response",
    type: "smoothstep",
    label: "chat",
    markerEnd: { type: MarkerType.ArrowClosed },
    style: { stroke: "#64748b", strokeWidth: 2.5, strokeDasharray: "4", opacity: 0.6 },
  },
  {
    id: "e-intent-handoff",
    source: "intent",
    target: "handoff",
    type: "smoothstep",
    label: "escalate",
    markerEnd: { type: MarkerType.ArrowClosed },
    style: { stroke: "#ef4444", strokeWidth: 3 },
  },
  {
    id: "e-connector-retrieval",
    source: "connector",
    target: "retrieval",
    type: "smoothstep",
    markerEnd: { type: MarkerType.ArrowClosed },
    style: { stroke: "#06b6d4", strokeWidth: 2.5, strokeDasharray: "4", opacity: 0.6 },
  },
  {
    id: "e-connector-capture",
    source: "connector",
    target: "capture",
    type: "smoothstep",
    markerEnd: { type: MarkerType.ArrowClosed },
    style: { stroke: "#f59e0b", strokeWidth: 2.5, strokeDasharray: "4", opacity: 0.6 },
  },
  {
    id: "e-connector-response",
    source: "connector",
    target: "response",
    type: "smoothstep",
    markerEnd: { type: MarkerType.ArrowClosed },
    style: { stroke: "#06b6d4", strokeWidth: 2.5 },
  },
  {
    id: "e-retrieval-capture",
    source: "retrieval",
    target: "capture",
    type: "smoothstep",
    markerEnd: { type: MarkerType.ArrowClosed },
    style: { stroke: "#f59e0b", strokeWidth: 2.5, strokeDasharray: "4", opacity: 0.6 },
  },
  {
    id: "e-retrieval-response",
    source: "retrieval",
    target: "response",
    type: "smoothstep",
    animated: true,
    markerEnd: { type: MarkerType.ArrowClosed },
    style: { stroke: "#10b981", strokeWidth: 2.5 },
  },
  {
    id: "e-capture-connector",
    source: "capture",
    target: "connector",
    type: "smoothstep",
    markerEnd: { type: MarkerType.ArrowClosed },
    style: { stroke: "#06b6d4", strokeWidth: 2.5, strokeDasharray: "4", opacity: 0.6 },
  },
  {
    id: "e-capture-retrieval",
    source: "capture",
    target: "retrieval",
    type: "smoothstep",
    markerEnd: { type: MarkerType.ArrowClosed },
    style: { stroke: "#10b981", strokeWidth: 2.5, strokeDasharray: "4", opacity: 0.6 },
  },
  {
    id: "e-capture-response",
    source: "capture",
    target: "response",
    type: "smoothstep",
    markerEnd: { type: MarkerType.ArrowClosed },
    style: { stroke: "#f59e0b", strokeWidth: 2.5 },
  },
  {
    id: "e-handoff-response",
    source: "handoff",
    target: "response",
    type: "smoothstep",
    markerEnd: { type: MarkerType.ArrowClosed },
    style: { stroke: "#ef4444", strokeWidth: 2.5 },
  },
  {
    id: "e-response-verify",
    source: "response",
    target: "verify",
    type: "smoothstep",
    label: "verify_responses: true",
    markerEnd: { type: MarkerType.ArrowClosed },
    style: { stroke: "#14b8a6", strokeWidth: 2.5, strokeDasharray: "4", opacity: 0.6 },
  },
  {
    id: "e-verify-end",
    source: "verify",
    target: "END",
    type: "smoothstep",
    markerEnd: { type: MarkerType.ArrowClosed },
    style: { stroke: "#14b8a6", strokeWidth: 2.5, strokeDasharray: "4", opacity: 0.6 },
  },
  {
    id: "e-response-end",
    source: "response",
    target: "END",
    type: "smoothstep",
    label: "verify_responses: false",
    animated: true,
    markerEnd: { type: MarkerType.ArrowClosed },
    style: { stroke: "#10b981", strokeWidth: 3 },
  },
]

const simulationFlows = {
  standard: ["START", "identity", "intent", "retrieval", "response", "END"],
  escalate: ["START", "identity", "intent", "handoff", "response", "END"],
  sales: ["START", "identity", "intent", "retrieval", "capture", "response", "END"],
}

function FlowCanvas() {
  const { fitView } = useReactFlow()
  const [orientation, setOrientation] = React.useState<"vertical" | "horizontal">("vertical")
  const [nodes, setNodes, onNodesChange] = useNodesState(buildNodes("vertical"))
  const [edges, setEdges, onEdgesChange] = useEdgesState(initialEdges)
  const [selectedNodeData, setSelectedNodeData] = React.useState<AgentNodeData | null>(
    buildNodes("vertical").find((n) => n.id === "intent")!.data
  )
  const [activeSimulation, setActiveSimulation] = React.useState<string | null>(null)

  // Reproductor paso a paso
  const [stepIndex, setStepIndex] = React.useState<number | null>(null)
  const [isPlayingAuto, setIsPlayingAuto] = React.useState(false)
  const [searchQuery, setSearchQuery] = React.useState("")
  const [isConfigModalOpen, setIsConfigModalOpen] = React.useState(false)

  const onNodeClick = (_: React.MouseEvent, node: Node) => {
    setSelectedNodeData(node.data as AgentNodeData)
  }

  const toggleOrientation = () => {
    const next = orientation === "vertical" ? "horizontal" : "vertical"
    setOrientation(next)
    setNodes(buildNodes(next))
    setTimeout(() => {
      fitView({ padding: 0.2, duration: 400 })
    }, 50)
  }

  const highlightFlowEdges = (type: "standard" | "escalate" | "sales") => {
    if (type === "standard") {
      setEdges((eds) =>
        eds.map((e) => {
          const isStandard =
            e.id === "e-start-identity" ||
            e.id === "e-identity-intent" ||
            e.id === "e-intent-retrieval" ||
            e.id === "e-retrieval-response" ||
            e.id === "e-response-end"
          return {
            ...e,
            animated: isStandard,
            style: isStandard
              ? { stroke: "#10b981", strokeWidth: 3.5 }
              : { stroke: "#94a3b8", opacity: 0.25 },
          }
        })
      )
    } else if (type === "escalate") {
      setEdges((eds) =>
        eds.map((e) => {
          const isEscalate =
            e.id === "e-start-identity" ||
            e.id === "e-identity-intent" ||
            e.id === "e-intent-handoff" ||
            e.id === "e-handoff-response" ||
            e.id === "e-response-end"
          return {
            ...e,
            animated: isEscalate,
            style: isEscalate
              ? { stroke: "#ef4444", strokeWidth: 3.5 }
              : { stroke: "#94a3b8", opacity: 0.25 },
          }
        })
      )
    } else {
      setEdges((eds) =>
        eds.map((e) => {
          const isSales =
            e.id === "e-start-identity" ||
            e.id === "e-identity-intent" ||
            e.id === "e-intent-retrieval" ||
            e.id === "e-retrieval-capture" ||
            e.id === "e-capture-response" ||
            e.id === "e-response-end"
          return {
            ...e,
            animated: isSales,
            style: isSales
              ? { stroke: "#f59e0b", strokeWidth: 3.5 }
              : { stroke: "#94a3b8", opacity: 0.25 },
          }
        })
      )
    }
  }

  const simulatePath = (type: "standard" | "escalate" | "sales") => {
    setActiveSimulation(type)
    setIsPlayingAuto(false)
    setStepIndex(null)
    highlightFlowEdges(type)
    toast.info(`Ruta activa: ${type === "standard" ? "Consulta KB" : type === "escalate" ? "Escalado Humano" : "Ventas"}`)
  }

  const resetEdges = () => {
    setActiveSimulation(null)
    setStepIndex(null)
    setIsPlayingAuto(false)
    setEdges(initialEdges)
    setNodes(buildNodes(orientation))
    fitView({ padding: 0.2, duration: 400 })
    toast.info("Grafo restablecido al estado inicial")
  }

  // Reproducción Paso a Paso
  const activeFlow = simulationFlows[(activeSimulation as "standard" | "escalate" | "sales") || "standard"]

  const handleStepForward = () => {
    const nextIdx = stepIndex === null ? 0 : (stepIndex + 1) % activeFlow.length
    setStepIndex(nextIdx)
    const nodeId = activeFlow[nextIdx]
    setNodes(buildNodes(orientation, nodeId))
    const targetNode = nodes.find((n) => n.id === nodeId)
    if (targetNode) {
      setSelectedNodeData(targetNode.data)
    }
    highlightFlowEdges((activeSimulation as "standard" | "escalate" | "sales") || "standard")
  }

  // Autoplay loop
  React.useEffect(() => {
    let timer: ReturnType<typeof setInterval>
    if (isPlayingAuto) {
      timer = setInterval(() => {
        setStepIndex((prev) => {
          const next = prev === null ? 0 : (prev + 1) % activeFlow.length
          const nodeId = activeFlow[next]
          setNodes(buildNodes(orientation, nodeId))
          const target = nodes.find((n) => n.id === nodeId)
          if (target) setSelectedNodeData(target.data)
          return next
        })
      }, 1200)
    }
    return () => clearInterval(timer)
  }, [isPlayingAuto, activeFlow, orientation, nodes, setNodes])

  // Buscar y centrar nodo
  const handleSearchNode = (e: React.FormEvent) => {
    e.preventDefault()
    if (!searchQuery.trim()) return
    const match = nodes.find((n) =>
      n.id.toLowerCase().includes(searchQuery.toLowerCase()) ||
      n.data.label.toLowerCase().includes(searchQuery.toLowerCase())
    )
    if (match) {
      setSelectedNodeData(match.data)
      fitView({ nodes: [{ id: match.id }], duration: 600, padding: 0.5 })
      toast.success(`Nodo encontrado: ${match.data.label}`)
    } else {
      toast.error("Nodo no encontrado en el grafo")
    }
  }

  // Exportar Grafo a JSON
  const handleExportGraph = () => {
    const graphData = {
      nodes: nodes.map((n) => ({ id: n.id, data: n.data, position: n.position })),
      edges: edges.map((e) => ({ id: e.id, source: e.source, target: e.target, label: e.label })),
      exportedAt: new Date().toISOString(),
    }
    const dataStr = "data:text/json;charset=utf-8," + encodeURIComponent(JSON.stringify(graphData, null, 2))
    const a = document.createElement("a")
    a.href = dataStr
    a.download = `langgraph_topology_${new Date().toISOString().slice(0, 10)}.json`
    a.click()
    toast.success("Topología de LangGraph exportada como JSON")
  }

  return (
    <div className="flex flex-col gap-6">
      {/* Encabezado y Métricas */}
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <div className="flex items-center gap-2">
            <h2 className="text-2xl font-bold tracking-tight">
              Flujo del Grafo (LangGraph Workflow)
            </h2>
            <Badge variant="outline" className="font-mono text-xs gap-1">
              <SparklesIcon className="size-3 text-primary" /> React Flow
            </Badge>
          </div>
          <p className="text-sm text-muted-foreground mt-0.5">
            Topología interactiva de nodos y transiciones condicionales configuradas en <code>src/core/graph.py</code>.
          </p>
        </div>

        {/* Barra de Estadísticas Rápidas & Exportar */}
        <div className="flex items-center gap-2 flex-wrap">
          <Badge variant="secondary" className="font-mono text-xs py-1 px-2.5 gap-1.5">
            <LayersIcon className="size-3.5 text-primary" /> 9 Nodos + START/END
          </Badge>
          <Badge variant="secondary" className="font-mono text-xs py-1 px-2.5 gap-1.5">
            <CpuIcon className="size-3.5 text-purple-400" /> LLM por tenant.yaml
          </Badge>
          <Button
            variant="outline"
            size="sm"
            onClick={handleExportGraph}
            className="h-8 text-xs gap-1"
            title="Exportar esquema del grafo en formato JSON"
          >
            <DownloadIcon className="size-3.5" />
            Exportar Grafo
          </Button>
        </div>
      </div>

      {/* Grid: Canvas + Inspector Lateral */}
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-4">
        {/* Lienzo Interactivo React Flow */}
        <div className="h-[760px] rounded-2xl border bg-card/40 shadow-sm lg:col-span-3 overflow-hidden relative">
          <ReactFlow
            nodes={nodes}
            edges={edges}
            nodeTypes={nodeTypes}
            onNodesChange={onNodesChange}
            onEdgesChange={onEdgesChange}
            onNodeClick={onNodeClick}
            fitView
            fitViewOptions={{ padding: 0.2 }}
            attributionPosition="bottom-left"
            className="bg-muted/10"
          >
            <Background variant={BackgroundVariant.Dots} gap={24} size={1.2} />

            {/* Panel Flotante Superior Izquierdo: Simulación de Rutas y Reproductor Paso a Paso */}
            <Panel position="top-left" className="m-3">
              <div className="flex flex-col gap-2 p-2 rounded-xl border bg-card/95 backdrop-blur-md shadow-md max-w-sm">
                <div className="flex flex-wrap items-center gap-1.5">
                  <span className="text-[11px] font-semibold text-muted-foreground px-1 flex items-center gap-1">
                    <PlayIcon className="size-3 text-primary" /> Simular:
                  </span>
                  <Button
                    size="sm"
                    variant={activeSimulation === "standard" ? "default" : "outline"}
                    onClick={() => simulatePath("standard")}
                    className="h-7 text-xs gap-1 shadow-2xs"
                  >
                    <BookOpenIcon className="size-3 text-emerald-400" />
                    Consulta KB
                  </Button>
                  <Button
                    size="sm"
                    variant={activeSimulation === "escalate" ? "default" : "outline"}
                    onClick={() => simulatePath("escalate")}
                    className="h-7 text-xs gap-1 shadow-2xs text-destructive hover:text-destructive"
                  >
                    <PhoneForwardedIcon className="size-3" />
                    Escalado
                  </Button>
                  <Button
                    size="sm"
                    variant={activeSimulation === "sales" ? "default" : "outline"}
                    onClick={() => simulatePath("sales")}
                    className="h-7 text-xs gap-1 shadow-2xs"
                  >
                    <GaugeIcon className="size-3 text-amber-400" />
                    Ventas
                  </Button>
                  {activeSimulation && (
                    <Button
                      size="sm"
                      variant="ghost"
                      onClick={resetEdges}
                      className="h-7 text-xs px-2 text-muted-foreground hover:text-foreground"
                      title="Restablecer simulación"
                    >
                      <RotateCcwIcon className="size-3" />
                    </Button>
                  )}
                </div>

                {/* Reproductor Paso a Paso */}
                <div className="flex items-center justify-between border-t pt-1.5 text-[11px]">
                  <div className="flex items-center gap-1">
                    <span className="text-muted-foreground font-semibold">Paso:</span>
                    <Badge variant="outline" className="font-mono text-[10px]">
                      {stepIndex !== null ? `${stepIndex + 1}/${activeFlow.length} (${activeFlow[stepIndex]})` : "Inactivo"}
                    </Badge>
                  </div>
                  <div className="flex items-center gap-1">
                    <Button
                      size="sm"
                      variant="ghost"
                      onClick={() => setIsPlayingAuto((p) => !p)}
                      className="h-6 text-[10px] gap-1 px-1.5"
                      title={isPlayingAuto ? "Pausar reproducción" : "Reproducir paso a paso"}
                    >
                      {isPlayingAuto ? <PauseIcon className="size-3" /> : <PlayIcon className="size-3" />}
                      {isPlayingAuto ? "Pausar" : "Auto"}
                    </Button>
                    <Button
                      size="sm"
                      variant="outline"
                      onClick={handleStepForward}
                      className="h-6 text-[10px] gap-1 px-2"
                      title="Avanzar un nodo en el flujo"
                    >
                      <StepForwardIcon className="size-3" />
                      Siguiente
                    </Button>
                  </div>
                </div>
              </div>
            </Panel>

            {/* Panel Flotante Superior Derecho: Cambiar Disposición, Búsqueda y Re-centrar */}
            <Panel position="top-right" className="m-3">
              <div className="flex items-center gap-1.5 p-1.5 rounded-xl border bg-card/95 backdrop-blur-md shadow-md">
                <form onSubmit={handleSearchNode} className="flex items-center gap-1">
                  <Input
                    value={searchQuery}
                    onChange={(e) => setSearchQuery(e.target.value)}
                    placeholder="Buscar nodo..."
                    className="h-7 w-28 text-xs px-2"
                  />
                  <Button type="submit" size="icon" variant="ghost" className="size-7">
                    <SearchIcon className="size-3" />
                  </Button>
                </form>

                <Button
                  size="sm"
                  variant="outline"
                  onClick={toggleOrientation}
                  className="h-7 text-xs gap-1.5 shadow-2xs"
                  title="Alternar entre disposición Vertical y Horizontal"
                >
                  <ArrowRightLeftIcon className="size-3" />
                  {orientation === "vertical" ? "Disposición Horizontal" : "Disposición Vertical"}
                </Button>
                <Button
                  size="sm"
                  variant="ghost"
                  onClick={() => fitView({ padding: 0.2, duration: 400 })}
                  className="h-7 size-7 p-0"
                  title="Ajustar vista a pantalla completa"
                >
                  <Maximize2Icon className="size-3.5" />
                </Button>
              </div>
            </Panel>

            {/* Controles de Zoom / Ajuste */}
            <Controls position="bottom-left" showInteractive={false} />

            {/* MiniMapa */}
            <MiniMap
              position="bottom-right"
              nodeColor={(n) => {
                const d = n.data as AgentNodeData
                return d?.accentColor || "#64748b"
              }}
              className="bg-card border rounded-xl shadow-md"
            />
          </ReactFlow>
        </div>

        {/* Panel Lateral de Inspección del Nodo Seleccionado */}
        <div className="space-y-4">
          <Card className="shadow-xs border">
            <CardHeader className="pb-3 border-b">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <LayersIcon className="size-4 text-primary" />
                  <CardTitle className="text-sm font-semibold">
                    Inspector de Nodo
                  </CardTitle>
                </div>
                {selectedNodeData && (
                  <Button
                    variant="ghost"
                    size="icon"
                    className="size-7"
                    onClick={() => setIsConfigModalOpen(true)}
                    title="Editar parámetros del nodo"
                  >
                    <EditIcon className="size-3.5" />
                  </Button>
                )}
              </div>
              <CardDescription className="text-xs">
                Selecciona cualquier nodo para ver sus contratos de entrada y salida
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4 text-xs pt-4">
              {selectedNodeData ? (
                <>
                  <div>
                    <span className="text-muted-foreground block text-[10px] uppercase tracking-wider mb-1 font-semibold">
                      Identificador:
                    </span>
                    <div className="flex items-center gap-2">
                      <span className="font-mono text-sm font-bold">
                        {selectedNodeData.label}
                      </span>
                      <Badge
                        variant="outline"
                        className="text-[10px] uppercase font-mono capitalize"
                      >
                        {selectedNodeData.category}
                      </Badge>
                    </div>
                  </div>

                  <div>
                    <span className="text-muted-foreground block text-[10px] uppercase tracking-wider mb-1 font-semibold">
                      Archivo de Implementación:
                    </span>
                    <div className="flex items-center gap-1.5 rounded-lg border bg-muted/30 p-2 font-mono text-[11px]">
                      <FileCodeIcon className="size-3.5 text-primary shrink-0" />
                      <span className="truncate">{selectedNodeData.module}</span>
                    </div>
                  </div>

                  <div>
                    <span className="text-muted-foreground block text-[10px] uppercase tracking-wider mb-1 font-semibold">
                      Propósito del Nodo:
                    </span>
                    <p className="text-muted-foreground leading-relaxed">
                      {selectedNodeData.description}
                    </p>
                  </div>

                  {/* Entradas y Salidas */}
                  <div className="space-y-2 pt-2 border-t">
                    <div>
                      <span className="text-muted-foreground block text-[10px] uppercase tracking-wider mb-1 font-semibold">
                        Entradas (State Inputs):
                      </span>
                      <div className="flex flex-wrap gap-1">
                        {selectedNodeData.inputs.map((inp, idx) => (
                          <Badge
                            key={idx}
                            variant="secondary"
                            className="font-mono text-[10px] py-0 px-1.5"
                          >
                            {inp}
                          </Badge>
                        ))}
                      </div>
                    </div>

                    <div>
                      <span className="text-muted-foreground block text-[10px] uppercase tracking-wider mb-1 font-semibold">
                        Salidas (State Outputs):
                      </span>
                      <div className="flex flex-wrap gap-1">
                        {selectedNodeData.outputs.map((out, idx) => (
                          <Badge
                            key={idx}
                            variant="outline"
                            className="font-mono text-[10px] py-0 px-1.5 text-primary border-primary/40"
                          >
                            {out}
                          </Badge>
                        ))}
                      </div>
                    </div>
                  </div>

                  {/* Prompt Asociado */}
                  {selectedNodeData.promptSnippet && (
                    <div className="pt-2 border-t">
                      <span className="text-muted-foreground block text-[10px] uppercase tracking-wider mb-1 font-semibold">
                        Prompt en Catálogo:
                      </span>
                      <div className="rounded-lg border bg-muted/40 p-2.5 font-mono text-[11px] leading-relaxed">
                        {selectedNodeData.promptSnippet}
                      </div>
                    </div>
                  )}

                  <div className="pt-2 border-t text-[11px] text-muted-foreground space-y-1">
                    <div className="flex items-center gap-1 font-semibold text-foreground">
                      <CheckCircle2Icon className="size-3 text-emerald-500" />
                      LangGraph StateGraph
                    </div>
                    <p>
                      Los datos fluyen por el diccionario tipado <code>ConversationState</code>.
                    </p>
                  </div>
                </>
              ) : (
                <div className="text-muted-foreground py-6 text-center">
                  Selecciona un nodo en el canvas
                </div>
              )}
            </CardContent>
          </Card>

          {/* Tarjeta de Información */}
          <Card className="bg-primary/5 border-primary/20 shadow-xs">
            <CardContent className="p-4 space-y-2 text-xs">
              <div className="flex items-center gap-1.5 font-semibold text-primary">
                <InfoIcon className="size-3.5" /> Arquitectura Declarativa
              </div>
              <p className="text-muted-foreground leading-relaxed">
                Todas las transiciones condicionales se deciden dinámicamente según la clasificación del mensaje y las reglas de <code>tenant.yaml</code>.
              </p>
            </CardContent>
          </Card>
        </div>
      </div>

      {/* Modal de Configuración Rápida de Nodo */}
      {isConfigModalOpen && selectedNodeData && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-background/80 backdrop-blur-xs">
          <div className="relative w-full max-w-md rounded-2xl border bg-card p-6 shadow-xl space-y-4 text-xs">
            <div className="flex items-center justify-between border-b pb-3">
              <div>
                <h3 className="text-base font-bold">Configuración de Nodo: {selectedNodeData.label}</h3>
                <p className="text-muted-foreground text-[11px]">Solo lectura: los parámetros reales se editan en tenant.yaml y en la sección Prompts</p>
              </div>
              <Button
                variant="ghost"
                size="icon"
                onClick={() => setIsConfigModalOpen(false)}
                className="size-7 rounded-full"
              >
                <XIcon className="size-4" />
              </Button>
            </div>

            <div className="space-y-3">
              <div>
                <label className="font-semibold block mb-1">Módulo Python</label>
                <Input value={selectedNodeData.module} readOnly className="h-8 font-mono text-xs bg-muted/30" />
              </div>
              <div>
                <label className="font-semibold block mb-1">Descripción Funcional</label>
                <textarea
                  defaultValue={selectedNodeData.description}
                  readOnly
                  rows={3}
                  className="w-full rounded-md border bg-background p-2 text-xs"
                />
              </div>
            </div>

            <div className="flex items-center justify-end gap-2 pt-2 border-t">
              <Button size="sm" variant="outline" onClick={() => setIsConfigModalOpen(false)}>
                Cerrar
              </Button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

export function GraphWorkflowView() {
  return (
    <ReactFlowProvider>
      <FlowCanvas />
    </ReactFlowProvider>
  )
}
