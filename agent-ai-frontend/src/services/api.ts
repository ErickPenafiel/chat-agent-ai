import type {
  KnowledgeBlock,
  KnowledgeVersion,
  PromptItem,
  ConnectorItem,
  OutcomeSummary,
} from "@/types/agent"

const BASE_URL = import.meta.env.VITE_API_URL || ""

class ApiService {
  private token: string | null = null

  setAuthToken(token: string | null) {
    this.token = token
  }

  private async request<T>(
    endpoint: string,
    options: RequestInit = {}
  ): Promise<T> {
    const headers: Record<string, string> = {
      "Content-Type": "application/json",
      ...(options.headers as Record<string, string>),
    }

    if (this.token) {
      headers["Authorization"] = `Bearer ${this.token}`
    }

    const response = await fetch(`${BASE_URL}${endpoint}`, {
      ...options,
      headers,
    })

    if (!response.ok) {
      const errorText = await response.text()
      let parsed = errorText
      try {
        const json = JSON.parse(errorText)
        parsed = json.detail || json.message || errorText
      } catch {
        // fallback to errorText
      }
      throw new Error(`API ${response.status}: ${parsed}`)
    }

    if (response.status === 204) {
      return {} as T
    }

    return response.json()
  }

  // Health
  async getHealth(): Promise<{ status: string; business?: string }> {
    return this.request<{ status: string; business?: string }>("/health")
  }

  // Knowledge Blocks
  async getKnowledgeBlocks(params?: {
    intent?: string
    category?: string
    status?: string
    q?: string
  }): Promise<KnowledgeBlock[]> {
    const query = new URLSearchParams()
    if (params?.intent) query.set("intent", params.intent)
    if (params?.category) query.set("category", params.category)
    if (params?.status) query.set("status", params.status)
    if (params?.q) query.set("q", params.q)

    const qs = query.toString() ? `?${query.toString()}` : ""
    return this.request<KnowledgeBlock[]>(`/knowledge-blocks${qs}`)
  }

  async getKnowledgeBlock(id: number): Promise<KnowledgeBlock> {
    return this.request<KnowledgeBlock>(`/knowledge-blocks/${id}`)
  }

  async createKnowledgeBlock(
    block: Partial<KnowledgeBlock>
  ): Promise<KnowledgeBlock> {
    return this.request<KnowledgeBlock>("/knowledge-blocks", {
      method: "POST",
      body: JSON.stringify(block),
    })
  }

  async updateKnowledgeBlock(
    id: number,
    block: Partial<KnowledgeBlock> & { note?: string }
  ): Promise<KnowledgeBlock> {
    return this.request<KnowledgeBlock>(`/knowledge-blocks/${id}`, {
      method: "PUT",
      body: JSON.stringify(block),
    })
  }

  async deleteKnowledgeBlock(id: number): Promise<void> {
    await this.request<void>(`/knowledge-blocks/${id}`, {
      method: "DELETE",
    })
  }

  async getKnowledgeVersions(id: number): Promise<KnowledgeVersion[]> {
    return this.request<KnowledgeVersion[]>(`/knowledge-blocks/${id}/versions`)
  }

  async getKnowledgeOrphans(): Promise<
    Array<{ id: number; title: string; problems: string[] }>
  > {
    return this.request<
      Array<{ id: number; title: string; problems: string[] }>
    >("/knowledge-blocks/orphans")
  }

  // Prompts
  async getPrompts(): Promise<PromptItem[]> {
    return this.request<PromptItem[]>("/prompts")
  }

  async getPromptVariables(): Promise<Record<string, string[]>> {
    return this.request<Record<string, string[]>>("/prompts/variables")
  }

  async previewPrompt(
    name: string,
    variables: Record<string, unknown>
  ): Promise<{ rendered: string }> {
    return this.request<{ rendered: string }>(`/prompts/${name}/preview`, {
      method: "POST",
      body: JSON.stringify({ variables }),
    })
  }

  async updatePrompt(
    name: string,
    text: string
  ): Promise<{ name: string; text: string }> {
    return this.request<{ name: string; text: string }>(`/prompts/${name}`, {
      method: "PUT",
      body: JSON.stringify({ text }),
    })
  }

  // Connectors
  async getConnectors(): Promise<ConnectorItem[]> {
    return this.request<ConnectorItem[]>("/connectors")
  }

  async getConnectorHealth(name: string): Promise<{ status: string; latency_ms?: number }> {
    return this.request<{ status: string; latency_ms?: number }>(
      `/connectors/${name}/health`
    )
  }

  // Evaluation
  async getOutcomesSummary(): Promise<OutcomeSummary> {
    return this.request<OutcomeSummary>("/evaluation/outcomes/summary")
  }

  async getEvaluationProposals(): Promise<
    Array<{ id: number; title: string; rationale: string; status: string }>
  > {
    return this.request<
      Array<{ id: number; title: string; rationale: string; status: string }>
    >("/evaluation/proposals")
  }

  // Web Channel Chat Playground
  async sendWebMessage(
    userId: string,
    text: string
  ): Promise<{
    processed: number
    replies: string[]
    actions?: Array<{
      intent?: string
      detected_issue?: string | null
      retrieved_blocks?: Array<{ id: number; title: string; category?: string }>
      connectors?: Array<{ id: string; found: boolean }>
      handoff?: boolean
      reply_mode?: string
      capture?: Record<string, unknown>
      capture_done?: boolean
      provider?: string | null
      model?: string | null
      verification?: string | null
      unsupported_claims?: string[]
    }>
  }> {
    return this.request<{
      processed: number
      replies: string[]
      actions?: Array<{
        intent?: string
        detected_issue?: string | null
        retrieved_blocks?: Array<{ id: number; title: string; category?: string }>
        connectors?: Array<{ id: string; found: boolean }>
        handoff?: boolean
        reply_mode?: string
        capture?: Record<string, unknown>
        capture_done?: boolean
        provider?: string | null
        model?: string | null
        verification?: string | null
        unsupported_claims?: string[]
      }>
    }>("/channels/web/webhook", {
      method: "POST",
      body: JSON.stringify({ user_id: userId, text }),
    })
  }


  async getWebOutbox(userId: string): Promise<Array<{ type: string; text?: string; url?: string }>> {
    return this.request<Array<{ type: string; text?: string; url?: string }>>(
      `/channels/web/outbox/${userId}`
    )
  }
}

export const api = new ApiService()
