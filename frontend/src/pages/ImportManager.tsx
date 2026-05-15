import { useState, useRef, useEffect } from 'react'
import { importApi } from '../api/client'
import ReactMarkdown from 'react-markdown'

type Tab = 'l1' | 'l2' | 'l3'

interface ProgressUpdate {
  task_id: string
  stage: string
  current: number
  total: number
  message: string
  detail?: string
}

interface ImportTask {
  taskId: string
  type: 'l1_csv' | 'l1_txt' | 'l1_markdown' | 'l2' | 'l2_markdown'
  status: 'idle' | 'processing' | 'success' | 'error'
  progress: number
  message: string
  detail?: string
  stage?: string
}

const STAGE_LABELS: Record<string, string> = {
  idle: '等待', parsing: '解析中', extracting: '提取中',
  creating_nodes: '创建节点', creating_relations: '建立关系',
  scoring: '评分', completing: '完成', completed: '完成',
  error: '错误', subscribed: '已连接',
}

const TAB_ITEMS: { key: Tab; label: string; icon: string }[] = [
  { key: 'l1', label: 'L1 组件', icon: '📦' },
  { key: 'l2', label: 'L2 文档', icon: '📄' },
  { key: 'l3', label: 'L3 术语', icon: '📖' },
]

function ImportProgressCard({ task, onClose }: { task: ImportTask; onClose: () => void }) {
  const stageLabel = STAGE_LABELS[task.stage || ''] || task.stage || ''

  return (
    <div className="card mt-lg" style={{
      background: task.status === 'error' ? 'var(--color-error-bg)' :
                  task.status === 'success' ? 'var(--color-success-bg)' :
                  'var(--color-bg)',
      borderColor: task.status === 'error' ? '#fecaca' :
                   task.status === 'success' ? '#bbf7d0' :
                   'var(--color-border)',
    }}>
      <div className="flex items-center justify-between mb-md">
        <span className="font-bold text-sm">
          {task.type === 'l1_csv' ? 'CSV导入' :
           task.type === 'l1_txt' ? 'TXT导入' :
           task.type === 'l1_markdown' ? 'Markdown导入' :
           task.type === 'l2_markdown' ? 'L2 Markdown导入' : 'L2文档导入'}
        </span>
        <span className={`badge ${task.status === 'error' ? 'badge-red' : task.status === 'success' ? 'badge-green' : 'badge-blue'}`}>
          {task.status === 'error' ? '失败' : task.status === 'success' ? '成功' : '处理中'}
        </span>
      </div>

      <div className="progress-bar-container mb-sm">
        <div className="progress-bar-info">
          <span className="text-sm"><ReactMarkdown>{task.message || stageLabel}</ReactMarkdown></span>
          <span>{task.progress}%</span>
        </div>
        <div className="progress-bar-track">
          <div
            className={`progress-bar-fill ${task.status === 'error' ? 'error' : task.status === 'success' ? 'green complete' : task.status === 'processing' && task.progress === 0 ? 'indeterminate blue' : 'blue'}`}
            style={task.status === 'processing' && task.progress === 0 ? undefined : { width: `${task.progress}%` }}
          />
        </div>
      </div>

      {task.detail && (
        <div className="text-xs text-secondary mt-sm">
          <ReactMarkdown>{task.detail}</ReactMarkdown>
        </div>
      )}

      {/* Stage indicator */}
      <div className="flex items-center gap-md mt-md text-xs text-secondary">
        <span style={{
          width: 8, height: 8, borderRadius: '50%',
          background: task.status === 'processing' ? 'var(--color-l1)' : task.status === 'success' ? 'var(--color-l1)' : task.status === 'error' ? 'var(--color-error)' : '#d1d5db',
          display: 'inline-block',
        }} />
        <span>阶段: {stageLabel}</span>
      </div>

      {task.status === 'success' && (
        <button className="btn btn-ghost btn-sm mt-md" onClick={onClose}>
          关闭
        </button>
      )}
    </div>
  )
}

export function ImportManager() {
  const [activeTab, setActiveTab] = useState<Tab>('l1')
  const [message, setMessage] = useState('')
  const [activeTasks, setActiveTasks] = useState<ImportTask[]>([])

  const [l1Form, setL1Form] = useState({
    name: '', battery_model: '', tool_required: '', safety_level: 1, precedence: '',
  })

  const csvRef = useRef<HTMLInputElement>(null)
  const txtRef = useRef<HTMLInputElement>(null)
  const pdfRef = useRef<HTMLInputElement>(null)
  const mdRef = useRef<HTMLInputElement>(null)
  const mdL2Ref = useRef<HTMLInputElement>(null)
  const mdL3Ref = useRef<HTMLInputElement>(null)

  useEffect(() => {
    const eventSources: Record<string, EventSource> = {}
    activeTasks.forEach(task => {
      if (task.status === 'processing' && !eventSources[task.taskId]) {
        const eventSource = new EventSource(`/api/v1/import/progress/${task.taskId}`)
        eventSource.onmessage = (event) => {
          try {
            const data: ProgressUpdate = JSON.parse(event.data)
            setActiveTasks(prev => prev.map(t => {
              if (t.taskId !== task.taskId) return t
              const newProgress = Math.round((data.current / data.total) * 100)
              const newStatus = data.stage === 'completed' ? 'success'
                : data.stage === 'error' || data.stage === 'not_found' || data.stage === 'timeout' ? 'error' : 'processing'
              return { ...t, status: newStatus, progress: newProgress, message: data.message, detail: data.detail, stage: data.stage }
            }))
          } catch (e) { /* ignore */ }
        }
        eventSource.onerror = () => eventSource.close()
        eventSources[task.taskId] = eventSource
      }
    })
    return () => { Object.values(eventSources).forEach(es => es.close()) }
  }, [activeTasks.length])

  const addTask = (taskId: string, type: ImportTask['type']): ImportTask => {
    const task: ImportTask = { taskId, type, status: 'processing', progress: 0, message: '开始导入任务...', stage: 'idle' }
    setActiveTasks(prev => [...prev, task])
    return task
  }

  const removeTask = (taskId: string) => setActiveTasks(prev => prev.filter(t => t.taskId !== taskId))

  const handleL1Manual = async () => {
    if (!l1Form.name || !l1Form.battery_model) {
      setMessage('**⚠️ 请填写必填字段**\n\n- 组件名称\n- 电池型号')
      return
    }
    try {
      await importApi.importL1Manual({
        name: l1Form.name, battery_model: l1Form.battery_model,
        tool_required: l1Form.tool_required.split(',').map(t => t.trim()).filter(Boolean),
        safety_level: l1Form.safety_level,
        precedence: l1Form.precedence.split(',').map(p => p.trim()).filter(Boolean),
      })
      setMessage('## ✅ 导入成功\n\n组件已添加到知识图谱')
      setL1Form({ name: '', battery_model: '', tool_required: '', safety_level: 1, precedence: '' })
    } catch { setMessage('## ❌ 导入失败\n\n请检查网络连接或重试') }
  }

  const handleFileUpload = async (
    e: React.ChangeEvent<HTMLInputElement>,
    apiFn: (formData: FormData) => Promise<any>,
    taskType: ImportTask['type'] | null,
  ) => {
    const file = e.target.files?.[0]
    if (!file) return
    try {
      const formData = new FormData()
      formData.append('file', file)
      const res = await apiFn(formData)
      if (taskType && res.data.task_id) addTask(res.data.task_id, taskType)
      setMessage(res.data.message || '## 📥 导入任务已创建')
    } catch { setMessage('## ❌ 导入失败\n\n请检查文件格式或网络连接') }
  }

  const recentTasks = activeTasks.slice(-5).reverse()

  return (
    <div className="page-content">
      <h1 className="page-header">📥 导入管理</h1>

      {/* Status Message */}
      {message && (
        <div className="card mb-xl" style={{
          background: message.includes('成功') || message.includes('开始') ? 'var(--color-success-bg)' : 'var(--color-error-bg)',
          borderColor: message.includes('成功') || message.includes('开始') ? '#bbf7d0' : '#fecaca',
        }}>
          <ReactMarkdown>{message}</ReactMarkdown>
        </div>
      )}

      {/* Active Tasks */}
      {recentTasks.length > 0 && (
        <div className="card mb-xl">
          <div className="card-header">
            <span className="card-title">📊 导入进度</span>
          </div>
          {recentTasks.map(task => (
            <ImportProgressCard key={task.taskId} task={task} onClose={() => removeTask(task.taskId)} />
          ))}
        </div>
      )}

      {/* Tabs */}
      <div className="flex gap-md mb-xl">
        {TAB_ITEMS.map(tab => (
          <button
            key={tab.key}
            className={`btn ${activeTab === tab.key ? 'btn-primary' : 'btn-ghost'}`}
            onClick={() => setActiveTab(tab.key)}
          >
            {tab.icon} {tab.label}
          </button>
        ))}
      </div>

      {/* L1 Tab */}
      {activeTab === 'l1' && (
        <div className="card">
          <div className="card-header">
            <span className="card-title">📦 L1 组件导入</span>
          </div>

          <div className="mb-xl">
            <div className="font-bold text-sm mb-md">手动输入</div>
            <div className="grid-2 mb-lg">
              <div className="form-group">
                <label className="form-label">组件名称 *</label>
                <input type="text" className="form-input" value={l1Form.name} onChange={(e) => setL1Form({ ...l1Form, name: e.target.value })} placeholder="例如: 绝缘体" />
              </div>
              <div className="form-group">
                <label className="form-label">电池型号 *</label>
                <input type="text" className="form-input" value={l1Form.battery_model} onChange={(e) => setL1Form({ ...l1Form, battery_model: e.target.value })} placeholder="例如: Model_A" />
              </div>
              <div className="form-group">
                <label className="form-label">所需工具 (逗号分隔)</label>
                <input type="text" className="form-input" value={l1Form.tool_required} onChange={(e) => setL1Form({ ...l1Form, tool_required: e.target.value })} placeholder="扳手,螺丝刀" />
              </div>
              <div className="form-group">
                <label className="form-label">安全等级</label>
                <input type="number" min={1} max={5} className="form-input" value={l1Form.safety_level} onChange={(e) => setL1Form({ ...l1Form, safety_level: Number(e.target.value) })} />
              </div>
              <div className="form-group" style={{ gridColumn: 'span 2' }}>
                <label className="form-label">前序任务 (逗号分隔)</label>
                <input type="text" className="form-input" value={l1Form.precedence} onChange={(e) => setL1Form({ ...l1Form, precedence: e.target.value })} placeholder="上盖,绝缘体" />
              </div>
            </div>
            <button className="btn btn-success" onClick={handleL1Manual}>导入</button>
          </div>

          <div style={{ borderTop: '1px solid var(--color-border)', paddingTop: 'var(--space-xl)' }}>
            <div className="font-bold text-sm mb-md">批量导入</div>
            <div className="flex gap-md flex-wrap">
              <input type="file" ref={mdRef} accept=".md,.markdown" onChange={(e) => handleFileUpload(e, importApi.importL1Markdown, 'l1_markdown')} style={{ display: 'none' }} />
              <button className="btn btn-primary" onClick={() => mdRef.current?.click()}>📄 Markdown导入</button>
              <input type="file" ref={csvRef} accept=".csv" onChange={(e) => handleFileUpload(e, importApi.importL1Csv, 'l1_csv')} style={{ display: 'none' }} />
              <button className="btn btn-primary" onClick={() => csvRef.current?.click()}>📊 CSV导入</button>
              <input type="file" ref={txtRef} accept=".txt" onChange={(e) => handleFileUpload(e, importApi.importL1Txt, 'l1_txt')} style={{ display: 'none' }} />
              <button className="btn btn-primary" onClick={() => txtRef.current?.click()}>📝 TXT导入</button>
              <input type="file" ref={pdfRef} accept=".pdf" onChange={(e) => handleFileUpload(e, importApi.importL1Pdf, null)} style={{ display: 'none' }} />
              <button className="btn btn-warning" onClick={() => pdfRef.current?.click()}>📕 PDF提取导入</button>
            </div>
          </div>
        </div>
      )}

      {/* L2 Tab */}
      {activeTab === 'l2' && (
        <div className="card">
          <div className="card-header">
            <span className="card-title">📄 L2 文档导入</span>
          </div>
          <p className="text-sm text-secondary mb-lg">
            上传 PDF 或 Markdown 文档，系统将自动解析并提取其中的组件和术语信息存入 L2 层。
          </p>
          <div className="flex gap-lg flex-wrap">
            <input type="file" accept=".pdf" onChange={(e) => handleFileUpload(e, importApi.importL2, 'l2')} style={{ display: 'none' }} id="l2-pdf-upload" />
            <button className="btn btn-warning btn-lg" onClick={() => document.getElementById('l2-pdf-upload')?.click()}>📕 选择PDF文件</button>
            <input type="file" ref={mdL2Ref} accept=".md,.markdown" onChange={(e) => handleFileUpload(e, importApi.importL2Markdown, 'l2_markdown')} style={{ display: 'none' }} />
            <button className="btn btn-primary btn-lg" onClick={() => mdL2Ref.current?.click()}>📄 选择Markdown文件</button>
          </div>
        </div>
      )}

      {/* L3 Tab */}
      {activeTab === 'l3' && (
        <div className="card">
          <div className="card-header">
            <span className="card-title">📖 L3 术语导入</span>
          </div>
          <p className="text-sm text-secondary mb-lg">
            L3 术语可以从 L2 文档自动提取，也支持 Markdown 文件导入或手动添加。
          </p>

          <div className="mb-xl">
            <div className="font-bold text-sm mb-md">Markdown 文件导入</div>
            <input type="file" ref={mdL3Ref} accept=".md,.markdown" onChange={(e) => handleFileUpload(e, importApi.importL3Markdown, null)} style={{ display: 'none' }} />
            <button className="btn btn-primary" onClick={() => mdL3Ref.current?.click()}>📄 选择Markdown文件</button>
          </div>

          <div style={{ borderTop: '1px solid var(--color-border)', paddingTop: 'var(--space-xl)' }}>
            <div className="font-bold text-sm mb-md">手动添加术语</div>
            <div className="grid-2 mb-lg">
              <div className="form-group">
                <label className="form-label">术语 ID *</label>
                <input type="text" className="form-input" id="term-id" placeholder="例如: TERM_001" />
              </div>
              <div className="form-group">
                <label className="form-label">术语名称 *</label>
                <input type="text" className="form-input" id="term-name" placeholder="例如: 绝缘材料" />
              </div>
              <div className="form-group" style={{ gridColumn: 'span 2' }}>
                <label className="form-label">定义 *</label>
                <textarea className="form-input" id="term-definition" rows={3} placeholder="术语的详细定义..." style={{ resize: 'vertical' }} />
              </div>
            </div>
            <button
              className="btn btn-success"
              onClick={async () => {
                const termId = (document.getElementById('term-id') as HTMLInputElement)?.value?.trim()
                const name = (document.getElementById('term-name') as HTMLInputElement)?.value?.trim()
                const definition = (document.getElementById('term-definition') as HTMLTextAreaElement)?.value?.trim()
                if (!termId || !name || !definition) {
                  setMessage('**⚠️ 请填写所有必填字段**\n\n- 术语ID\n- 术语名称\n- 定义')
                  return
                }
                try {
                  const res = await importApi.importL3({ terms: [{ term_id: termId, name, definition, units: '' }] })
                  setMessage(res.data.message || '## ✅ 术语导入成功')
                  ;(document.getElementById('term-id') as HTMLInputElement).value = ''
                  ;(document.getElementById('term-name') as HTMLInputElement).value = ''
                  ;(document.getElementById('term-definition') as HTMLTextAreaElement).value = ''
                } catch { setMessage('## ❌ 术语导入失败') }
              }}
            >
              添加术语
            </button>
          </div>
        </div>
      )}
    </div>
  )
}
