import { useState, useRef } from 'react'
import { importApi } from '../api/client'

type Tab = 'l1' | 'l2' | 'l3'

export function ImportManager() {
  const [activeTab, setActiveTab] = useState<Tab>('l1')
  const [uploading, setUploading] = useState(false)
  const [message, setMessage] = useState('')

  const [l1Form, setL1Form] = useState({
    name: '',
    battery_model: '',
    tool_required: '',
    safety_level: 1,
    precedence: '',
  })

  const csvRef = useRef<HTMLInputElement>(null)
  const txtRef = useRef<HTMLInputElement>(null)
  const pdfRef = useRef<HTMLInputElement>(null)

  const handleL1Manual = async () => {
    if (!l1Form.name || !l1Form.battery_model) {
      setMessage('请填写必填字段')
      return
    }

    setUploading(true)
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
    } finally {
      setUploading(false)
    }
  }

  const handleCsvUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (!file) return

    setUploading(true)
    try {
      const formData = new FormData()
      formData.append('file', file)
      const res = await importApi.importL1Csv(formData)
      setMessage(`成功: ${res.data.success}, 失败: ${res.data.failed}`)
    } catch (error) {
      setMessage('CSV导入失败')
    } finally {
      setUploading(false)
    }
  }

  const handleTxtUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (!file) return

    setUploading(true)
    try {
      const formData = new FormData()
      formData.append('file', file)
      const res = await importApi.importL1Txt(formData)
      setMessage(res.data.message)
    } catch (error) {
      setMessage('TXT导入失败')
    } finally {
      setUploading(false)
    }
  }

  const handlePdfUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (!file) return

    setUploading(true)
    try {
      const formData = new FormData()
      formData.append('file', file)
      const res = await importApi.importL1Pdf(formData)
      setMessage(res.data.message)
    } catch (error) {
      setMessage('PDF导入失败')
    } finally {
      setUploading(false)
    }
  }

  const handleL2Upload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (!file) return

    setUploading(true)
    try {
      const formData = new FormData()
      formData.append('file', file)
      const res = await importApi.importL2(formData)
      setMessage(`文档已导入，DocID: ${res.data.doc_id}`)
    } catch (error) {
      setMessage('L2导入失败')
    } finally {
      setUploading(false)
    }
  }

  return (
    <div>
      <h1 className="page-header">导入管理</h1>

      {message && (
        <div className="card" style={{ marginBottom: '20px', backgroundColor: message.includes('成功') ? '#d4edda' : '#f8d7da' }}>
          {message}
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
              disabled={uploading}
              style={{ marginTop: '15px', padding: '10px 20px', backgroundColor: '#22c55e', color: 'white', border: 'none', borderRadius: '8px', cursor: uploading ? 'not-allowed' : 'pointer' }}
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
                disabled={uploading}
                style={{ padding: '10px 20px', backgroundColor: '#3b82f6', color: 'white', border: 'none', borderRadius: '8px', cursor: uploading ? 'not-allowed' : 'pointer' }}
              >
                CSV导入
              </button>

              <input type="file" ref={txtRef} accept=".txt" onChange={handleTxtUpload} style={{ display: 'none' }} />
              <button
                onClick={() => txtRef.current?.click()}
                disabled={uploading}
                style={{ padding: '10px 20px', backgroundColor: '#3b82f6', color: 'white', border: 'none', borderRadius: '8px', cursor: uploading ? 'not-allowed' : 'pointer' }}
              >
                TXT导入
              </button>

              <input type="file" ref={pdfRef} accept=".pdf" onChange={handlePdfUpload} style={{ display: 'none' }} />
              <button
                onClick={() => pdfRef.current?.click()}
                disabled={uploading}
                style={{ padding: '10px 20px', backgroundColor: '#f97316', color: 'white', border: 'none', borderRadius: '8px', cursor: uploading ? 'not-allowed' : 'pointer' }}
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
            disabled={uploading}
            style={{ padding: '15px 30px', backgroundColor: '#f97316', color: 'white', border: 'none', borderRadius: '8px', cursor: uploading ? 'not-allowed' : 'pointer' }}
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
