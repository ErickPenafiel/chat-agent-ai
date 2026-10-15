import * as React from "react"
import { motion, AnimatePresence } from "framer-motion"
import {
  SearchIcon,
  FilterIcon,
  PlusIcon,
  AlertCircleIcon,
  HelpCircleIcon,
  ListOrderedIcon,
  ClockIcon,
  XIcon,
  EditIcon,
  Trash2Icon,
  CopyIcon,
  UploadIcon,
  HistoryIcon,
  FileSpreadsheetIcon,
  FileJsonIcon,
} from "lucide-react"
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { toast } from "sonner"
import type { KnowledgeBlock, KnowledgeVersion } from "@/types/agent"
import { mockKnowledgeBlocks } from "@/services/mockData"
import { api } from "@/services/api"

interface KnowledgeBaseViewProps {
  backendOnline: boolean
}

export function KnowledgeBaseView({ backendOnline }: KnowledgeBaseViewProps) {
  const [blocks, setBlocks] = React.useState<KnowledgeBlock[]>(mockKnowledgeBlocks)
  const [search, setSearch] = React.useState("")
  const [selectedCategory, setSelectedCategory] = React.useState<string>("all")
  const [selectedBlock, setSelectedBlock] = React.useState<KnowledgeBlock | null>(null)
  const [loading, setLoading] = React.useState(false)
  const [orphanAlerts, setOrphanAlerts] = React.useState<number>(0)
  const [showOrphansOnly, setShowOrphansOnly] = React.useState(false)

  // Modales
  const [isCreateOpen, setIsCreateOpen] = React.useState(false)
  const [isEditOpen, setIsEditOpen] = React.useState(false)
  const [isDeleteOpen, setIsDeleteOpen] = React.useState(false)
  const [blockToEdit, setBlockToEdit] = React.useState<KnowledgeBlock | null>(null)
  const [blockToDelete, setBlockToDelete] = React.useState<KnowledgeBlock | null>(null)
  const [isSaving, setIsSaving] = React.useState(false)

  // Versiones
  const [blockVersions, setBlockVersions] = React.useState<KnowledgeVersion[]>([])
  const [loadingVersions, setLoadingVersions] = React.useState(false)
  const [activeTab, setActiveTab] = React.useState<"content" | "versions">("content")

  // Estado formulario de creación/edición
  const [formData, setFormData] = React.useState({
    title: "",
    content: "",
    category: "products",
    intents: "info, sales",
    keywords: "",
    example_questions: "",
    status: "published" as "published" | "draft" | "archived",
    note: "",
  })

  const fileInputRef = React.useRef<HTMLInputElement>(null)

  // Carga inicial
  React.useEffect(() => {
    let active = true
    if (backendOnline) {
      Promise.all([
        api.getKnowledgeBlocks().catch(() => mockKnowledgeBlocks),
        api.getKnowledgeOrphans().catch(() => []),
      ])
        .then(([fetchedBlocks, orphans]) => {
          if (!active) return
          if (fetchedBlocks && fetchedBlocks.length > 0) {
            setBlocks(fetchedBlocks)
          }
          if (orphans) {
            setOrphanAlerts(orphans.length)
          }
        })
        .finally(() => {
          if (active) setLoading(false)
        })
    }
    return () => {
      active = false
    }
  }, [backendOnline])

  const categories = ["all", "products", "subscription", "shipping", "payments"]

  const filteredBlocks = blocks.filter((b) => {
    const matchesSearch =
      b.title.toLowerCase().includes(search.toLowerCase()) ||
      b.content.toLowerCase().includes(search.toLowerCase()) ||
      b.keywords.some((k) => k.toLowerCase().includes(search.toLowerCase())) ||
      b.intents.some((i) => i.toLowerCase().includes(search.toLowerCase()))

    const matchesCat =
      selectedCategory === "all" || b.category === selectedCategory

    const matchesOrphan =
      !showOrphansOnly || (b.intents.length === 0 || b.intents.includes("none"))

    return matchesSearch && matchesCat && matchesOrphan
  })

  // Abrir Modal de Creación
  const openCreateModal = () => {
    setFormData({
      title: "",
      content: "",
      category: "products",
      intents: "info, sales",
      keywords: "",
      example_questions: "",
      status: "published",
      note: "",
    })
    setIsCreateOpen(true)
  }

  // Abrir Modal de Edición
  const openEditModal = (block: KnowledgeBlock, e?: React.MouseEvent) => {
    if (e) e.stopPropagation()
    setBlockToEdit(block)
    setFormData({
      title: block.title,
      content: block.content,
      category: block.category || "products",
      intents: block.intents.join(", "),
      keywords: block.keywords.join(", "),
      example_questions: (block.example_questions || []).join("\n"),
      status: block.status,
      note: "",
    })
    setIsEditOpen(true)
  }

  // Confirmar Eliminación
  const openDeleteModal = (block: KnowledgeBlock, e?: React.MouseEvent) => {
    if (e) e.stopPropagation()
    setBlockToDelete(block)
    setIsDeleteOpen(true)
  }

  // Duplicar Bloque
  const handleDuplicateBlock = (e: React.MouseEvent, block: KnowledgeBlock) => {
    e.stopPropagation()
    const duplicate: KnowledgeBlock = {
      ...block,
      id: Number(`${block.id}01`),
      title: `${block.title} (Copia)`,
      version: 1,
      updated_at: block.updated_at,
    }
    setBlocks((prev) => [duplicate, ...prev])
    toast.success(`Bloque "${block.title}" duplicado con éxito`)
  }

  // Guardar Creación
  const handleCreateBlock = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!formData.title.trim() || !formData.content.trim()) {
      toast.error("Por favor completa el título y el contenido")
      return
    }

    setIsSaving(true)
    const intentsList = formData.intents
      .split(",")
      .map((s) => s.trim())
      .filter(Boolean)
    const keywordsList = formData.keywords
      .split(",")
      .map((s) => s.trim())
      .filter(Boolean)
    const questionsList = formData.example_questions
      .split("\n")
      .map((s) => s.trim())
      .filter(Boolean)

    const payload: Partial<KnowledgeBlock> = {
      title: formData.title.trim(),
      content: formData.content.trim(),
      category: formData.category,
      intents: intentsList.length > 0 ? intentsList : ["info"],
      keywords: keywordsList,
      example_questions: questionsList,
      language: "es",
      status: formData.status,
      attachments: [],
      steps: [],
      meta: {},
    }

    try {
      let created: KnowledgeBlock
      if (backendOnline) {
        created = await api.createKnowledgeBlock(payload)
      } else {
        created = {
          id: Date.now(),
          title: payload.title!,
          content: payload.content!,
          category: payload.category || null,
          intents: payload.intents || ["info"],
          language: "es",
          status: payload.status || "published",
          version: 1,
          keywords: payload.keywords || [],
          example_questions: payload.example_questions || [],
          attachments: [],
          steps: [],
          meta: {},
          created_at: new Date().toISOString(),
          updated_at: new Date().toISOString(),
        }
      }
      setBlocks((prev) => [created, ...prev])
      setIsCreateOpen(false)
      toast.success("Nuevo bloque de conocimiento creado exitosamente")
    } catch (err) {
      toast.error(`Error al crear bloque: ${err instanceof Error ? err.message : "Desconocido"}`)
    } finally {
      setIsSaving(false)
    }
  }

  // Guardar Edición
  const handleUpdateBlock = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!blockToEdit) return

    setIsSaving(true)
    const intentsList = formData.intents
      .split(",")
      .map((s) => s.trim())
      .filter(Boolean)
    const keywordsList = formData.keywords
      .split(",")
      .map((s) => s.trim())
      .filter(Boolean)
    const questionsList = formData.example_questions
      .split("\n")
      .map((s) => s.trim())
      .filter(Boolean)

    const updatedData: Partial<KnowledgeBlock> & { note?: string } = {
      title: formData.title.trim(),
      content: formData.content.trim(),
      category: formData.category,
      intents: intentsList,
      keywords: keywordsList,
      example_questions: questionsList,
      status: formData.status,
      note: formData.note.trim() || undefined,
    }

    try {
      let result: KnowledgeBlock
      if (backendOnline) {
        result = await api.updateKnowledgeBlock(blockToEdit.id, updatedData)
      } else {
        result = {
          ...blockToEdit,
          ...updatedData,
          version: blockToEdit.version + 1,
          updated_at: new Date().toISOString(),
        } as KnowledgeBlock
      }

      setBlocks((prev) => prev.map((b) => (b.id === blockToEdit.id ? result : b)))
      if (selectedBlock?.id === blockToEdit.id) {
        setSelectedBlock(result)
      }
      setIsEditOpen(false)
      toast.success(`Bloque "${result.title}" actualizado (v${result.version})`)
    } catch (err) {
      toast.error(`Error al actualizar bloque: ${err instanceof Error ? err.message : "Desconocido"}`)
    } finally {
      setIsSaving(false)
    }
  }

  // Eliminar Bloque
  const handleDeleteBlock = async () => {
    if (!blockToDelete) return

    setIsSaving(true)
    try {
      if (backendOnline) {
        await api.deleteKnowledgeBlock(blockToDelete.id)
      }
      setBlocks((prev) => prev.filter((b) => b.id !== blockToDelete.id))
      if (selectedBlock?.id === blockToDelete.id) {
        setSelectedBlock(null)
      }
      setIsDeleteOpen(false)
      toast.success(`Bloque "${blockToDelete.title}" eliminado`)
    } catch (err) {
      toast.error(`Error al eliminar bloque: ${err instanceof Error ? err.message : "Desconocido"}`)
    } finally {
      setIsSaving(false)
    }
  }

  // Cargar Historial de Versiones
  const loadVersions = async (block: KnowledgeBlock) => {
    setActiveTab("versions")
    setLoadingVersions(true)
    try {
      if (backendOnline) {
        const v = await api.getKnowledgeVersions(block.id)
        setBlockVersions(v)
      } else {
        await new Promise((r) => setTimeout(r, 300))
        setBlockVersions([
          {
            version: block.version,
            author: "Sistema",
            note: "Versión actual activa",
            created_at: block.updated_at,
            snapshot: {
              title: block.title,
              content: block.content,
            },
          },
        ])
      }
    } catch {
      toast.info("Sin versiones históricas adicionales registradas")
    } finally {
      setLoadingVersions(false)
    }
  }

  // Exportar a JSON
  const handleExportJSON = () => {
    const dataStr = "data:text/json;charset=utf-8," + encodeURIComponent(JSON.stringify(blocks, null, 2))
    const downloadAnchor = document.createElement("a")
    downloadAnchor.setAttribute("href", dataStr)
    downloadAnchor.setAttribute("download", `knowledge_base_${new Date().toISOString().slice(0, 10)}.json`)
    document.body.appendChild(downloadAnchor)
    downloadAnchor.click()
    downloadAnchor.remove()
    toast.success("Base de conocimiento exportada como JSON")
  }

  // Exportar a CSV
  const handleExportCSV = () => {
    const headers = ["ID", "Title", "Category", "Intents", "Status", "Content"]
    const rows = blocks.map((b) => [
      b.id,
      `"${b.title.replace(/"/g, '""')}"`,
      b.category || "",
      `"${b.intents.join(", ")}"`,
      b.status,
      `"${b.content.replace(/"/g, '""')}"`,
    ])
    const csvContent = "data:text/csv;charset=utf-8," + [headers.join(","), ...rows.map((e) => e.join(","))].join("\n")
    const encodedUri = encodeURI(csvContent)
    const link = document.createElement("a")
    link.setAttribute("href", encodedUri)
    link.setAttribute("download", `knowledge_base_${new Date().toISOString().slice(0, 10)}.csv`)
    document.body.appendChild(link)
    link.click()
    link.remove()
    toast.success("Base de conocimiento exportada como CSV")
  }

  // Importar desde archivo JSON
  const handleImportJSON = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (!file) return

    const reader = new FileReader()
    reader.onload = (event) => {
      try {
        const parsed = JSON.parse(event.target?.result as string)
        if (Array.isArray(parsed) && parsed.length > 0) {
          setBlocks((prev) => {
            const existingIds = new Set(prev.map((b) => b.id))
            const newOnes = parsed.filter((p) => !existingIds.has(p.id))
            return [...newOnes, ...prev]
          })
          toast.success(`${parsed.length} bloques importados exitosamente`)
        } else {
          toast.error("El archivo JSON no contiene un arreglo válido de bloques")
        }
      } catch {
        toast.error("Formato JSON inválido")
      }
    }
    reader.readAsText(file)
    if (fileInputRef.current) fileInputRef.current.value = ""
  }

  return (
    <div className="flex flex-col gap-6">
      {/* Encabezado y Acciones */}
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <div className="flex items-center gap-2">
            <h2 className="text-2xl font-bold tracking-tight">Base de Conocimiento (KB)</h2>
            <Badge variant="outline" className="font-mono text-xs">
              {blocks.length} Bloques
            </Badge>
          </div>
          <p className="text-sm text-muted-foreground mt-0.5">
            Bloques semánticos consultados por el agente para responder preguntas de clientes con citas fácticas.
          </p>
        </div>

        <div className="flex items-center gap-2 flex-wrap">
          {orphanAlerts > 0 && (
            <Button
              variant={showOrphansOnly ? "destructive" : "outline"}
              size="sm"
              onClick={() => setShowOrphansOnly((prev) => !prev)}
              className="gap-1.5 text-xs h-8"
            >
              <AlertCircleIcon className="size-3.5" />
              {orphanAlerts} Huérfanos
            </Button>
          )}

          <input
            type="file"
            accept=".json"
            ref={fileInputRef}
            onChange={handleImportJSON}
            className="hidden"
          />

          <Button
            variant="outline"
            size="sm"
            onClick={() => fileInputRef.current?.click()}
            className="gap-1.5 text-xs h-8"
            title="Importar bloques desde archivo JSON"
          >
            <UploadIcon className="size-3.5" />
            Importar
          </Button>

          <Button
            variant="outline"
            size="sm"
            onClick={handleExportJSON}
            className="gap-1.5 text-xs h-8"
            title="Exportar bloques en formato JSON"
          >
            <FileJsonIcon className="size-3.5" />
            JSON
          </Button>

          <Button
            variant="outline"
            size="sm"
            onClick={handleExportCSV}
            className="gap-1.5 text-xs h-8"
            title="Exportar bloques en formato CSV"
          >
            <FileSpreadsheetIcon className="size-3.5" />
            CSV
          </Button>

          <Button
            size="sm"
            onClick={openCreateModal}
            className="gap-1.5 shadow-xs h-8"
          >
            <PlusIcon className="size-4" />
            Nuevo Bloque
          </Button>
        </div>
      </div>

      {/* Barra de Filtros y Búsqueda */}
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between rounded-xl border bg-card p-3 shadow-xs">
        <div className="relative flex-1 max-w-md">
          <SearchIcon className="absolute left-3 top-1/2 -translate-y-1/2 size-4 text-muted-foreground" />
          <Input
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Buscar por título, contenido, intención o palabra clave..."
            className="pl-9 h-9 text-sm"
          />
        </div>

        <div className="flex items-center gap-1.5 overflow-x-auto text-xs">
          <span className="text-muted-foreground flex items-center gap-1 mr-1">
            <FilterIcon className="size-3" /> Categoría:
          </span>
          {categories.map((cat) => (
            <Button
              key={cat}
              variant={selectedCategory === cat ? "default" : "outline"}
              size="sm"
              onClick={() => setSelectedCategory(cat)}
              className="h-7 text-xs capitalize"
            >
              {cat === "all" ? "Todas" : cat}
            </Button>
          ))}
        </div>
      </div>

      {/* Grid de Bloques con Framer Motion */}
      {loading ? (
        <div className="text-center py-12 text-muted-foreground text-sm">
          Cargando bloques de la base de conocimiento...
        </div>
      ) : filteredBlocks.length === 0 ? (
        <div className="text-center py-16 border rounded-2xl bg-card/40 space-y-3">
          <p className="text-sm text-muted-foreground">
            No se encontraron bloques con los filtros aplicados.
          </p>
          <Button variant="outline" size="sm" onClick={() => { setSearch(""); setSelectedCategory("all"); setShowOrphansOnly(false); }}>
            Limpiar filtros
          </Button>
        </div>
      ) : (
        <motion.div
          initial="hidden"
          animate="visible"
          variants={{
            hidden: { opacity: 0 },
            visible: { opacity: 1, transition: { staggerChildren: 0.05 } },
          }}
          className="grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-3"
        >
          {filteredBlocks.map((block) => (
            <motion.div
              key={block.id}
              variants={{
                hidden: { opacity: 0, y: 12 },
                visible: { opacity: 1, y: 0 },
              }}
              whileHover={{ y: -3, transition: { duration: 0.2 } }}
            >
              <Card
                onClick={() => {
                  setSelectedBlock(block)
                  setActiveTab("content")
                }}
                className="h-full cursor-pointer hover:border-primary/50 transition-all shadow-xs flex flex-col justify-between group"
              >
                <CardHeader className="pb-3">
                  <div className="flex items-start justify-between gap-2">
                    <CardTitle className="text-base font-semibold leading-tight line-clamp-1">
                      {block.title}
                    </CardTitle>
                    <div className="flex items-center gap-1 shrink-0">
                      <Badge variant="outline" className="text-[10px] uppercase font-mono">
                        v{block.version}
                      </Badge>
                    </div>
                  </div>
                  <div className="flex flex-wrap items-center gap-1 mt-1.5">
                    {block.category && (
                      <Badge variant="secondary" className="text-[10px] capitalize">
                        {block.category}
                      </Badge>
                    )}
                    {block.intents.map((intent) => (
                      <Badge
                        key={intent}
                        variant="outline"
                        className="text-[10px] font-mono text-muted-foreground"
                      >
                        #{intent}
                      </Badge>
                    ))}
                  </div>
                </CardHeader>
                <CardContent className="space-y-3 text-xs flex-1 flex flex-col justify-between">
                  <p className="text-muted-foreground line-clamp-3 leading-relaxed">
                    {block.content}
                  </p>

                  <div className="pt-2 border-t flex items-center justify-between text-[11px] text-muted-foreground">
                    <div className="flex items-center gap-2">
                      {block.steps && block.steps.length > 0 && (
                        <span className="flex items-center gap-0.5">
                          <ListOrderedIcon className="size-3" /> {block.steps.length} pasos
                        </span>
                      )}
                      {block.example_questions && block.example_questions.length > 0 && (
                        <span className="flex items-center gap-0.5">
                          <HelpCircleIcon className="size-3" /> {block.example_questions.length} preg.
                        </span>
                      )}
                    </div>

                    <div className="flex items-center gap-1">
                      <Button
                        variant="ghost"
                        size="icon"
                        className="size-6 text-muted-foreground hover:text-foreground"
                        onClick={(e) => handleDuplicateBlock(e, block)}
                        title="Duplicar bloque"
                      >
                        <CopyIcon className="size-3" />
                      </Button>
                      <Button
                        variant="ghost"
                        size="icon"
                        className="size-6 text-muted-foreground hover:text-foreground"
                        onClick={(e) => openEditModal(block, e)}
                        title="Editar bloque"
                      >
                        <EditIcon className="size-3" />
                      </Button>
                      <Button
                        variant="ghost"
                        size="icon"
                        className="size-6 text-destructive/70 hover:text-destructive"
                        onClick={(e) => openDeleteModal(block, e)}
                        title="Eliminar bloque"
                      >
                        <Trash2Icon className="size-3" />
                      </Button>
                    </div>
                  </div>
                </CardContent>
              </Card>
            </motion.div>
          ))}
        </motion.div>
      )}

      {/* Modal / Drawer de Detalle del Bloque */}
      <AnimatePresence>
        {selectedBlock && (
          <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-background/80 backdrop-blur-xs">
            <motion.div
              initial={{ opacity: 0, scale: 0.95, y: 10 }}
              animate={{ opacity: 1, scale: 1, y: 0 }}
              exit={{ opacity: 0, scale: 0.95, y: 10 }}
              transition={{ duration: 0.2 }}
              className="relative w-full max-w-2xl max-h-[85vh] overflow-y-auto rounded-2xl border bg-card p-6 shadow-xl space-y-5"
            >
              <div className="flex items-start justify-between gap-4 border-b pb-4">
                <div>
                  <div className="flex items-center gap-2">
                    <h3 className="text-xl font-bold leading-tight">{selectedBlock.title}</h3>
                    <Badge variant="outline" className="font-mono text-xs">
                      v{selectedBlock.version}
                    </Badge>
                  </div>
                  <div className="flex items-center gap-2 mt-1 text-xs text-muted-foreground">
                    <span>Categoría: <strong>{selectedBlock.category || "General"}</strong></span>
                    <span>•</span>
                    <span>Idioma: <strong>{selectedBlock.language}</strong></span>
                    <span>•</span>
                    <span className="capitalize text-emerald-500 font-medium">
                      {selectedBlock.status}
                    </span>
                  </div>
                </div>
                <div className="flex items-center gap-1.5">
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => openEditModal(selectedBlock)}
                    className="h-8 gap-1 text-xs"
                  >
                    <EditIcon className="size-3" />
                    Editar
                  </Button>
                  <Button
                    variant="ghost"
                    size="icon"
                    onClick={() => setSelectedBlock(null)}
                    className="size-8 rounded-full"
                  >
                    <XIcon className="size-4" />
                  </Button>
                </div>
              </div>

              {/* Tabs Contenido vs Versiones */}
              <div className="flex items-center gap-2 border-b pb-2">
                <Button
                  size="sm"
                  variant={activeTab === "content" ? "default" : "ghost"}
                  onClick={() => setActiveTab("content")}
                  className="h-7 text-xs"
                >
                  Contenido Semántico
                </Button>
                <Button
                  size="sm"
                  variant={activeTab === "versions" ? "default" : "ghost"}
                  onClick={() => loadVersions(selectedBlock)}
                  className="h-7 text-xs gap-1"
                >
                  <HistoryIcon className="size-3" />
                  Historial de Versiones
                </Button>
              </div>

              {activeTab === "content" ? (
                <div className="space-y-4">
                  <div>
                    <h4 className="text-xs font-semibold uppercase tracking-wider text-muted-foreground mb-1.5">
                      Contenido Semántico:
                    </h4>
                    <div className="rounded-xl border bg-muted/30 p-4 text-sm leading-relaxed whitespace-pre-wrap font-mono text-xs">
                      {selectedBlock.content}
                    </div>
                  </div>

                  {selectedBlock.keywords && selectedBlock.keywords.length > 0 && (
                    <div>
                      <h4 className="text-xs font-semibold uppercase tracking-wider text-muted-foreground mb-1.5">
                        Palabras Clave (Keywords):
                      </h4>
                      <div className="flex flex-wrap gap-1.5">
                        {selectedBlock.keywords.map((k, i) => (
                          <Badge key={i} variant="secondary" className="text-xs">
                            {k}
                          </Badge>
                        ))}
                      </div>
                    </div>
                  )}

                  {selectedBlock.steps && selectedBlock.steps.length > 0 && (
                    <div>
                      <h4 className="text-xs font-semibold uppercase tracking-wider text-muted-foreground mb-1.5">
                        Pasos Guiados:
                      </h4>
                      <div className="space-y-1.5">
                        {selectedBlock.steps.map((st, i) => (
                          <div key={i} className="flex items-start gap-2 text-xs bg-muted/40 p-2 rounded-lg border">
                            <span className="flex size-4 shrink-0 items-center justify-center rounded-full bg-primary text-[10px] text-primary-foreground font-bold">
                              {i + 1}
                            </span>
                            <span>{st.text}</span>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}

                  {selectedBlock.example_questions && selectedBlock.example_questions.length > 0 && (
                    <div>
                      <h4 className="text-xs font-semibold uppercase tracking-wider text-muted-foreground mb-1.5">
                        Preguntas de Ejemplo para el Retriever:
                      </h4>
                      <div className="flex flex-wrap gap-1.5">
                        {selectedBlock.example_questions.map((q, i) => (
                          <Badge key={i} variant="secondary" className="text-xs py-1">
                            {q}
                          </Badge>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              ) : (
                <div className="space-y-3">
                  {loadingVersions ? (
                    <div className="text-center py-6 text-xs text-muted-foreground">
                      Cargando versiones históricas...
                    </div>
                  ) : blockVersions.length === 0 ? (
                    <div className="text-center py-6 text-xs text-muted-foreground">
                      No hay versiones anteriores registradas.
                    </div>
                  ) : (
                    <div className="space-y-2">
                      {blockVersions.map((v) => (
                        <div key={v.version} className="p-3 rounded-xl border bg-muted/20 space-y-1.5 text-xs">
                          <div className="flex items-center justify-between">
                            <span className="font-bold font-mono">Versión {v.version}</span>
                            <span className="text-[10px] text-muted-foreground">
                              {new Date(v.created_at).toLocaleString()}
                            </span>
                          </div>
                          {v.note && (
                            <p className="text-muted-foreground italic">Nota: {v.note}</p>
                          )}
                          <p className="line-clamp-2 text-muted-foreground text-[11px] font-mono">
                            {v.snapshot?.content || "Sin contenido registrado"}
                          </p>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              )}

              <div className="flex items-center justify-between border-t pt-4 text-xs text-muted-foreground">
                <span className="flex items-center gap-1">
                  <ClockIcon className="size-3.5" /> Actualizado: {new Date(selectedBlock.updated_at).toLocaleDateString()}
                </span>
                <Button size="sm" onClick={() => setSelectedBlock(null)}>
                  Cerrar
                </Button>
              </div>
            </motion.div>
          </div>
        )}

        {/* Modal de Creación */}
        {isCreateOpen && (
          <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-background/80 backdrop-blur-xs">
            <motion.div
              initial={{ opacity: 0, scale: 0.95, y: 10 }}
              animate={{ opacity: 1, scale: 1, y: 0 }}
              exit={{ opacity: 0, scale: 0.95, y: 10 }}
              transition={{ duration: 0.2 }}
              className="relative w-full max-w-xl max-h-[85vh] overflow-y-auto rounded-2xl border bg-card p-6 shadow-xl space-y-4"
            >
              <div className="flex items-center justify-between border-b pb-3">
                <div>
                  <h3 className="text-lg font-bold">Nuevo Bloque de Conocimiento</h3>
                  <p className="text-xs text-muted-foreground">
                    Define la información que el agente utilizará para responder consultas
                  </p>
                </div>
                <Button
                  variant="ghost"
                  size="icon"
                  onClick={() => setIsCreateOpen(false)}
                  className="size-8 rounded-full"
                >
                  <XIcon className="size-4" />
                </Button>
              </div>

              <form onSubmit={handleCreateBlock} className="space-y-4 text-xs">
                <div>
                  <label className="font-semibold block mb-1">Título del Bloque *</label>
                  <Input
                    required
                    value={formData.title}
                    onChange={(e) => setFormData((prev) => ({ ...prev, title: e.target.value }))}
                    placeholder="Ej. Métodos de Pago Aceptados"
                    className="h-9 text-xs"
                  />
                </div>

                <div className="grid grid-cols-2 gap-3">
                  <div>
                    <label className="font-semibold block mb-1">Categoría</label>
                    <select
                      value={formData.category}
                      onChange={(e) => setFormData((prev) => ({ ...prev, category: e.target.value }))}
                      className="w-full h-9 rounded-md border bg-background px-3 text-xs"
                    >
                      <option value="products">products</option>
                      <option value="subscription">subscription</option>
                      <option value="shipping">shipping</option>
                      <option value="payments">payments</option>
                    </select>
                  </div>
                  <div>
                    <label className="font-semibold block mb-1">Intenciones (separadas por coma)</label>
                    <Input
                      value={formData.intents}
                      onChange={(e) => setFormData((prev) => ({ ...prev, intents: e.target.value }))}
                      placeholder="info, sales, support"
                      className="h-9 text-xs"
                    />
                  </div>
                </div>

                <div>
                  <label className="font-semibold block mb-1">Contenido Semántico *</label>
                  <textarea
                    required
                    rows={4}
                    value={formData.content}
                    onChange={(e) => setFormData((prev) => ({ ...prev, content: e.target.value }))}
                    placeholder="Escribe la información fáctica y concisa que el agente debe comunicar..."
                    className="w-full rounded-md border bg-background p-2.5 text-xs focus:outline-hidden focus:ring-2 focus:ring-primary/50"
                  />
                </div>

                <div>
                  <label className="font-semibold block mb-1">Palabras Clave (keywords)</label>
                  <Input
                    value={formData.keywords}
                    onChange={(e) => setFormData((prev) => ({ ...prev, keywords: e.target.value }))}
                    placeholder="café, pago, tarjeta, visa (separadas por coma)"
                    className="h-9 text-xs"
                  />
                </div>

                <div>
                  <label className="font-semibold block mb-1">Preguntas de Ejemplo (una por línea)</label>
                  <textarea
                    rows={2}
                    value={formData.example_questions}
                    onChange={(e) => setFormData((prev) => ({ ...prev, example_questions: e.target.value }))}
                    placeholder="¿Aceptan tarjeta?&#10;¿Cómo puedo abonar?"
                    className="w-full rounded-md border bg-background p-2.5 text-xs focus:outline-hidden focus:ring-2 focus:ring-primary/50"
                  />
                </div>

                <div className="flex items-center justify-end gap-2 pt-2 border-t">
                  <Button
                    type="button"
                    variant="outline"
                    size="sm"
                    onClick={() => setIsCreateOpen(false)}
                    disabled={isSaving}
                  >
                    Cancelar
                  </Button>
                  <Button type="submit" size="sm" disabled={isSaving}>
                    {isSaving ? "Guardando..." : "Crear Bloque"}
                  </Button>
                </div>
              </form>
            </motion.div>
          </div>
        )}

        {/* Modal de Edición */}
        {isEditOpen && blockToEdit && (
          <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-background/80 backdrop-blur-xs">
            <motion.div
              initial={{ opacity: 0, scale: 0.95, y: 10 }}
              animate={{ opacity: 1, scale: 1, y: 0 }}
              exit={{ opacity: 0, scale: 0.95, y: 10 }}
              transition={{ duration: 0.2 }}
              className="relative w-full max-w-xl max-h-[85vh] overflow-y-auto rounded-2xl border bg-card p-6 shadow-xl space-y-4"
            >
              <div className="flex items-center justify-between border-b pb-3">
                <div>
                  <h3 className="text-lg font-bold">Editar Bloque de Conocimiento</h3>
                  <p className="text-xs text-muted-foreground">
                    Modificar contenido existente (incrementará a v{blockToEdit.version + 1})
                  </p>
                </div>
                <Button
                  variant="ghost"
                  size="icon"
                  onClick={() => setIsEditOpen(false)}
                  className="size-8 rounded-full"
                >
                  <XIcon className="size-4" />
                </Button>
              </div>

              <form onSubmit={handleUpdateBlock} className="space-y-4 text-xs">
                <div>
                  <label className="font-semibold block mb-1">Título del Bloque *</label>
                  <Input
                    required
                    value={formData.title}
                    onChange={(e) => setFormData((prev) => ({ ...prev, title: e.target.value }))}
                    className="h-9 text-xs"
                  />
                </div>

                <div className="grid grid-cols-2 gap-3">
                  <div>
                    <label className="font-semibold block mb-1">Categoría</label>
                    <select
                      value={formData.category}
                      onChange={(e) => setFormData((prev) => ({ ...prev, category: e.target.value }))}
                      className="w-full h-9 rounded-md border bg-background px-3 text-xs"
                    >
                      <option value="products">products</option>
                      <option value="subscription">subscription</option>
                      <option value="shipping">shipping</option>
                      <option value="payments">payments</option>
                    </select>
                  </div>
                  <div>
                    <label className="font-semibold block mb-1">Intenciones</label>
                    <Input
                      value={formData.intents}
                      onChange={(e) => setFormData((prev) => ({ ...prev, intents: e.target.value }))}
                      className="h-9 text-xs"
                    />
                  </div>
                </div>

                <div>
                  <label className="font-semibold block mb-1">Contenido Semántico *</label>
                  <textarea
                    required
                    rows={4}
                    value={formData.content}
                    onChange={(e) => setFormData((prev) => ({ ...prev, content: e.target.value }))}
                    className="w-full rounded-md border bg-background p-2.5 text-xs focus:outline-hidden focus:ring-2 focus:ring-primary/50"
                  />
                </div>

                <div>
                  <label className="font-semibold block mb-1">Palabras Clave</label>
                  <Input
                    value={formData.keywords}
                    onChange={(e) => setFormData((prev) => ({ ...prev, keywords: e.target.value }))}
                    className="h-9 text-xs"
                  />
                </div>

                <div>
                  <label className="font-semibold block mb-1">Preguntas de Ejemplo</label>
                  <textarea
                    rows={2}
                    value={formData.example_questions}
                    onChange={(e) => setFormData((prev) => ({ ...prev, example_questions: e.target.value }))}
                    className="w-full rounded-md border bg-background p-2.5 text-xs focus:outline-hidden focus:ring-2 focus:ring-primary/50"
                  />
                </div>

                <div>
                  <label className="font-semibold block mb-1">Nota del Cambio (Opcional)</label>
                  <Input
                    value={formData.note}
                    onChange={(e) => setFormData((prev) => ({ ...prev, note: e.target.value }))}
                    placeholder="Ej. Actualización de tarifas y nuevos métodos de pago"
                    className="h-9 text-xs"
                  />
                </div>

                <div className="flex items-center justify-end gap-2 pt-2 border-t">
                  <Button
                    type="button"
                    variant="outline"
                    size="sm"
                    onClick={() => setIsEditOpen(false)}
                    disabled={isSaving}
                  >
                    Cancelar
                  </Button>
                  <Button type="submit" size="sm" disabled={isSaving}>
                    {isSaving ? "Guardando..." : "Guardar Cambios"}
                  </Button>
                </div>
              </form>
            </motion.div>
          </div>
        )}

        {/* Modal de Confirmación de Eliminación */}
        {isDeleteOpen && blockToDelete && (
          <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-background/80 backdrop-blur-xs">
            <motion.div
              initial={{ opacity: 0, scale: 0.95 }}
              animate={{ opacity: 1, scale: 1 }}
              exit={{ opacity: 0, scale: 0.95 }}
              className="relative w-full max-w-md rounded-2xl border bg-card p-6 shadow-xl space-y-4 text-xs"
            >
              <div className="flex items-center gap-3">
                <div className="flex size-10 shrink-0 items-center justify-center rounded-full bg-destructive/10 text-destructive">
                  <Trash2Icon className="size-5" />
                </div>
                <div>
                  <h3 className="text-base font-bold text-foreground">¿Eliminar este bloque?</h3>
                  <p className="text-muted-foreground mt-0.5">
                    Esta acción eliminará "{blockToDelete.title}" de la base de conocimiento del agente.
                  </p>
                </div>
              </div>

              <div className="flex items-center justify-end gap-2 pt-2 border-t">
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => setIsDeleteOpen(false)}
                  disabled={isSaving}
                >
                  Cancelar
                </Button>
                <Button
                  variant="destructive"
                  size="sm"
                  onClick={handleDeleteBlock}
                  disabled={isSaving}
                >
                  {isSaving ? "Eliminando..." : "Eliminar Definitivamente"}
                </Button>
              </div>
            </motion.div>
          </div>
        )}
      </AnimatePresence>
    </div>
  )
}
