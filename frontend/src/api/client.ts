import axios from 'axios'
import type {
  QueryRequest,
  QueryResponse,
  Config,
  GraphNode,
  GraphEdge,
  L1ComponentInput,
  L3TermInput,
} from '../types'

const api = axios.create({
  baseURL: '/api/v1',
  timeout: 300000,
})

export const graphApi = {
  getNodes: () => api.get<GraphNode[]>('/graph/nodes'),
  getNode: (id: string) => api.get(`/graph/node/${id}`),
  getRelationships: () => api.get<GraphEdge[]>('/graph/relationships'),
  search: (q: string) => api.get('/graph/search', { params: { q } }),
}

export const queryApi = {
  ask: (data: QueryRequest) => api.post<QueryResponse>('/disassembly/plan', data),
  getHistory: (limit = 10) => api.get('/query/history', { params: { limit } }),
  feedback: (data: { question: string; use_web_search: boolean }) =>
    api.post('/query/feedback', data),
  feedbackSync: (data: { question: string; use_web_search: boolean }) =>
    api.post<{ code: number; message: string; data: { answer: string; sources: any[] } }>('/query/feedback/sync', data),
}

export const batteryApi = {
  search: (q: string = '') =>
    api.get<{ code: number; message: string; data: Array<{ model: string; L1_components: number; L2_entities: number; L3_terms: number }> }>('/battery-models', { params: { search: q, include_stats: true } }),
}

export const sequenceApi = {
  getSequence: (battery_model: string) => {
    return fetch('/api/v1/disassembly/sequence', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ battery_model }),
    }).then(res => res.json())
  },
}

export const configApi = {
  getAll: () => api.get<Config>('/config'),
  update: (category: string, data: Record<string, unknown>) =>
    api.put(`/config/${category}`, data),
  validate: () => api.get('/config/validate'),
  reload: () => api.post('/config/reload'),
}

export const importApi = {
  importL1Manual: (data: L1ComponentInput) => api.post('/import/l1/manual', data),
  importL1Csv: (formData: FormData) =>
    api.post('/import/l1/csv', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    }),
  importL1Txt: (formData: FormData) =>
    api.post('/import/l1/txt', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    }),
  importL1Pdf: (formData: FormData) =>
    api.post('/import/l1/pdf', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    }),
  importL1Markdown: (formData: FormData) =>
    api.post('/import/l1/markdown', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    }),
  importL2: (formData: FormData) =>
    api.post('/import/l2', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    }),
  importL2Markdown: (formData: FormData) =>
    api.post('/import/l2/markdown', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    }),
  importL3: (data: L3TermInput) => api.post('/import/l3', data),
  importL3Markdown: (formData: FormData) =>
    api.post('/import/l3/markdown', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    }),
  getStatus: () => api.get('/import/status'),
}

export const evaluationApi = {
  // Rules
  createRule: (data: any) => api.post('/evaluation/rules', data),
  listRules: (status?: string) => api.get('/evaluation/rules', { params: status ? { status } : {} }),
  getRule: (id: string) => api.get(`/evaluation/rules/${id}`),
  updateRule: (id: string, data: any) => api.put(`/evaluation/rules/${id}`, data),
  deleteRule: (id: string) => api.delete(`/evaluation/rules/${id}`),

  // Versions
  createVersion: (data: any) => api.post('/evaluation/versions', data),
  listVersions: () => api.get('/evaluation/versions'),
  getVersion: (id: string) => api.get(`/evaluation/versions/${id}`),

  // Assessment
  assess: (versionId: string) => api.post('/evaluation/assess', { version_id: versionId }),
  getAssessment: (id: string) => api.get(`/evaluation/assessments/${id}`),
  getFeedbackText: (id: string) => api.post(`/evaluation/assessments/${id}/feedback-text`),
  submitExpertFeedback: (assessmentId: string, data: any) =>
    api.post(`/evaluation/assessments/${assessmentId}/feedback`, data),
  generateActions: (assessmentId: string) =>
    api.post(`/evaluation/assessments/${assessmentId}/optimize`),
  applyActions: (data: any) => api.post('/evaluation/actions/apply', data),

  // Prediction
  predict: (data: any) => api.post('/evaluation/predict', data),

  // Batch Assessment
  batchAssess: (versionIds: string[]) =>
    api.post('/evaluation/batch-assess', { version_ids: versionIds }),

  // Grade Config
  getGradeConfig: () => api.get('/evaluation/grade-config'),
  updateGradeConfig: (config: any) => api.put('/evaluation/grade-config', config),
  calibrateThresholds: () => api.post('/evaluation/grade-config/calibrate'),

  // Import
  extractRules: (docIds: string[]) => api.post('/evaluation/import/extract', { doc_ids: docIds }),
  listCandidates: () => api.get('/evaluation/import/candidates'),
  approveCandidate: (id: string) => api.post(`/evaluation/import/approve/${id}`),
  rejectCandidate: (id: string) => api.post(`/evaluation/import/reject/${id}`),

  // Component Eval Attributes
  getEvalAttributes: (componentId: string) => api.get(`/evaluation/components/${componentId}/eval-attributes`),
  updateEvalAttributes: (componentId: string, data: Record<string, string>) =>
    api.put(`/evaluation/components/${componentId}/eval-attributes`, data),
};

export default api
