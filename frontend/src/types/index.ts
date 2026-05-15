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
  debug: boolean
  mode?: 'local' | 'global'
}

export interface ParallelBatch {
  batch_id: number
  tasks: number[]
  start_time: number
  duration: number
}

export interface QueryResponse {
  code: number
  message: string
  data: {
    steps?: DisassemblyStep[]
    response?: string
    mode?: 'local' | 'global'
    trace?: QueryTrace
    total_time_seconds?: number
    parallel_batches?: ParallelBatch[]
    reasoning_traces?: ReasoningTrace[]
    total_feedback_iterations?: number
    final_confidence?: number
  }
}

export interface ReasoningLink {
  claim: string
  evidence_id: string
  evidence_name: string
  evidence_layer: 1 | 2 | 3
  evidence_snippet: string
  confidence: number
}

export interface StepReasoningChain {
  step_id: string
  links: ReasoningLink[]
  overall_reasoning: string
}

export interface ConfidenceInfo {
  overall: number
  grade: 'PASS' | 'WARN_CONSISTENCY' | 'FAIL_DEPTH' | 'FAIL_COVERAGE'
  evidence_coverage: number
  cross_layer_depth_score: number
  consistency: number
  method: string
}

export interface DisassemblyStep {
  id: number
  component: string
  component_name?: string
  action: string
  tool: string | string[]
  evidence: string[]
  confidence: number
  reasoning_chain?: StepReasoningChain
  confidence_info?: ConfidenceInfo
  safety_level?: number
  depends_on?: number[]
  time_seconds: number
  start_time?: number
  duration?: number
  h_score?: number
  s_score?: number
  as_score?: number
  human_loss?: number
  robot_loss?: number
  loss_diff?: number
  assignee?: 'human' | 'robot'
}

export interface ReasoningTrace {
  query: string
  iteration: number
  retrieved_nodes_count: number
  cross_layer_expansion: {
    l1_nodes?: number
    l2_nodes?: number
    l3_nodes?: number
    [key: string]: number | undefined
  }
  confidence_factors: {
    evidence_coverage: number
    cross_layer_depth: number
    consistency: number
  }
  confidence: number
  reasoning_steps: string[]
  web_results_count: number
  missing_evidence: string[]
  target_depth: number
  confidence_result: ConfidenceInfo
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
    name: string
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
