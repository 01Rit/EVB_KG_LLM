import { useState, useRef, useEffect } from 'react'
import { importApi } from '../api/client'

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
  type: 'l1_csv' | 'l1_txt' | 'l2'
  status: 'idle' | 'processing' | 'success' | 'error'
  progress: number
  message: string
  detail?: string
  stage?: string
}

const STAGE_LABELS: Record<string, string> = {
  idle: '等待',
  parsing: '解析中',
  extracting: '提取中',
  creating_nodes: '创建节点',
  creating_relations: '建立关系',
  scoring: '评分',
  completing: '完成',
  completed: '完成',
  error: '错误',
  subscribed: '已连接'
}

function ImportProgressCard({ task, onClose }: { task: ImportTask; onClose: () => void }) {
  const percentage = task.progress
  const stageLabel = STAGE_LABELS[task.stage || ''] || task.stage || ''

  return (
    <div style={{
      marginTop: '16px',
      padding: '16px',
      backgroundColor: task.status === 'error' ? '#fef2f2' : task.status === 'success' ? '#f0fdf4' : '#f8fafc',
      borderRadius: '8px',
      border: `1px solid ${task.status === 'error' ? '#fecaca' : task.status === 'success' ? '#bbf7d0' : '#e2e8f0'}`
    }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '12px' }}>
        <span style={{ fontWeight: 'bold', color: '#1e293b' }}>
          {task.type === 'l1_csv' ? 'CSV导入' : task.type === 'l1_txt' ? 'TXT导入' : 'L2文档导入'}
        </span>
        <span style={{
          fontSize: '12px',
          padding: '2px 8px',
          borderRadius: '4px',
          backgroundColor: task.status === 'error' ? '#ef4444' : task.status === 'success' ? '#22c55e' : '#3b82f6',
          color: 'white'
        }}>
          {task.status === 'error' ? '失败' : task.status === 'success' ? '成功' : '处理中'}
        </span>
      </div>

      <div style={{ marginBottom: '8px' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '13px', color: '#64748b' }}>
          <span>{task.message || stageLabel}</span>
          <span>{percentage}%</span>
        </div>
        <div style={{ height: '8px', backgroundColor: '#e2e8f0', borderRadius: '4px', overflow: 'hidden', marginTop: '4px' }}>
          <div style={{
            height: '100%',
            width: `${percentage}%`,
            backgroundColor: task.status === 'error' ? '#ef4444' : task.status === 'success' ? '#22c55e' : '#3b82f6',
            transition: 'width 0.3s ease'
          }} />
        </div>
      </div>

      {task.detail && (
        <div style={{ fontSize: '12px', color: '#64748b', marginTop: '8px' }}>
          详情: {task.detail}
        </div>
      )}

      <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginTop: '12px' }}>
        <div style={{
          width: '8px',
          height: '8px',
          borderRadius: '50%',
          backgroundColor: task.status === 'processing' ? '#22c55e' : 'transparent'
        }} />
        <span style={{ fontSize: '12px', color: '#64748b' }}>
          阶段: {stageLabel}
        </span>
      </div>

      {task.status === 'success' && (
        <button
          onClick={onClose}
          style={{
            marginTop: '12px',
            padding: '6px 12px',
            fontSize: '12px',
            backgroundColor: '#64748b',
            color: 'white',
            border: 'none',
            borderRadius: '4px',
            cursor: 'pointer'
          }}
        >
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

  const l1Form = useState({
    name: '',
    battery_model: '',
    tool_required: '',
    safety_level: 1,
    precedence: '',
  })[0]
  const setL1Form = useState({
    name: '',
    battery_model: '',
    tool_required: '',
    safety_level: 1,
    precedence: '',
  })[1]

  const csvRef = useRef<HTMLInputElement>(null)
  const txtRef = useRef<HTMLInputElement>(null)
  const pdfRef = useRef<HTMLInputElement>(null)

  useEffect(() => {
    const eventSources: Record<string, EventSource> = {}

    activeTasks.forEach(task => {
      if (task.status === 'processing' && !eventSources[task.taskId]) {
        const url = `/api/v1/import/progress/${task.taskId}`
        const eventSource = new EventSource(url)

        eventSource.onmessage = (event) => {
          try {
            const data: ProgressUpdate = JSON.parse(event.data)

            setActiveTasks(prev => prev.map(t => {
              if (t.taskId !== task.taskId) return t

              const newProgress = Math.round((data.current / data.total) * 100)
              const newStatus = data.stage === 'completed' ? 'success'
                : data.stage === 'error' ? 'error'
                : data.stage === 'not_found' ? 'error'
                : data.stage === 'timeout' ? 'error'
                : 'processing'

              return {
                ...t,
                status: newStatus,
                progress: newProgress,
                message: data.message,
                detail: data.detail,
                stage: data.stage
              }
            }))
          } catch (e) {
            console.error('Failed to parse SSE data:', e)
          }
        }

        eventSource.onerror = () => {
          eventSource.close()
        }

        eventSources[task.taskId] = eventSource
      }
    })

    return () => {
      Object.values(eventSources).forEach(es => es.close())
    }
  }, [activeTasks.length, activeTasks.filter(t => t.status === 'processing').length])

  const addTask = (taskId: string, type: ImportTask['type']): ImportTask => {
    const task: ImportTask = {
      taskId,
      type,
      status: 'processing',
      progress: 0,
      message: '开始导入...',
      stage: 'idle'
    }
    setActiveTasks(prev => [...prev, task])
    return task
  }

  const removeTask = (taskId: string) => {
    setActiveTasks(prev => prev.filter(t => t.taskId !== taskId))
  }

  const handleL1Manual = async () => {
    if (!l1Form.name || !l1Form.battery_model) {
      setMessage('请填写必填字段')
      return
    }

    try {
      await importApi.importL1Manual({
        name: l1Form.name,
        battery_model: l1Form.battery_model,
        tool_required: l1Form.tool_required.split(',').map(t => t.trim()).filter(Boolean),
        safety_level: l1Form.safety_level,
        precedence: l1Form.precedence.split(',').map(p => p.trim()).filter(Boolean),
      })
      setMessage('导入成功')
      setL1Form({ name: '', battery_model: '', tool_required: '', safety_level: 1, precedence: '' })
    } catch (error) {
      setMessage('导入失败')
    }
  }

  const handleCsvUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (!file) return

    try {
      const formData = new FormData()
      formData.append('file', file)
      const res = await importApi.importL1Csv(formData)

      if (res.data.task_id) {
        addTask(res.data.task_id, 'l1_csv')
      }

      setMessage(`开始导入${res.data.total || 0}行`)
    } catch (error) {
      setMessage('CSV导入失败')
    }
  }

  const handleTxtUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (!file) return

    try {
      const formData = new FormData()
      formData.append('file', file)
      const res = await importApi.importL1Txt(formData)

      if (res.data.task_id) {
        addTask(res.data.task_id, 'l1_txt')
      }

      setMessage('开始解析TXT三元组')
    } catch (error) {
      setMessage('TXT导入失败')
    }
  }

  const handlePdfUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (!file) return

    try {
      const formData = new FormData()
      formData.append('file', file)
      const res = await importApi.importL1Pdf(formData)
      setMessage(res.data.message)
    } catch (error) {
      setMessage('PDF导入失败')
    }
  }

  const handleL2Upload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (!file) return

    try {
      const formData = new FormData()
      const blob = new Blob([await file.arrayBuffer()], { type: 'application/pdf' })
      const safeFile = new File([blob], encodeURIComponent(file.name), { type: 'application/pdf' })
      formData.append('file', safeFile)

      const res = await importApi.importL2(formData)

      if (res.data.task_id) {
        addTask(res.data.task_id, 'l2')
      }

      setMessage('开始L2文档导入')
    } catch (error) {
      setMessage('L2导入失败')
    }
  }

  const recentTasks = activeTasks.slice(-5).reverse()

  return (
    <div>
      <h1 className="page-header">导入管理</h1>

      {message && (
        <div className="card" style={{ marginBottom: '20px', backgroundColor: message.includes('成功') || message.includes('开始') ? '#d4edda' : '#f8d7da' }}>
          {message}
        </div>
      )}

      {recentTasks.length > 0 && (
        <div className="card" style={{ marginBottom: '20px' }}>
          <h3 style={{ marginBottom: '12px', fontSize: '16px' }}>导入进度</h3>
          {recentTasks.map(task => (
            <ImportProgressCard
              key={task.taskId}
              task={task}
              onClose={() => removeTask(task.taskId)}
            />
          ))}
        </div>
      )}

      <div style={{ display: 'flex', gap: '10px', marginBottom: '20px' }}>
        {(['l1', 'l2', 'l3'] as Tab[]).map(tab => (
          <button
            key={tab}
            onClick={() => setActiveTab(tab)}
            style={{
              padding: '10px 20px',
              backgroundColor: activeTab === tab ? '#3b82f6' : '#666',
              color: 'white',
              border: 'none',
              borderRadius: '8px',
              cursor: 'pointer',
            }}
          >
            {tab === 'l1' ? 'L1组件' : tab === 'l2' ? 'L2文档' : 'L3术语'}
          </button>
        ))}
      </div>

      {activeTab === 'l1' && (
        <div className="card">
          <h2 style={{ marginBottom: '20px' }}>L1组件导入</h2>

          <div style={{ marginBottom: '20px' }}>
            <h3 style={{ marginBottom: '10px' }}>手动输入</h3>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: '15px' }}>
              <div>
                <label style={{ display: 'block', marginBottom: '5px' }}>组件名称 *</label>
                <input
                  type="text"
                  value={l1Form.name}
                  onChange={(e) => setL1Form({ ...l1Form, name: e.target.value })}
                  style={{ width: '100%', padding: '8px', borderRadius: '4px', border: '1px solid #ddd' }}
                />
              </div>
              <div>
                <label style={{ display: 'block', marginBottom: '5px' }}>电池型号 *</label>
                <input
                  type="text"
                  value={l1Form.battery_model}
                  onChange={(e) => setL1Form({ ...l1Form, battery_model: e.target.value })}
                  style={{ width: '100%', padding: '8px', borderRadius: '4px', border: '1px solid #ddd' }}
                />
              </div>
            </div>
            <button
              onClick={handleL1Manual}
              style={{ marginTop: '15px', padding: '10px 20px', backgroundColor: '#22c55e', color: 'white', border: 'none', borderRadius: '8px', cursor: 'pointer' }}
            >
              导入
            </button>
          </div>

          <div style={{ borderTop: '1px solid #eee', paddingTop: '20px' }}>
            <h3 style={{ marginBottom: '10px' }}>批量导入</h3>
            <div style={{ display: 'flex', gap: '10px' }}>
              <input type="file" ref={csvRef} accept=".csv" onChange={handleCsvUpload} style={{ display: 'none' }} />
              <button
                onClick={() => csvRef.current?.click()}
                style={{ padding: '10px 20px', backgroundColor: '#3b82f6', color: 'white', border: 'none', borderRadius: '8px', cursor: 'pointer' }}
              >
                CSV导入
              </button>

              <input type="file" ref={txtRef} accept=".txt" onChange={handleTxtUpload} style={{ display: 'none' }} />
              <button
                onClick={() => txtRef.current?.click()}
                style={{ padding: '10px 20px', backgroundColor: '#3b82f6', color: 'white', border: 'none', borderRadius: '8px', cursor: 'pointer' }}
              >
                TXT导入
              </button>

              <input type="file" ref={pdfRef} accept=".pdf" onChange={handlePdfUpload} style={{ display: 'none' }} />
              <button
                onClick={() => pdfRef.current?.click()}
                style={{ padding: '10px 20px', backgroundColor: '#f97316', color: 'white', border: 'none', borderRadius: '8px', cursor: 'pointer' }}
              >
                PDF提取导入
              </button>
            </div>
          </div>
        </div>
      )}

      {activeTab === 'l2' && (
        <div className="card">
          <h2 style={{ marginBottom: '20px' }}>L2文档导入</h2>
          <p style={{ marginBottom: '15px', color: '#666' }}>
            上传PDF文档，系统将自动解析并提取其中的组件和术语信息存入L2层。
          </p>
          <input
            type="file"
            accept=".pdf"
            onChange={handleL2Upload}
            style={{ display: 'none' }}
            id="l2-upload"
          />
          <button
            onClick={() => document.getElementById('l2-upload')?.click()}
            style={{ padding: '15px 30px', backgroundColor: '#f97316', color: 'white', border: 'none', borderRadius: '8px', cursor: 'pointer' }}
          >
            选择PDF文件
          </button>
        </div>
      )}

      {activeTab === 'l3' && (
        <div className="card">
          <h2 style={{ marginBottom: '20px' }}>L3术语导入</h2>
          <p style={{ color: '#666' }}>
            L3术语可以从L2文档自动提取，也支持手动添加。
          </p>
        </div>
      )}
    </div>
  )
}