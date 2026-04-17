import axios from 'axios'
import type {
  QueryRequest,
  QueryResponse,
  SequenceResponse,
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
  feedback: (data: { question: string; use_web_search: boolean; context: string[] }) =>
    api.post('/query/feedback', data),
  feedbackSync: (data: { question: string; use_web_search: boolean; context: string[] }) =>
    api.post<{ code: number; message: string; data: { answer: string; sources: any[] } }>('/query/feedback/sync', data),
}

export const batteryApi = {
  search: (q: string = '') =>
    api.get<{ code: number; message: string; data: Array<{ model: string; L1_components: number; L2_entities: number; L3_terms: number }> }>('/battery-models', { params: { search: q, include_stats: true } }),
}

export const sequenceApi = {
  getSequence: (batteryModel: string) =>
    api.get<SequenceResponse>(`/disassembly/sequence/${batteryModel}`),
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
  importL2: (formData: FormData) =>
    api.post('/import/l2', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    }),
  importL3: (data: L3TermInput) => api.post('/import/l3', data),
  getStatus: () => api.get('/import/status'),
}

export default api
