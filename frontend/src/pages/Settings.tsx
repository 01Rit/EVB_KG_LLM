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
      setMessage('✅ 保存成功')
      setTimeout(() => setMessage(''), 3000)
    } catch (error) {
      setMessage('❌ 保存失败')
    } finally {
      setSaving(false)
    }
  }

  if (loading) {
    return (
      <div className="page-content">
        <h1 className="page-header">⚙️ 参数设置</h1>
        <div className="card">
          <div className="skeleton" style={{ height: 24, width: '60%', marginBottom: 16 }} />
          <div className="skeleton" style={{ height: 40, width: '100%', marginBottom: 12 }} />
          <div className="skeleton" style={{ height: 40, width: '100%', marginBottom: 12 }} />
          <div className="skeleton" style={{ height: 40, width: '100%' }} />
        </div>
      </div>
    )
  }

  return (
    <div className="page-content">
      <h1 className="page-header">⚙️ 参数设置</h1>

      {message && (
        <div className={`card mb-xl ${message.includes('✅') ? '' : ''}`}
          style={{
            background: message.includes('✅') ? 'var(--color-success-bg)' : 'var(--color-error-bg)',
            borderColor: message.includes('✅') ? '#bbf7d0' : '#fecaca',
          }}
        >
          <span className="font-bold text-sm">{message}</span>
        </div>
      )}

      {config && (
        <div className="flex-col gap-xl">
          {/* MTM */}
          <div className="card">
            <div className="card-header">
              <span className="card-title">⏱️ MTM 时间参数</span>
            </div>
            <div className="grid-3 mb-lg">
              <div className="form-group">
                <label className="form-label">工具切换时间 (秒)</label>
                <input
                  type="number"
                  className="form-input"
                  value={config.mtm.tool_switch_default}
                  onChange={(e) => setConfig({ ...config, mtm: { ...config.mtm, tool_switch_default: Number(e.target.value) } })}
                />
              </div>
              <div className="form-group">
                <label className="form-label">位置转移时间 (秒)</label>
                <input
                  type="number"
                  className="form-input"
                  value={config.mtm.position_default}
                  onChange={(e) => setConfig({ ...config, mtm: { ...config.mtm, position_default: Number(e.target.value) } })}
                />
              </div>
              <div className="form-group">
                <label className="form-label">MTM 基准时间 (秒)</label>
                <input
                  type="number"
                  className="form-input"
                  value={config.mtm.mtm_base_seconds}
                  onChange={(e) => setConfig({ ...config, mtm: { ...config.mtm, mtm_base_seconds: Number(e.target.value) } })}
                />
              </div>
            </div>
            <button className="btn btn-primary" onClick={() => handleSave('mtm')} disabled={saving}>
              {saving ? '保存中...' : '保存 MTM 参数'}
            </button>
          </div>

          {/* Threshold */}
          <div className="card">
            <div className="card-header">
              <span className="card-title">🎯 分配阈值</span>
            </div>
            <div className="grid-2 mb-lg">
              <div className="form-group">
                <label className="form-label">Robot 阈值 (AS &gt; ?)</label>
                <input
                  type="number"
                  step="0.1"
                  min="0"
                  max="1"
                  className="form-input"
                  value={config.threshold.robot_threshold}
                  onChange={(e) => setConfig({ ...config, threshold: { ...config.threshold, robot_threshold: Number(e.target.value) } })}
                />
              </div>
              <div className="form-group">
                <label className="form-label">Human 阈值 (AS &lt; ?)</label>
                <input
                  type="number"
                  step="0.1"
                  min="0"
                  max="1"
                  className="form-input"
                  value={config.threshold.human_threshold}
                  onChange={(e) => setConfig({ ...config, threshold: { ...config.threshold, human_threshold: Number(e.target.value) } })}
                />
              </div>
            </div>
            <button className="btn btn-primary" onClick={() => handleSave('threshold')} disabled={saving}>
              {saving ? '保存中...' : '保存阈值参数'}
            </button>
          </div>

          {/* LLM */}
          <div className="card">
            <div className="card-header">
              <span className="card-title">🧠 LLM 参数</span>
            </div>
            <div className="grid-2 mb-lg">
              <div className="form-group">
                <label className="form-label">Temperature</label>
                <input
                  type="number"
                  step="0.1"
                  min="0"
                  max="1"
                  className="form-input"
                  value={config.llm.temperature}
                  onChange={(e) => setConfig({ ...config, llm: { ...config.llm, temperature: Number(e.target.value) } })}
                />
              </div>
              <div className="form-group">
                <label className="form-label">Max Tokens</label>
                <input
                  type="number"
                  className="form-input"
                  value={config.llm.max_tokens}
                  onChange={(e) => setConfig({ ...config, llm: { ...config.llm, max_tokens: Number(e.target.value) } })}
                />
              </div>
            </div>
            <button className="btn btn-primary" onClick={() => handleSave('llm')} disabled={saving}>
              {saving ? '保存中...' : '保存 LLM 参数'}
            </button>
          </div>

          {/* RAG */}
          <div className="card">
            <div className="card-header">
              <span className="card-title">📚 RAG 参数</span>
            </div>
            <div className="grid-3 mb-lg">
              <div className="form-group">
                <label className="form-label">Top K</label>
                <input
                  type="number"
                  className="form-input"
                  value={config.rag.top_k}
                  onChange={(e) => setConfig({ ...config, rag: { ...config.rag, top_k: Number(e.target.value) } })}
                />
              </div>
              <div className="form-group">
                <label className="form-label">相似度阈值</label>
                <input
                  type="number"
                  step="0.01"
                  min="0"
                  max="1"
                  className="form-input"
                  value={config.rag.similarity_threshold}
                  onChange={(e) => setConfig({ ...config, rag: { ...config.rag, similarity_threshold: Number(e.target.value) } })}
                />
              </div>
              <div className="form-group">
                <label className="form-label">检索深度</label>
                <input
                  type="number"
                  className="form-input"
                  value={config.rag.retrieval_depth}
                  onChange={(e) => setConfig({ ...config, rag: { ...config.rag, retrieval_depth: Number(e.target.value) } })}
                />
              </div>
            </div>
            <button className="btn btn-primary" onClick={() => handleSave('rag')} disabled={saving}>
              {saving ? '保存中...' : '保存 RAG 参数'}
            </button>
          </div>
        </div>
      )}
    </div>
  )
}
