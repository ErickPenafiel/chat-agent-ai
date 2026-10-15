import * as React from "react"
import { motion } from "framer-motion"
import {
  PlayIcon,
  CheckIcon,
  VariableIcon,
  SaveIcon,
  RotateCcwIcon,
  DownloadIcon,
  ColumnsIcon,
  FileTextIcon,
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
import { Input } from "@/components/ui/input"
import { toast } from "sonner"
import type { PromptItem } from "@/types/agent"
import { mockPrompts } from "@/services/mockData"
import { api } from "@/services/api"

interface PromptsViewProps {
  backendOnline: boolean
}

const availableVariables: Record<string, string[]> = {
  agent_chat: ["business_name", "tone_formality", "tone_address", "kb_context", "user_message"],
  intent_classifier: ["business_name", "allowed_intents", "user_message"],
  sales_capture: ["business_name", "required_fields", "conversation_history"],
  handoff_summary: ["customer_name", "issue_summary", "sla_hours"],
  fallback_general: ["business_name", "support_channel"],
}

export function PromptsView({ backendOnline }: PromptsViewProps) {
  const [prompts, setPrompts] = React.useState<PromptItem[]>(mockPrompts)
  const [selectedPrompt, setSelectedPrompt] = React.useState<PromptItem>(mockPrompts[0])
  const [promptText, setPromptText] = React.useState<string>(mockPrompts[0].text)
  const [originalText, setOriginalText] = React.useState<string>(mockPrompts[0].text)
  const [previewResult, setPreviewResult] = React.useState<string | null>(null)
  const [isTesting, setIsTesting] = React.useState(false)
  const [isSaving, setIsSaving] = React.useState(false)
  const [viewMode, setViewMode] = React.useState<"editor" | "diff" | "ab_test">("editor")

  // Variables de prueba interactivas
  const [testVariables, setTestVariables] = React.useState<Record<string, string>>({
    business_name: "Lumbre Café",
    tone_formality: "informal",
    tone_address: "tú",
    kb_context: "Vendemos café de especialidad en grano y molido. Métodos de pago: Tarjeta y transferencias.",
    sla_hours: "12",
  })

  const textareaRef = React.useRef<HTMLTextAreaElement>(null)

  React.useEffect(() => {
    if (backendOnline) {
      api.getPrompts()
        .then((data) => {
          if (data && data.length > 0) {
            setPrompts(data)
            setSelectedPrompt(data[0])
            setPromptText(data[0].text)
            setOriginalText(data[0].text)
          }
        })
        .catch(() => {})
    }
  }, [backendOnline])

  const handleSelectPrompt = (p: PromptItem) => {
    setSelectedPrompt(p)
    setPromptText(p.text)
    setOriginalText(p.text)
    setPreviewResult(null)
  }

  // Insertar variable en cursor
  const handleInsertVariable = (varName: string) => {
    const token = `{{${varName}}}`
    if (!textareaRef.current) {
      setPromptText((prev) => prev + ` ${token}`)
      return
    }

    const start = textareaRef.current.selectionStart
    const end = textareaRef.current.selectionEnd
    const nextText = promptText.substring(0, start) + token + promptText.substring(end)
    setPromptText(nextText)

    setTimeout(() => {
      if (textareaRef.current) {
        textareaRef.current.selectionStart = textareaRef.current.selectionEnd = start + token.length
        textareaRef.current.focus()
      }
    }, 10)
    toast.info(`Variable ${token} insertada`)
  }

  // Probar preview
  const handleTestPreview = async () => {
    setIsTesting(true)
    const promptId = selectedPrompt.slug || selectedPrompt.name || "agent_chat"
    try {
      if (backendOnline) {
        const res = await api.previewPrompt(promptId, testVariables)
        setPreviewResult(res.rendered)
      } else {
        await new Promise((r) => setTimeout(r, 350))
        let rendered = promptText
        Object.entries(testVariables).forEach(([k, v]) => {
          rendered = rendered.replaceAll(`{${k}}`, v).replaceAll(`{{${k}}}`, v)
        })
        setPreviewResult(rendered)
      }
      toast.success("Preview generado exitosamente")
    } catch {
      let rendered = promptText
      Object.entries(testVariables).forEach(([k, v]) => {
        rendered = rendered.replaceAll(`{${k}}`, v).replaceAll(`{{${k}}}`, v)
      })
      setPreviewResult(rendered)
    } finally {
      setIsTesting(false)
    }
  }

  // Guardar prompt
  const handleSavePrompt = async () => {
    const promptId = selectedPrompt.slug || selectedPrompt.name || "agent_chat"
    setIsSaving(true)
    try {
      if (backendOnline) {
        await api.updatePrompt(promptId, promptText)
      }
      setOriginalText(promptText)
      setPrompts((prev) =>
        prev.map((p) => {
          const currentSlug = p.slug || p.name
          return currentSlug === promptId ? { ...p, text: promptText } : p
        })
      )
      toast.success(`Prompt "${promptId}" guardado con éxito`)
    } catch (err) {
      toast.error(`Error al guardar: ${err instanceof Error ? err.message : "Desconocido"}`)
    } finally {
      setIsSaving(false)
    }
  }

  // Restablecer a original
  const handleResetToDefault = () => {
    setPromptText(originalText)
    toast.info("Prompt revertido a la versión original")
  }

  // Exportar catálogo
  const handleExportPrompts = () => {
    const dataStr = "data:text/json;charset=utf-8," + encodeURIComponent(JSON.stringify(prompts, null, 2))
    const a = document.createElement("a")
    a.href = dataStr
    a.download = `system_prompts_catalog_${new Date().toISOString().slice(0, 10)}.json`
    a.click()
    toast.success("Catálogo de prompts exportado como JSON")
  }

  const currentSlug = selectedPrompt.slug || selectedPrompt.name || "agent_chat"
  const currentVars = availableVariables[currentSlug] || [
    "business_name",
    "tone_formality",
    "kb_context",
  ]

  const hasModifications = promptText !== originalText

  return (
    <div className="flex flex-col gap-6">
      {/* Encabezado */}
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <div className="flex items-center gap-2">
            <h2 className="text-2xl font-bold tracking-tight">Catálogo de Prompts</h2>
            <Badge variant="outline" className="font-mono text-xs">
              {prompts.length} Prompts del Sistema
            </Badge>
          </div>
          <p className="text-sm text-muted-foreground mt-0.5">
            Configuración y personalización de las instrucciones directas enviadas al modelo LLM.
          </p>
        </div>

        <div className="flex items-center gap-2 flex-wrap">
          <Button
            variant="outline"
            size="sm"
            onClick={handleExportPrompts}
            className="h-8 text-xs gap-1"
          >
            <DownloadIcon className="size-3.5" />
            Exportar Prompts
          </Button>

          <Button
            variant={hasModifications ? "default" : "outline"}
            size="sm"
            onClick={handleSavePrompt}
            disabled={isSaving || !hasModifications}
            className="h-8 text-xs gap-1.5 shadow-xs"
          >
            <SaveIcon className="size-3.5" />
            {isSaving ? "Guardando..." : "Guardar Cambios"}
          </Button>
        </div>
      </div>

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
        {/* Lista de Prompts */}
        <div className="space-y-3">
          <h3 className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
            Prompts Registrados
          </h3>
          <div className="space-y-2">
            {prompts.map((p) => {
              const slug = p.slug || p.name || "prompt"
              const isSelected = currentSlug === slug
              return (
                <motion.button
                  key={slug}
                  whileHover={{ scale: 1.01 }}
                  whileTap={{ scale: 0.99 }}
                  onClick={() => handleSelectPrompt(p)}
                  className={`w-full text-left p-3.5 rounded-xl border transition-all ${
                    isSelected
                      ? "bg-primary text-primary-foreground border-primary shadow-xs"
                      : "bg-card hover:border-primary/40"
                  }`}
                >
                  <div className="flex items-center justify-between">
                    <span className="font-mono font-semibold text-sm">{slug}</span>
                    <Badge
                      variant={isSelected ? "secondary" : "outline"}
                      className="text-[10px] uppercase font-mono"
                    >
                      {slug.split("_")[0]}
                    </Badge>
                  </div>
                  <p
                    className={`text-xs mt-1 line-clamp-2 ${
                      isSelected ? "text-primary-foreground/80" : "text-muted-foreground"
                    }`}
                  >
                    {p.text}
                  </p>
                </motion.button>
              )
            })}
          </div>
        </div>

        {/* Editor y Vista de Variables / Diff */}
        <div className="lg:col-span-2 space-y-4">
          <Card className="shadow-xs border">
            <CardHeader className="pb-3 border-b flex flex-row items-center justify-between">
              <div>
                <div className="flex items-center gap-2">
                  <FileTextIcon className="size-4 text-primary" />
                  <CardTitle className="text-base font-bold font-mono">
                    {currentSlug}
                  </CardTitle>
                </div>
                <CardDescription className="text-xs">
                  Modifica las directivas del sistema e inserta variables dinámicas del tenant
                </CardDescription>
              </div>

              {/* Selector de Modos: Editor vs Diff vs A/B */}
              <div className="flex items-center gap-1">
                <Button
                  size="sm"
                  variant={viewMode === "editor" ? "default" : "ghost"}
                  onClick={() => setViewMode("editor")}
                  className="h-7 text-xs"
                >
                  Editor
                </Button>
                <Button
                  size="sm"
                  variant={viewMode === "diff" ? "default" : "ghost"}
                  onClick={() => setViewMode("diff")}
                  className="h-7 text-xs gap-1"
                >
                  <ColumnsIcon className="size-3" />
                  Comparativa
                </Button>
              </div>
            </CardHeader>

            <CardContent className="space-y-4 pt-4 text-xs">
              {/* Chips de Variables Dinámicas */}
              <div>
                <span className="text-[11px] font-semibold text-muted-foreground flex items-center gap-1 mb-2">
                  <VariableIcon className="size-3 text-primary" /> Variables disponibles para este prompt (clic para insertar):
                </span>
                <div className="flex flex-wrap gap-1.5">
                  {currentVars.map((v) => (
                    <Button
                      key={v}
                      type="button"
                      variant="secondary"
                      size="sm"
                      onClick={() => handleInsertVariable(v)}
                      className="h-6 text-[11px] font-mono hover:bg-primary hover:text-primary-foreground"
                    >
                      +{`{{${v}}}`}
                    </Button>
                  ))}
                </div>
              </div>

              {/* Vista Editor vs Comparativa */}
              {viewMode === "editor" ? (
                <div>
                  <textarea
                    ref={textareaRef}
                    rows={10}
                    value={promptText}
                    onChange={(e) => setPromptText(e.target.value)}
                    className="w-full rounded-xl border bg-muted/20 p-3 font-mono text-xs leading-relaxed focus:outline-hidden focus:ring-2 focus:ring-primary/50"
                  />
                  <div className="flex items-center justify-between mt-2 text-[11px] text-muted-foreground">
                    <span>{promptText.length} caracteres • {promptText.split(/\s+/).filter(Boolean).length} palabras</span>
                    {hasModifications && (
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={handleResetToDefault}
                        className="h-6 text-xs text-muted-foreground hover:text-foreground gap-1"
                      >
                        <RotateCcwIcon className="size-3" />
                        Revertir cambios
                      </Button>
                    )}
                  </div>
                </div>
              ) : (
                <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                  <div className="space-y-1">
                    <span className="font-semibold text-muted-foreground block text-[11px]">Versión Original:</span>
                    <div className="p-3 rounded-xl border bg-muted/30 font-mono text-xs whitespace-pre-wrap max-h-64 overflow-y-auto">
                      {originalText}
                    </div>
                  </div>
                  <div className="space-y-1">
                    <span className="font-semibold text-primary block text-[11px]">Versión Editada (Actual):</span>
                    <div className="p-3 rounded-xl border border-primary/30 bg-primary/5 font-mono text-xs whitespace-pre-wrap max-h-64 overflow-y-auto">
                      {promptText}
                    </div>
                  </div>
                </div>
              )}

              {/* Parámetros de Prueba para Simulación */}
              <div className="border-t pt-3 space-y-2">
                <span className="text-[11px] font-semibold text-muted-foreground block">
                  Variables de Prueba para Renderizado:
                </span>
                <div className="grid grid-cols-2 gap-2">
                  <div>
                    <label className="text-[10px] text-muted-foreground block">business_name</label>
                    <Input
                      value={testVariables.business_name}
                      onChange={(e) => setTestVariables((p) => ({ ...p, business_name: e.target.value }))}
                      className="h-7 text-xs"
                    />
                  </div>
                  <div>
                    <label className="text-[10px] text-muted-foreground block">tone_formality</label>
                    <Input
                      value={testVariables.tone_formality}
                      onChange={(e) => setTestVariables((p) => ({ ...p, tone_formality: e.target.value }))}
                      className="h-7 text-xs"
                    />
                  </div>
                </div>

                <div className="flex items-center justify-end gap-2 pt-1">
                  <Button
                    size="sm"
                    variant="outline"
                    onClick={handleTestPreview}
                    disabled={isTesting}
                    className="h-7 text-xs gap-1.5"
                  >
                    <PlayIcon className="size-3" />
                    {isTesting ? "Renderizando..." : "Previsualizar"}
                  </Button>
                </div>
              </div>

              {/* Resultado del Preview */}
              {previewResult && (
                <div className="space-y-1.5 border-t pt-3">
                  <span className="font-semibold text-xs flex items-center gap-1.5 text-emerald-500">
                    <CheckIcon className="size-3.5" /> Prompt Renderizado Listo para LLM:
                  </span>
                  <div className="rounded-xl border bg-muted/40 p-3 font-mono text-xs leading-relaxed whitespace-pre-wrap">
                    {previewResult}
                  </div>
                </div>
              )}
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  )
}
