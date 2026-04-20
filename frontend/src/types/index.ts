export interface GraphNode {
  id: string
  name: string
  type: 'L1' | 'L2' | 'L3'
  properties: Record<string, unknown>
}

export interface GraphEdge {
  from_: string
  to: string
  type: string
}

export interface QueryRequest {
  battery_model: string
  context: string[]
  debug: boolean
  mode?: 'local' | 'global'
}

export interface QueryResponse {
  code: number
  message: string
  data: {
    steps?: DisassemblyStep[]
    response?: string
    mode?: 'local' | 'global'
    trace?: QueryTrace
  }
}

export interface DisassemblyStep {
  id: number
  component: string
  component_name?: string
  action: string
  tool: string | string[]
  evidence: string[]
  confidence: number
  safety_level?: number
  h_score?: number
  s_score?: number
  as_score?: number
  human_loss?: number
  robot_loss?: number
  loss_diff?: number
  assignee?: 'human' | 'robot'
  time_seconds?: number
}

export interface QueryTrace {
  rewritten_queries: string[]
  retrieval_paths: string[]
  evidence_count: number
  iteration_count: number
  timing: Record<string, number>
  retrieval_nodes?: number
  all_components_count?: number
  all_relations_count?: number
}

export interface SequenceResponse {
  battery_model: string
  steps: SequenceStep[]
  parallel_groups: string[][]
  total_time_seconds: number
  cycle_count: number
}

export interface SequenceStep {
  step: number
  component: string
  component_name: string
  time_seconds: number
  tool_required: string[]
  safety_level: number
  assignee?: 'human' | 'robot'
}

export interface L1ComponentInput {
  name: string
  battery_model: string
  tool_required: string[]
  safety_level: number
  precedence: string[]
}

export interface L3TermInput {
  terms: Array<{
    term_id: string
    definition: string
    units: string
  }>
}

export interface Config {
  mtm: {
    tool_switch_default: number
    position_default: number
    mtm_base_seconds: number
  }
  as: {
    h_weights: number[]
    s_weights: number[]
  }
  threshold: {
    robot_threshold: number
    human_threshold: number
  }
  cost: {
    cost_decision_enabled: boolean
    robot_cost_default: number
    human_cost_default: number
    loss_cost_enabled: boolean
  }
  parallel: {
    parallel_level: number
  }
  time_coefficient: number
  llm: {
    temperature: number
    max_tokens: number
  }
  rag: {
    top_k: number
    similarity_threshold: number
    retrieval_depth: number
  }
}
