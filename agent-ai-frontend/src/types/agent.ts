export type KnowledgeStatus = "draft" | "published" | "archived"

export interface KnowledgeAttachment {
  id: string
  type: "image" | "video" | "document" | "audio"
  url: string
  alt?: string | null
}

export interface KnowledgeStep {
  text: string
  attachment_id?: string | null
}

export interface KnowledgeBlock {
  id: number
  title: string
  content: string
  intents: string[]
  category: string | null
  language: string
  status: KnowledgeStatus
  version: number
  keywords: string[]
  example_questions: string[]
  attachments: KnowledgeAttachment[]
  steps: KnowledgeStep[]
  meta: Record<string, unknown>
  created_at: string
  updated_at: string
}

export interface KnowledgeVersion {
  version: number
  author: string | null
  note: string | null
  created_at: string
  snapshot: Partial<KnowledgeBlock>
}

export interface PromptItem {
  slug?: string
  name?: string
  version?: number
  text: string
  source?: "db" | "tenant" | "default"
  available_variables?: string[]
  updated_at?: string | null
}

export interface ConnectorItem {
  name: string
  type: string
  status: "ok" | "degraded" | "error" | "mock"
  description?: string
  latency_ms?: number
}

export interface OutcomeSummary {
  total_sessions: number
  resolved: number
  escalated: number
  abandoned: number
  resolved_rate: number
  escalated_rate: number
  avg_turns?: number
}

export interface AgentActionTrace {
  intent?: string
  detected_issue?: string | null
  retrieved_blocks?: Array<{ id: number; title: string; category?: string }>
  connectors?: Array<{ id: string; found: boolean }>
  handoff?: boolean
  reply_mode?: string
  capture?: Record<string, unknown>
  capture_done?: boolean
  verification?: string | null
  unsupported_claims?: string[]
  provider?: string | null
  model?: string | null
  latency_ms?: number
  step_summary?: string[]
}

export interface ChatMessage {
  id: string
  sender: "user" | "agent" | "system"
  text: string
  timestamp: string
  intents?: string[]
  retrieved_blocks?: string[]
  escalated?: boolean
  trace?: AgentActionTrace
}

