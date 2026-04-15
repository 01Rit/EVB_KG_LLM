import { useState, useEffect } from 'react'
import { configApi } from '../api/client'
import type { Config } from '../types'

export function Settings() {
  const [config, setConfig] = useState<Config | null>(null)
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [message, setMessage] = useState('')

  useEffect(() => {
    const loadConfig = async () => {
      try {
        const res = await configApi.getAll()
        setConfig(res.data)
      } catch (error) {
        console.error('Failed to load config:', error)
      } finally {
        setLoading(false)
      }
    }
    loadConfig()
  }, [])

  const handleSave = async (category: string) => {
    if (!config) return

    setSaving(true)
    try {
      await configApi.update(category, (config as any)[category])
      setMessage('保存成功')
      setTimeout(() => setMessage(''), 3000)
    } catch (error) {
      setMessage('保存失败')
    } finally {
      setSaving(false)
    }
  }

  if (loading) return <div>加载中...</div>

  return (
    <div>
      <h1 className="page-header">参数设置</h1>

      {message && (
        <div className="card" style={{ backgroundColor: message.includes('成功') ? '#d4edda' : '#f8d7da' }}>
          {message}
        </div>
      )}

      {config && (
        <>
          <div className="card">
            <h2 style={{ marginBottom: '15px' }}>MTM时间参数</h2>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '15px' }}>
              <div>
                <label style={{ display: 'block', marginBottom: '5px' }}>工具切换时间(秒)</label>
                <input
                  type="number"
                  value={config.mtm.tool_switch_default}
                  onChange={(e) => setConfig({
                    ...config,
                    mtm: { ...config.mtm, tool_switch_default: Number(e.target.value) }
                  })}
                  style={{ width: '100%', padding: '8px', borderRadius: '4px', border: '1px solid #ddd' }}
                />
              </div>
              <div>
                <label style={{ display: 'block', marginBottom: '5px' }}>位置转移时间(秒)</label>
                <input
                  type="number"
                  value={config.mtm.position_default}
                  onChange={(e) => setConfig({
                    ...config,
                    mtm: { ...config.mtm, position_default: Number(e.target.value) }
                  })}
                  style={{ width: '100%', padding: '8px', borderRadius: '4px', border: '1px solid #ddd' }}
                />
              </div>
              <div>
                <label style={{ display: 'block', marginBottom: '5px' }}>MTM基准时间(秒)</label>
                <input
                  type="number"
                  value={config.mtm.mtm_base_seconds}
                  onChange={(e) => setConfig({
                    ...config,
                    mtm: { ...config.mtm, mtm_base_seconds: Number(e.target.value) }
                  })}
                  style={{ width: '100%', padding: '8px', borderRadius: '4px', border: '1px solid #ddd' }}
                />
              </div>
            </div>
            <button
              onClick={() => handleSave('mtm')}
              disabled={saving}
              style={{ marginTop: '15px', padding: '8px 20px', backgroundColor: '#3b82f6', color: 'white', border: 'none', borderRadius: '4px', cursor: saving ? 'not-allowed' : 'pointer' }}
            >
              保存MTM参数
            </button>
          </div>

          <div className="card">
            <h2 style={{ marginBottom: '15px' }}>分配阈值</h2>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: '15px' }}>
              <div>
                <label style={{ display: 'block', marginBottom: '5px' }}>Robot阈值 (AS &gt; ?)</label>
                <input
                  type="number"
                  step="0.1"
                  min="0"
                  max="1"
                  value={config.threshold.robot_threshold}
                  onChange={(e) => setConfig({
                    ...config,
                    threshold: { ...config.threshold, robot_threshold: Number(e.target.value) }
                  })}
                  style={{ width: '100%', padding: '8px', borderRadius: '4px', border: '1px solid #ddd' }}
                />
              </div>
              <div>
                <label style={{ display: 'block', marginBottom: '5px' }}>Human阈值 (AS &lt; ?)</label>
                <input
                  type="number"
                  step="0.1"
                  min="0"
                  max="1"
                  value={config.threshold.human_threshold}
                  onChange={(e) => setConfig({
                    ...config,
                    threshold: { ...config.threshold, human_threshold: Number(e.target.value) }
                  })}
                  style={{ width: '100%', padding: '8px', borderRadius: '4px', border: '1px solid #ddd' }}
                />
              </div>
            </div>
            <button
              onClick={() => handleSave('threshold')}
              disabled={saving}
              style={{ marginTop: '15px', padding: '8px 20px', backgroundColor: '#3b82f6', color: 'white', border: 'none', borderRadius: '4px', cursor: saving ? 'not-allowed' : 'pointer' }}
            >
              保存阈值参数
            </button>
          </div>

          <div className="card">
            <h2 style={{ marginBottom: '15px' }}>LLM参数</h2>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: '15px' }}>
              <div>
                <label style={{ display: 'block', marginBottom: '5px' }}>Temperature</label>
                <input
                  type="number"
                  step="0.1"
                  min="0"
                  max="1"
                  value={config.llm.temperature}
                  onChange={(e) => setConfig({
                    ...config,
                    llm: { ...config.llm, temperature: Number(e.target.value) }
                  })}
                  style={{ width: '100%', padding: '8px', borderRadius: '4px', border: '1px solid #ddd' }}
                />
              </div>
              <div>
                <label style={{ display: 'block', marginBottom: '5px' }}>Max Tokens</label>
                <input
                  type="number"
                  value={config.llm.max_tokens}
                  onChange={(e) => setConfig({
                    ...config,
                    llm: { ...config.llm, max_tokens: Number(e.target.value) }
                  })}
                  style={{ width: '100%', padding: '8px', borderRadius: '4px', border: '1px solid #ddd' }}
                />
              </div>
            </div>
            <button
              onClick={() => handleSave('llm')}
              disabled={saving}
              style={{ marginTop: '15px', padding: '8px 20px', backgroundColor: '#3b82f6', color: 'white', border: 'none', borderRadius: '4px', cursor: saving ? 'not-allowed' : 'pointer' }}
            >
              保存LLM参数
            </button>
          </div>

          <div className="card">
            <h2 style={{ marginBottom: '15px' }}>RAG参数</h2>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '15px' }}>
              <div>
                <label style={{ display: 'block', marginBottom: '5px' }}>Top K</label>
                <input
                  type="number"
                  value={config.rag.top_k}
                  onChange={(e) => setConfig({
                    ...config,
                    rag: { ...config.rag, top_k: Number(e.target.value) }
                  })}
                  style={{ width: '100%', padding: '8px', borderRadius: '4px', border: '1px solid #ddd' }}
                />
              </div>
              <div>
                <label style={{ display: 'block', marginBottom: '5px' }}>相似度阈值</label>
                <input
                  type="number"
                  step="0.01"
                  min="0"
                  max="1"
                  value={config.rag.similarity_threshold}
                  onChange={(e) => setConfig({
                    ...config,
                    rag: { ...config.rag, similarity_threshold: Number(e.target.value) }
                  })}
                  style={{ width: '100%', padding: '8px', borderRadius: '4px', border: '1px solid #ddd' }}
                />
              </div>
              <div>
                <label style={{ display: 'block', marginBottom: '5px' }}>检索深度</label>
                <input
                  type="number"
                  value={config.rag.retrieval_depth}
                  onChange={(e) => setConfig({
                    ...config,
                    rag: { ...config.rag, retrieval_depth: Number(e.target.value) }
                  })}
                  style={{ width: '100%', padding: '8px', borderRadius: '4px', border: '1px solid #ddd' }}
                />
              </div>
            </div>
            <button
              onClick={() => handleSave('rag')}
              disabled={saving}
              style={{ marginTop: '15px', padding: '8px 20px', backgroundColor: '#3b82f6', color: 'white', border: 'none', borderRadius: '4px', cursor: saving ? 'not-allowed' : 'pointer' }}
            >
              保存RAG参数
            </button>
          </div>
        </>
      )}
    </div>
  )
}