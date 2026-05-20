import { BrowserRouter, Routes, Route } from 'react-router-dom'
import { Layout } from './components/Layout/Layout'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { Dashboard } from './pages/Dashboard'
import { GraphExplorer } from './pages/GraphExplorer'
import { QueryPage } from './pages/QueryPage'
import { SequencePlanner } from './pages/SequencePlanner'
import { ImportManager } from './pages/ImportManager'
import { Settings } from './pages/Settings'
import EvaluationPage from './pages/EvaluationPage'

const queryClient = new QueryClient()

export default function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <Routes>
          <Route path="/" element={<Layout />}>
            <Route index element={<Dashboard />} />
            <Route path="graph" element={<GraphExplorer />} />
            <Route path="query" element={<QueryPage />} />
            <Route path="sequence" element={<SequencePlanner />} />
            <Route path="import" element={<ImportManager />} />
            <Route path="settings" element={<Settings />} />
            <Route path="evaluation" element={<EvaluationPage />} />
          </Route>
        </Routes>
      </BrowserRouter>
    </QueryClientProvider>
  )
}