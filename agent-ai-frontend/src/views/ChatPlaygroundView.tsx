import * as React from "react"
import { motion, AnimatePresence } from "framer-motion"
import {
  SendIcon,
  BotIcon,
  UserIcon,
  SparklesIcon,
  RotateCcwIcon,
  InfoIcon,
  CheckCircleIcon,
  AlertTriangleIcon,
  LayersIcon,
  DownloadIcon,
  CopyIcon,
  MicIcon,
  MicOffIcon,
  PlusIcon,
  Trash2Icon,
  MessagesSquareIcon,
  GaugeIcon,
  CpuIcon,
  EraserIcon,
} from "lucide-react"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Badge } from "@/components/ui/badge"
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card"
import { toast } from "sonner"
import type { ChatMessage, AgentActionTrace } from "@/types/agent"
import { api } from "@/services/api"


interface ChatPlaygroundViewProps {
  backendOnline: boolean
}

interface ChatSession {
  id: string
  name: string
  userId: string
  messages: ChatMessage[]
  updatedAt: string
}

const defaultPersonas = [
  {
    label: "¿Qué café venden?",
    prompt: "¿Qué café venden?",
    desc: "Consulta rápida de productos",
  },
  {
    label: "☕ Cliente Gourmet",
    prompt: "¿Cuáles son los perfiles de tueste y notas de cata de Lumbre Café?",
    desc: "Pregunta sobre especialidad y variedades",
  },
  {
    label: "📦 Suscripción",
    prompt: "¿Cómo funciona la suscripción mensual y tienen envíos gratis?",
    desc: "Consulta logística y precios",
  },
  {
    label: "💳 Medios de Pago",
    prompt: "¿Aceptan tarjeta de crédito y transferencias?",
    desc: "Dudas financieras y facturación",
  },
  {
    label: "🚨 Reclamo Humano",
    prompt: "Quiero hablar con una persona por favor",
    desc: "Dispara escalado y handoff",
  },
]

// Generadores deterministas fuera del componente para cumplir con React 19 purity
let idSequence = 1000
function generateMsgId(): string {
  idSequence += 1
  return `msg-${idSequence}`
}

function generateSessionId(): string {
  idSequence += 1
  return `sess-${idSequence}`
}

function getFormattedTime(): string {
  return new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })
}

function getIsoString(): string {
  return new Date().toISOString()
}

const thinkingSteps = [
  { step: 1, shortName: "Intención", label: "Análisis de Intención", desc: "Clasificando objetivo del mensaje con LangGraph...", icon: "🧠" },
  { step: 2, shortName: "RAG Semántico", label: "Base de Conocimiento", desc: "Recuperando bloques pertinentes de Lumbre Café...", icon: "🔍" },
  { step: 3, shortName: "Guardas", label: "Políticas y Guardas", desc: "Verificando límites de tokens y herramientas...", icon: "⚡" },
  { step: 4, shortName: "Groq LLM", label: "Generación de Respuesta", desc: "Sintetizando con Groq (GPT-OSS-120B)...", icon: "✨" },
]

export function ChatPlaygroundView({ backendOnline }: ChatPlaygroundViewProps) {

  // Manejo de múltiples sesiones persistidas en localStorage
  const [sessions, setSessions] = React.useState<ChatSession[]>(() => {
    try {
      const saved = localStorage.getItem("agente_chat_sessions")
      if (saved) return JSON.parse(saved)
    } catch {
      /* ignore storage read error */
    }
    return [
      {
        id: "sess-1",
        name: "Sesión Principal (Lumbre)",
        userId: "cliente-demo-1",
        messages: [
          {
            id: "welcome",
            sender: "agent",
            text: "¡Hola! Bienvenido a Lumbre Café ☕. Soy tu asistente virtual inteligente. ¿En qué puedo ayudarte hoy?",
            timestamp: "10:00",
            intents: ["chat"],
          },
        ],
        updatedAt: "2026-10-08T12:00:00Z",
      },
    ]
  })

  const [activeSessionId, setActiveSessionId] = React.useState<string>(sessions[0]?.id || "sess-1")
  const activeSession = sessions.find((s) => s.id === activeSessionId) || sessions[0]

  const [input, setInput] = React.useState("")
  const [isTyping, setIsTyping] = React.useState(false)
  const [streamingText, setStreamingText] = React.useState<string | null>(null)
  const [streamEnabled, setStreamEnabled] = React.useState(true)
  const [showTraceInChat, setShowTraceInChat] = React.useState(true)
  const [currentThoughtStep, setCurrentThoughtStep] = React.useState<number>(0)
  const [isRecordingVoice, setIsRecordingVoice] = React.useState(false)

  // Diagnóstico del último turno: solo datos reales del backend (o marcado como simulado sin backend).
  const [lastInspection, setLastInspection] = React.useState<{
    intent: string
    blocks: string[]
    connectors: Array<{ id: string; found: boolean }>
    escalated: boolean
    latencyMs?: number
    replyMode?: string
    verification?: string | null
    unsupportedClaims?: string[]
    model?: string | null
    provider?: string | null
    simulated: boolean
  } | null>(null)

  const messagesEndRef = React.useRef<HTMLDivElement>(null)

  // Guardar sesiones en localStorage
  React.useEffect(() => {
    try {
      localStorage.setItem("agente_chat_sessions", JSON.stringify(sessions))
    } catch {
      /* ignore storage save error */
    }
  }, [sessions])

  React.useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" })
  }, [activeSession?.messages, isTyping, streamingText])

  const setSessionMessages = React.useCallback((newMsgs: ChatMessage[] | ((prev: ChatMessage[]) => ChatMessage[])) => {
    setSessions((all) =>
      all.map((s) => {
        if (s.id !== activeSessionId) return s
        const resolved = typeof newMsgs === "function" ? newMsgs(s.messages) : newMsgs
        return {
          ...s,
          messages: resolved,
          updatedAt: getIsoString(),
        }
      })
    )
  }, [activeSessionId])

  // Crear nueva sesión
  const handleNewSession = () => {
    const newId = generateSessionId()
    const newSession: ChatSession = {
      id: newId,
      name: `Conversación #${sessions.length + 1}`,
      userId: `cliente-demo-${sessions.length + 1}`,
      messages: [
        {
          id: generateMsgId(),
          sender: "agent",
          text: "¡Hola! Bienvenido a Lumbre Café ☕. ¿En qué te puedo asesorar?",
          timestamp: getFormattedTime(),
          intents: ["chat"],
        },
      ],
      updatedAt: getIsoString(),
    }
    setSessions((prev) => [newSession, ...prev])
    setActiveSessionId(newId)
    toast.success("Nueva conversación creada")
  }

  // Vaciar completamente la conversación actual (0 mensajes y nuevo userId para limpiar memoria LangGraph)
  const handleEmptyChat = () => {
    const freshUserId = `cliente-${Date.now().toString().slice(-6)}`
    setSessions((all) =>
      all.map((s) => {
        if (s.id !== activeSessionId) return s
        return {
          ...s,
          userId: freshUserId,
          messages: [],
          updatedAt: getIsoString(),
        }
      })
    )
    toast.success("Historial de mensajes vaciado completamente")
  }

  // Eliminar conversación (si es la última, la reinicia desde cero totalmente limpia)
  const handleDeleteSession = (idToDelete: string) => {
    if (sessions.length <= 1) {
      const freshId = generateSessionId()
      const freshUserId = `cliente-${Date.now().toString().slice(-6)}`
      const freshSession: ChatSession = {
        id: freshId,
        name: "Conversación #1",
        userId: freshUserId,
        messages: [],
        updatedAt: getIsoString(),
      }
      setSessions([freshSession])
      setActiveSessionId(freshId)
      toast.info("Conversación reiniciada vacía desde cero")
      return
    }
    const filtered = sessions.filter((s) => s.id !== idToDelete)
    setSessions(filtered)
    setActiveSessionId(filtered[0].id)
    toast.info("Conversación eliminada")
  }

  // Restablecer conversación con mensaje de bienvenida inicial
  const handleResetWelcome = () => {
    const freshUserId = `cliente-${Date.now().toString().slice(-6)}`
    setSessions((all) =>
      all.map((s) => {
        if (s.id !== activeSessionId) return s
        return {
          ...s,
          userId: freshUserId,
          messages: [
            {
              id: generateMsgId(),
              sender: "agent",
              text: "¡Hola! Bienvenido a Lumbre Café ☕. Soy tu asistente virtual inteligente. ¿En qué puedo ayudarte hoy?",
              timestamp: getFormattedTime(),
              intents: ["chat"],
            },
          ],
          updatedAt: getIsoString(),
        }
      })
    )
    toast.success("Mensajes reiniciados con saludo inicial")
  }


  // Simular streaming de texto palabra por palabra con trazabilidad
  const streamBotReply = async (fullText: string, isEscalation: boolean, trace?: AgentActionTrace) => {
    if (!streamEnabled) {
      setSessionMessages((prev) => [
        ...prev,
        {
          id: generateMsgId(),
          sender: "agent",
          text: fullText,
          timestamp: getFormattedTime(),
          escalated: isEscalation,
          trace,
        },
      ])
      return
    }

    const words = fullText.split(" ")
    let current = ""
    setStreamingText("")

    for (let i = 0; i < words.length; i++) {
      current += (i === 0 ? "" : " ") + words[i]
      setStreamingText(current)
      await new Promise((r) => setTimeout(r, 20))
    }

    setSessionMessages((prev) => [
      ...prev,
      {
        id: generateMsgId(),
        sender: "agent",
        text: fullText,
        timestamp: getFormattedTime(),
        escalated: isEscalation,
        trace,
      },
    ])
    setStreamingText(null)
  }

  // Envío de mensaje con trazabilidad de acciones en tiempo real
  const handleSendMessage = async (textToSend?: string) => {
    const text = (textToSend || input).trim()
    if (!text || isTyping) return

    const userMsg: ChatMessage = {
      id: generateMsgId(),
      sender: "user",
      text,
      timestamp: getFormattedTime(),
    }

    setSessionMessages((prev) => [...prev, userMsg])
    setInput("")

    const startTime = performance.now()
    setIsTyping(true)
    setCurrentThoughtStep(0)

    try {
      const isEscalation = text.toLowerCase().includes("humano") || text.toLowerCase().includes("persona") || text.toLowerCase().includes("reclamo")

      // 1. Lanzar consulta al backend o simulación en paralelo
      const fetchPromise = (async () => {
        if (backendOnline) {
          try {
            const res = await api.sendWebMessage(activeSession.userId, text)
            return { res, error: null, ms: Math.round(performance.now() - startTime) }
          } catch (e) {
            return { res: null, error: e, ms: 0 }
          }
        }
        await new Promise((r) => setTimeout(r, 800))
        return { res: null, error: null, ms: 0 }
      })()

      // 2. Transición fluida y visible de los 4 pasos para que la audiencia aprecie la orquestación
      // Paso 1: Intención
      await new Promise((r) => setTimeout(r, 420))
      setCurrentThoughtStep(1)

      // Paso 2: RAG
      await new Promise((r) => setTimeout(r, 420))
      setCurrentThoughtStep(2)

      // Paso 3: Políticas y herramientas
      await new Promise((r) => setTimeout(r, 420))
      setCurrentThoughtStep(3)

      // Paso 4: Esperar respuesta del LLM si no terminó aún
      const { res: response, error: apiError, ms: backendMs } = await fetchPromise
      if (apiError) {
        throw apiError
      }
      await new Promise((r) => setTimeout(r, 380))

      let agentText = ""
      let detectedIntent = "info"
      let retrievedBlockName = "Catálogo General Lumbre Café"
      let actionTrace: AgentActionTrace | undefined

      if (response) {
        const action = response.actions?.[0]
        if (response.replies && response.replies.length > 0) {
          agentText = response.replies.join("\n\n")
        } else {
          const outbox = await api.getWebOutbox(activeSession.userId)
          agentText = outbox.length > 0 && outbox[outbox.length - 1].text
            ? outbox[outbox.length - 1].text!
            : "Respuesta procesada correctamente."
        }
        detectedIntent = action?.intent ?? "desconocida"
        const blockTitles = (action?.retrieved_blocks ?? []).map((b) => b.title)
        retrievedBlockName = blockTitles.join(", ")
        actionTrace = {
          intent: detectedIntent,
          detected_issue: action?.detected_issue,
          retrieved_blocks: action?.retrieved_blocks ?? [],
          connectors: action?.connectors ?? [],
          handoff: action?.handoff ?? false,
          reply_mode: action?.reply_mode,
          verification: action?.verification,
          unsupported_claims: action?.unsupported_claims,
          provider: action?.provider,
          model: action?.model,
          latency_ms: backendMs,
          step_summary: [
            `Intención clasificada: #${detectedIntent}`,
            `Bloques RAG: ${blockTitles.join(", ") || "ninguno"}`,
            action?.provider ? `Motor: ${action.provider} • ${action.model}` : "Motor: sin LLM (respuesta en crudo)",
          ],
        }
      } else {
        // Fallback simulado
        const lower = text.toLowerCase()
        if (lower.includes("venden") || lower.includes("tueste") || lower.includes("café")) {
          agentText = "En Lumbre Café tostamos café de especialidad (arábica 100%). Ofrecemos 3 perfiles: Suave (notas dulces a chocolate), Brillante (acidez cítrica frutal) e Intenso (cacao y especias). Viene en presentaciones de 250 g y 1 kg."
          detectedIntent = "info/products"
          retrievedBlockName = "Perfiles de Café y Variedades"
        } else if (lower.includes("suscrip") || lower.includes("mes") || lower.includes("envío")) {
          agentText = "Nuestra suscripción mensual incluye envío gratuito a domicilio todos los primeros martes del mes. Puedes pausar o cancelar en cualquier momento con un 15% de descuento respecto a compra única."
          detectedIntent = "sales/subscription"
          retrievedBlockName = "Planes de Suscripción"
        } else if (lower.includes("pago") || lower.includes("tarjeta") || lower.includes("transferencia")) {
          agentText = "Aceptamos tarjetas de débito y crédito (Visa, Mastercard, Amex), Mercado Pago y transferencias bancarias directas con confirmación automática."
          detectedIntent = "info/payments"
          retrievedBlockName = "Métodos de Pago"
        } else if (isEscalation) {
          agentText = "Comprendo perfectamente tu situación. He derivado tu caso a nuestro equipo de atención humana. Un especialista se comunicará contigo a la brevedad."
          detectedIntent = "escalate"
          retrievedBlockName = "Protocolo de Escalado Humano"
        } else {
          agentText = "En Lumbre Café estamos para ayudarte. ¿Deseas información sobre nuestros granos de café, suscripción mensual o consultar el estado de tu pedido?"
          detectedIntent = "chat/general"
          retrievedBlockName = "FAQ General"
        }
        actionTrace = {
          intent: detectedIntent,
          retrieved_blocks: [{ id: 1, title: retrievedBlockName, category: "cafe" }],
          handoff: isEscalation,
          reply_mode: "simulated",
          provider: "simulado",
          model: "demo-lumbre",
          step_summary: [
            `Intención clasificada: #${detectedIntent}`,
            `Bloques RAG: ${retrievedBlockName}`,
            `Motor: Reglas Lumbre Café (Modo Offline)`,
          ],
        }
      }


      setLastInspection({
        intent: detectedIntent,
        blocks: actionTrace?.retrieved_blocks?.map((b) => b.title) ?? [],
        connectors: actionTrace?.connectors ?? [],
        escalated: Boolean(actionTrace?.handoff),
        // La latencia de un turno simulado (sin backend) no es medible: solo es una espera artificial.
        latencyMs: response ? backendMs : undefined,
        replyMode: actionTrace?.reply_mode,
        verification: actionTrace?.verification,
        unsupportedClaims: actionTrace?.unsupported_claims,
        model: actionTrace?.model,
        provider: actionTrace?.provider,
        simulated: !response,
      })

      await streamBotReply(agentText, Boolean(actionTrace?.handoff), actionTrace)
    } catch (err) {
      toast.error(`Error al procesar: ${err instanceof Error ? err.message : "Desconocido"}`)
    } finally {
      setIsTyping(false)
    }
  }



  // Simular Nota de Voz (Speech-to-text)
  const handleSimulateVoice = () => {
    if (isRecordingVoice) {
      setIsRecordingVoice(false)
      return
    }

    setIsRecordingVoice(true)
    toast.info("Grabando nota de voz del cliente...", { duration: 1800 })

    setTimeout(() => {
      setIsRecordingVoice(false)
      const simulatedVoices = [
        "Hola, quería saber qué costo tiene el kilo de café intenso y si llega hoy a mi domicilio.",
        "Buenas tardes, quisiera consultar qué medios de pago tienen y si aceptan tarjeta.",
        "Necesito cancelar mi suscripción por favor, no puedo gestionarla desde la web.",
      ]
      const chosen = simulatedVoices[Math.floor(Math.random() * simulatedVoices.length)]
      setInput(chosen)
      toast.success("Voz transcrita exitosamente al campo de mensaje")
    }, 1800)
  }

  // Exportar transcripción
  const handleExportTranscript = () => {
    const lines = [
      `# Transcripción de Chat — ${activeSession.name}`,
      `**Usuario ID:** ${activeSession.userId}`,
      `**Fecha:** ${getFormattedTime()}`,
      "",
      "---",
      "",
    ]

    activeSession.messages.forEach((m) => {
      const sender = m.sender === "user" ? "Cliente" : "Agente IA (Lumbre)"
      lines.push(`**[${m.timestamp}] ${sender}:**\n${m.text}\n`)
    })

    const blob = new Blob([lines.join("\n")], { type: "text/markdown" })
    const url = URL.createObjectURL(blob)
    const a = document.createElement("a")
    a.href = url
    a.download = `chat_transcript_${activeSession.id}.md`
    a.click()
    URL.revokeObjectURL(url)
    toast.success("Transcripción descargada en Markdown")
  }

  // Copiar al portapapeles
  const handleCopyTranscript = () => {
    const text = activeSession.messages
      .map((m) => `[${m.timestamp}] ${m.sender === "user" ? "Cliente" : "Agente"}: ${m.text}`)
      .join("\n\n")
    navigator.clipboard.writeText(text)
    toast.success("Conversación copiada al portapapeles")
  }

  return (
    <div className="flex flex-col gap-6">
      {/* Encabezado y Selector de Sesiones */}
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <div className="flex items-center gap-2">
            <h2 className="text-2xl font-bold tracking-tight">Simulador de Chat en Vivo</h2>
            <Badge variant="outline" className="font-mono text-xs gap-1">
              <MessagesSquareIcon className="size-3 text-primary" /> Canal Web
            </Badge>
          </div>
          <p className="text-sm text-muted-foreground mt-0.5">
            Interacción en tiempo real conectada al webhook y orquestador LangGraph.
          </p>
        </div>

        {/* Acciones de Sesión */}
        <div className="flex items-center gap-2 flex-wrap">
          <select
            value={activeSessionId}
            onChange={(e) => setActiveSessionId(e.target.value)}
            className="h-8 rounded-lg border bg-card px-2.5 text-xs font-medium shadow-2xs"
          >
            {sessions.map((s) => (
              <option key={s.id} value={s.id}>
                {s.name}
              </option>
            ))}
          </select>

          <Button
            variant="outline"
            size="sm"
            onClick={handleNewSession}
            className="h-8 text-xs gap-1"
            title="Crear nueva conversación independiente"
          >
            <PlusIcon className="size-3.5" />
            Nueva
          </Button>

          <Button
            variant="outline"
            size="sm"
            onClick={handleEmptyChat}
            className="h-8 text-xs gap-1 text-amber-600 dark:text-amber-400 hover:text-amber-700 hover:bg-amber-500/10"
            title="Vaciar completamente todos los mensajes de esta conversación"
          >
            <EraserIcon className="size-3.5" />
            Vaciar Chat
          </Button>

          <Button
            variant="outline"
            size="sm"
            onClick={() => handleDeleteSession(activeSession.id)}
            className="h-8 text-xs gap-1 text-destructive hover:text-destructive hover:bg-destructive/10"
            title="Eliminar esta conversación"
          >
            <Trash2Icon className="size-3.5" />
            Eliminar
          </Button>

          <Button
            variant="ghost"
            size="sm"
            onClick={handleResetWelcome}
            className="h-8 text-xs text-muted-foreground hover:text-foreground gap-1"
            title="Restablecer saludo inicial de Lumbre Café"
          >
            <RotateCcwIcon className="size-3.5" />
            Reiniciar
          </Button>

          <Button
            variant="outline"
            size="sm"
            onClick={handleCopyTranscript}
            className="h-8 text-xs gap-1"
            title="Copiar texto de la conversación"
          >
            <CopyIcon className="size-3.5" />
            Copiar
          </Button>

          <Button
            variant="outline"
            size="sm"
            onClick={handleExportTranscript}
            className="h-8 text-xs gap-1"
            title="Descargar conversación como Markdown"
          >
            <DownloadIcon className="size-3.5" />
            Exportar
          </Button>
        </div>
      </div>

      {/* Grid Chat + Inspector */}
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
        {/* Ventana de Chat */}
        <Card className="flex flex-col h-[650px] lg:col-span-2 shadow-xs border">
          {/* Barra superior de la ventana de chat */}
          <CardHeader className="py-3 px-4 border-b bg-card/60 flex flex-row items-center justify-between">
            <div className="flex items-center gap-2.5">
              <div className="relative">
                <div className="flex size-9 items-center justify-center rounded-xl bg-primary/10 text-primary">
                  <BotIcon className="size-5" />
                </div>
                <span className="absolute bottom-0 right-0 size-2.5 rounded-full bg-emerald-500 border-2 border-background" />
              </div>
              <div>
                <CardTitle className="text-sm font-bold">Lumbre Bot (Canal Web)</CardTitle>
                <CardDescription className="text-[11px]">
                  LangGraph Agent • RAG Semántico • Meta Webhook
                </CardDescription>
              </div>
            </div>

            <div className="flex items-center gap-2">
              <Button
                variant={showTraceInChat ? "default" : "outline"}
                size="sm"
                onClick={() => setShowTraceInChat((p) => !p)}
                className="h-7 text-[11px] gap-1 px-2"
                title="Mostrar u ocultar las acciones del LLM en cada mensaje"
              >
                <CpuIcon className="size-3" />
                {showTraceInChat ? "Acciones LLM: ON" : "Acciones LLM: OFF"}
              </Button>
              <Button
                variant={streamEnabled ? "secondary" : "outline"}
                size="sm"
                onClick={() => setStreamEnabled((p) => !p)}
                className="h-7 text-[11px] gap-1 px-2"
                title="Efecto de escritura en vivo"
              >
                <SparklesIcon className="size-3" />
                {streamEnabled ? "Streaming ON" : "Streaming OFF"}
              </Button>
            </div>

          </CardHeader>

          {/* Área de Mensajes */}
          <CardContent className="flex-1 overflow-y-auto p-4 space-y-4 flex flex-col">
            {activeSession.messages.length === 0 && !isTyping && (
              <div className="flex flex-col items-center justify-center my-auto py-12 text-center text-muted-foreground space-y-3">
                <div className="size-12 rounded-2xl bg-primary/10 flex items-center justify-center text-primary">
                  <BotIcon className="size-6" />
                </div>
                <div className="space-y-1">
                  <h3 className="font-semibold text-sm text-foreground">Conversación Vacía</h3>
                  <p className="text-xs max-w-sm text-muted-foreground">
                    El historial se ha vaciado por completo. Escribe un mensaje o haz clic en cualquiera de los casos rápidos abajo para comenzar.
                  </p>
                </div>
              </div>
            )}

            <AnimatePresence initial={false}>
              {activeSession.messages.map((msg) => {
                const isUser = msg.sender === "user"
                return (
                  <motion.div
                    key={msg.id}
                    initial={{ opacity: 0, y: 10, scale: 0.98 }}
                    animate={{ opacity: 1, y: 0, scale: 1 }}
                    transition={{ duration: 0.2 }}
                    className={`flex items-start gap-2.5 ${isUser ? "flex-row-reverse" : "flex-row"}`}
                  >
                    <div
                      className={`flex size-7 shrink-0 items-center justify-center rounded-full text-xs ${
                        isUser
                          ? "bg-primary text-primary-foreground"
                          : "bg-muted text-muted-foreground border"
                      }`}
                    >
                      {isUser ? <UserIcon className="size-3.5" /> : <BotIcon className="size-3.5" />}
                    </div>

                    <div
                      className={`max-w-[80%] rounded-2xl p-3.5 text-xs leading-relaxed shadow-2xs ${
                        isUser
                          ? "bg-primary text-primary-foreground rounded-tr-xs"
                          : "bg-muted/70 text-foreground border rounded-tl-xs"
                      }`}
                    >
                      <p className="whitespace-pre-wrap">{msg.text}</p>

                      {/* Trazabilidad de Acciones del Agente (Compact Pills) */}
                      {!isUser && msg.trace && showTraceInChat && (
                        <div className="mt-2.5 pt-2 border-t border-border/30 text-[11px] flex flex-wrap items-center gap-1.5">
                          <Badge
                            variant="outline"
                            className="text-[9px] py-0 px-1.5 font-mono uppercase bg-primary/10 text-primary border-primary/20 gap-0.5"
                          >
                            <CpuIcon className="size-2.5" /> #{msg.trace.intent || "chat"}
                          </Badge>
                          {msg.trace.retrieved_blocks && msg.trace.retrieved_blocks.length > 0 && (
                            <Badge
                              variant="secondary"
                              className="text-[9px] py-0 px-1.5 font-sans text-muted-foreground gap-1 bg-muted/80 max-w-full truncate"
                              title={msg.trace.retrieved_blocks.map((b) => b.title).join(", ")}
                            >
                              <LayersIcon className="size-2.5 text-primary shrink-0" />
                              <span className="truncate">
                                {msg.trace.retrieved_blocks.map((b) => b.title).join(" • ")}
                              </span>
                            </Badge>
                          )}
                          {msg.trace.latency_ms && (
                            <span className="text-[9px] font-mono text-muted-foreground ml-auto">
                              ⚡ {msg.trace.latency_ms} ms
                            </span>
                          )}
                        </div>
                      )}

                      <div
                        className={`flex items-center gap-2 mt-1.5 text-[10px] ${
                          isUser ? "text-primary-foreground/75 justify-end" : "text-muted-foreground"
                        }`}
                      >
                        <span>{msg.timestamp}</span>
                        {msg.escalated && (
                          <Badge
                            variant="destructive"
                            className="text-[9px] py-0 px-1 font-mono uppercase gap-0.5"
                          >
                            <AlertTriangleIcon className="size-2.5" /> Escalado
                          </Badge>
                        )}
                      </div>
                    </div>
                  </motion.div>
                )
              })}

              {/* Burbuja de Streaming en vivo */}
              {streamingText !== null && (
                <motion.div
                  initial={{ opacity: 0, y: 8 }}
                  animate={{ opacity: 1, y: 0 }}
                  className="flex items-start gap-2.5 flex-row"
                >
                  <div className="flex size-7 shrink-0 items-center justify-center rounded-full bg-muted text-muted-foreground border">
                    <BotIcon className="size-3.5" />
                  </div>
                  <div className="max-w-[80%] rounded-2xl rounded-tl-xs bg-muted/70 text-foreground border p-3.5 text-xs leading-relaxed shadow-2xs">
                    <p className="whitespace-pre-wrap">
                      {streamingText}
                      <span className="inline-block w-1.5 h-3.5 ml-1 bg-primary animate-pulse align-middle" />
                    </p>
                  </div>
                </motion.div>
              )}

              {/* Indicador de Acciones en Curso del Agente (Pipeline Visual Horizontal) */}
              {isTyping && streamingText === null && (
                <motion.div
                  initial={{ opacity: 0, y: 8, scale: 0.98 }}
                  animate={{ opacity: 1, y: 0, scale: 1 }}
                  exit={{ opacity: 0, y: -4 }}
                  className="pl-9 max-w-[85%]"
                >
                  <div className="p-3.5 rounded-2xl bg-card border border-primary/25 shadow-sm space-y-2.5">
                    {/* Encabezado del Pipeline */}
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-2">
                        <span className="relative flex size-2">
                          <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-primary opacity-75" />
                          <span className="relative inline-flex rounded-full size-2 bg-primary" />
                        </span>
                        <span className="font-semibold text-xs text-foreground tracking-tight flex items-center gap-1.5">
                          <CpuIcon className="size-3.5 text-primary animate-spin" />
                          Pipeline LangGraph en Ejecución
                        </span>
                      </div>
                      <Badge variant="outline" className="text-[10px] py-0 px-1.5 font-mono bg-primary/10 text-primary border-primary/25">
                        Paso {currentThoughtStep + 1} de 4
                      </Badge>
                    </div>

                    {/* Stepper Horizontal de 4 Nodos */}
                    <div className="grid grid-cols-4 gap-1.5">
                      {thinkingSteps.map((step, idx) => {
                        const isCurrent = idx === currentThoughtStep
                        const isDone = idx < currentThoughtStep
                        return (
                          <div
                            key={idx}
                            className={`flex flex-col items-center justify-center p-2 rounded-xl text-center transition-all duration-300 ${
                              isCurrent
                                ? "bg-primary/15 border border-primary text-primary font-semibold shadow-xs scale-105 ring-2 ring-primary/20"
                                : isDone
                                ? "bg-emerald-500/10 border border-emerald-500/30 text-emerald-600 dark:text-emerald-400"
                                : "bg-muted/40 border border-transparent text-muted-foreground/40"
                            }`}
                          >
                            <span className="text-sm mb-0.5">{step.icon}</span>
                            <span className="text-[10px] leading-tight font-medium line-clamp-1">
                              {step.shortName}
                            </span>
                            {isDone ? (
                              <CheckCircleIcon className="size-2.5 text-emerald-500 mt-0.5" />
                            ) : isCurrent ? (
                              <span className="size-1.5 rounded-full bg-primary mt-1 animate-pulse" />
                            ) : (
                              <span className="size-1.5 rounded-full bg-muted mt-1" />
                            )}
                          </div>
                        )
                      })}
                    </div>

                    {/* Descripción del nodo activo */}
                    <div className="flex items-center gap-2 pt-1 border-t border-border/40 text-[11px] text-muted-foreground">
                      <span className="font-semibold text-foreground">
                        {thinkingSteps[currentThoughtStep]?.label}:
                      </span>
                      <span className="truncate italic">
                        {thinkingSteps[currentThoughtStep]?.desc}
                      </span>
                    </div>
                  </div>
                </motion.div>
              )}


            </AnimatePresence>
            <div ref={messagesEndRef} />
          </CardContent>

          {/* Barra de Personas / Consultas Rápidas */}
          <div className="px-4 py-2 bg-muted/20 border-t flex items-center gap-1.5 overflow-x-auto text-[11px]">
            <span className="text-muted-foreground shrink-0 flex items-center gap-1">
              <SparklesIcon className="size-3 text-primary" /> Casos rápidos:
            </span>
            {defaultPersonas.map((persona, idx) => (
              <Button
                key={idx}
                variant="outline"
                size="sm"
                onClick={() => handleSendMessage(persona.prompt)}
                disabled={isTyping}
                className="h-6 text-[10px] shrink-0 font-normal px-2 bg-background hover:bg-muted"
                title={persona.desc}
              >
                {persona.label}
              </Button>
            ))}
          </div>

          {/* Input de Mensaje */}
          <div className="p-3 border-t bg-card/60 flex items-center gap-2">
            <Button
              variant={isRecordingVoice ? "destructive" : "outline"}
              size="icon"
              onClick={handleSimulateVoice}
              disabled={isTyping}
              className="size-9 rounded-xl shrink-0"
              title="Simular mensaje de audio con transcripción automática"
            >
              {isRecordingVoice ? (
                <MicOffIcon className="size-4 animate-pulse" />
              ) : (
                <MicIcon className="size-4" />
              )}
            </Button>

            <Input
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter" && !e.shiftKey) {
                  e.preventDefault()
                  handleSendMessage()
                }
              }}
              placeholder="Escribe una pregunta para el agente..."
              disabled={isTyping}
              className="h-9 text-xs"
            />

            <Button
              onClick={() => handleSendMessage()}
              disabled={isTyping || !input.trim()}
              size="icon"
              className="size-9 rounded-xl shrink-0 shadow-xs"
            >
              <SendIcon className="size-4" />
            </Button>
          </div>
        </Card>

        {/* Panel de Inspección y Diagnóstico del Turno */}
        <div className="space-y-4">
          <Card className="shadow-xs border">
            <CardHeader className="pb-3 border-b">
              <div className="flex items-center gap-2">
                <GaugeIcon className="size-4 text-primary" />
                <CardTitle className="text-sm font-semibold">
                  Inspector de Grafo LangGraph
                </CardTitle>
              </div>
              <CardDescription className="text-xs">
                Métricas internas registradas en el último turno de conversación
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-3.5 text-xs pt-4">
              {!lastInspection ? (
                <p className="text-muted-foreground text-[11px] py-4 text-center">
                  Envía un mensaje para ver el diagnóstico del turno.
                </p>
              ) : (
                <>
                  {lastInspection.simulated && (
                    <div className="p-2 rounded-lg border border-amber-500/30 bg-amber-500/10 text-amber-700 dark:text-amber-400 text-[11px]">
                      Backend sin conexión: respuesta simulada con reglas locales.
                    </div>
                  )}
                  <div>
                    <span className="text-muted-foreground block text-[10px] uppercase tracking-wider mb-1 font-semibold">
                      Intención Clasificada:
                    </span>
                    <Badge variant="outline" className="font-mono text-xs">
                      #{lastInspection.intent}
                    </Badge>
                  </div>

                  <div>
                    <span className="text-muted-foreground block text-[10px] uppercase tracking-wider mb-1 font-semibold">
                      Bloques RAG Recuperados:
                    </span>
                    {lastInspection.blocks.length > 0 ? (
                      <div className="space-y-1">
                        {lastInspection.blocks.map((title, i) => (
                          <div key={i} className="rounded-lg border bg-muted/40 p-2 text-[11px] font-medium flex items-center gap-1.5">
                            <LayersIcon className="size-3 text-primary shrink-0" />
                            <span className="truncate">{title}</span>
                          </div>
                        ))}
                      </div>
                    ) : (
                      <span className="text-muted-foreground text-[11px]">Ninguno</span>
                    )}
                  </div>

                  {lastInspection.connectors.length > 0 && (
                    <div>
                      <span className="text-muted-foreground block text-[10px] uppercase tracking-wider mb-1 font-semibold">
                        Conectores:
                      </span>
                      <div className="flex flex-wrap gap-1">
                        {lastInspection.connectors.map((c) => (
                          <Badge key={c.id} variant={c.found ? "secondary" : "outline"} className="font-mono text-[10px]">
                            {c.id}: {c.found ? "dato encontrado" : "sin dato"}
                          </Badge>
                        ))}
                      </div>
                    </div>
                  )}

                  <div>
                    <span className="text-muted-foreground block text-[10px] uppercase tracking-wider mb-1 font-semibold">
                      Motor de Inferencia LLM:
                    </span>
                    <div className="rounded-lg border bg-muted/40 p-2 text-[11px] font-mono flex items-center justify-between gap-2">
                      <span className="flex items-center gap-1.5 min-w-0">
                        <CpuIcon className="size-3 text-primary shrink-0" />
                        <span className="truncate">
                          {lastInspection.provider ? `${lastInspection.provider}: ${lastInspection.model}` : "Sin LLM"}
                        </span>
                      </span>
                      {lastInspection.replyMode && (
                        <Badge
                          variant={lastInspection.replyMode === "llm" ? "secondary" : "destructive"}
                          className="text-[9px] py-0 shrink-0"
                          title="Cómo se generó la respuesta: llm = normal; llm_error / fallback / raw = el LLM no participó"
                        >
                          {lastInspection.replyMode}
                        </Badge>
                      )}
                    </div>
                  </div>

                  {lastInspection.verification && lastInspection.verification !== "skipped" && (
                    <div>
                      <span className="text-muted-foreground block text-[10px] uppercase tracking-wider mb-1 font-semibold">
                        Verificación anti-alucinación:
                      </span>
                      {lastInspection.verification === "supported" && (
                        <div className="p-2 rounded-lg border border-emerald-500/30 bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 text-[11px]">
                          Respuesta respaldada por la KB / datos.
                        </div>
                      )}
                      {lastInspection.verification === "rejected" && (
                        <div className="p-2 rounded-lg border border-destructive/30 bg-destructive/10 text-destructive text-[11px] space-y-1">
                          <div>Respuesta bloqueada: afirmaba datos sin respaldo.</div>
                          {lastInspection.unsupportedClaims?.map((c, i) => (
                            <div key={i} className="font-mono text-[10px]">• {c}</div>
                          ))}
                        </div>
                      )}
                      {lastInspection.verification === "error" && (
                        <div className="p-2 rounded-lg border border-amber-500/30 bg-amber-500/10 text-amber-700 dark:text-amber-400 text-[11px]">
                          El verificador falló; se envió la respuesta sin verificar.
                        </div>
                      )}
                    </div>
                  )}

                  {lastInspection.latencyMs !== undefined && (
                    <div className="p-2 rounded-lg border bg-muted/20">
                      <span className="text-[10px] text-muted-foreground block">Latencia total (petición al backend)</span>
                      <span className="font-mono font-bold text-sm text-foreground">
                        {lastInspection.latencyMs} ms
                      </span>
                    </div>
                  )}

                  <div className="pt-2 border-t">
                    <span className="text-muted-foreground block text-[10px] uppercase tracking-wider mb-1 font-semibold">
                      Estado de Derivación (Handoff):
                    </span>
                    {lastInspection.escalated ? (
                      <div className="p-2.5 rounded-lg border border-destructive/30 bg-destructive/10 text-destructive text-[11px] flex items-center gap-2">
                        <AlertTriangleIcon className="size-4 shrink-0" />
                        <span>Señal de escalado activada. Transferido a mesa humana.</span>
                      </div>
                    ) : (
                      <div className="p-2.5 rounded-lg border border-emerald-500/30 bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 text-[11px] flex items-center gap-2">
                        <CheckCircleIcon className="size-4 shrink-0" />
                        <span>Resuelto autónomamente por el agente.</span>
                      </div>
                    )}
                  </div>
                </>
              )}
            </CardContent>
          </Card>

          {/* Información del Canal */}
          <Card className="bg-primary/5 border-primary/20 shadow-xs">
            <CardContent className="p-4 space-y-2 text-xs">
              <div className="flex items-center gap-1.5 font-semibold text-primary">
                <InfoIcon className="size-3.5" /> Adaptador de Mensajería
              </div>
              <p className="text-muted-foreground leading-relaxed">
                Este chat replica exactamente el contrato de entrada y salida usado por los adaptadores de WhatsApp Cloud API y Twilio SMS.
              </p>
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  )
}
