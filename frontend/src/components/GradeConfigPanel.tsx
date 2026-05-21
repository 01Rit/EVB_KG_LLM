import { useState, useEffect } from 'react';
import { evaluationApi } from '../api/client';

interface GradeConfig {
  excellent_threshold: number;
  good_threshold: number;
  qualified_threshold: number;
  source: string;
}

export default function GradeConfigPanel() {
  const [config, setConfig] = useState<GradeConfig | null>(null);
  const [editing, setEditing] = useState(false);
  const [editForm, setEditForm] = useState<GradeConfig>({
    excellent_threshold: 0.75,
    good_threshold: 0.55,
    qualified_threshold: 0.35,
    source: 'default',
  });
  const [calibrating, setCalibrating] = useState(false);
  const [message, setMessage] = useState('');

  useEffect(() => { loadConfig(); }, []);

  async function loadConfig() {
    try {
      const res = await evaluationApi.getGradeConfig();
      const cfg = res.data.data;
      setConfig(cfg);
      setEditForm(cfg);
    } catch (e: any) {
      console.error('Failed to load grade config:', e);
    }
  }

  async function handleSave() {
    try {
      const res = await evaluationApi.updateGradeConfig(editForm);
      setConfig(res.data.data);
      setEditing(false);
      setMessage('阈值已更新');
      setTimeout(() => setMessage(''), 3000);
    } catch (e: any) {
      setMessage('更新失败: ' + e.message);
    }
  }

  async function handleCalibrate() {
    setCalibrating(true);
    try {
      const res = await evaluationApi.calibrateThresholds();
      setConfig(res.data.data);
      setEditForm(res.data.data);
      setMessage('自动标定完成');
      setTimeout(() => setMessage(''), 3000);
    } catch (e: any) {
      setMessage('标定失败: ' + (e.response?.data?.detail || e.message));
    } finally {
      setCalibrating(false);
    }
  }

  if (!config) return <div style={{ color: '#999' }}>加载中...</div>;

  return (
    <div style={{ padding: '16px', background: '#fafafa', borderRadius: '8px', border: '1px solid #eee' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '12px' }}>
        <h4 style={{ margin: 0 }}>等级阈值配置</h4>
        <div style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
          <span style={{
            padding: '2px 8px', borderRadius: '4px', fontSize: '12px',
            background: config.source === 'calibrated' ? '#f6ffed' : '#fffbe6',
            color: config.source === 'calibrated' ? '#52c41a' : '#faad14',
          }}>
            {config.source === 'calibrated' ? '自动标定' : '默认值'}
          </span>
          {!editing && (
            <>
              <button onClick={() => setEditing(true)} style={{ padding: '4px 12px', fontSize: '12px', border: '1px solid #d9d9d9', borderRadius: '4px', background: '#fff', cursor: 'pointer' }}>
                手动调整
              </button>
              <button onClick={handleCalibrate} disabled={calibrating} style={{ padding: '4px 12px', fontSize: '12px', border: '1px solid #1890ff', borderRadius: '4px', background: '#fff', color: '#1890ff', cursor: 'pointer' }}>
                {calibrating ? '标定中...' : '自动标定'}
              </button>
            </>
          )}
        </div>
      </div>

      {editing ? (
        <div>
          <div style={{ display: 'flex', gap: '16px', marginBottom: '12px' }}>
            <div>
              <label style={{ fontSize: '12px', color: '#666' }}>优秀 &ge;</label>
              <input type="number" min="0" max="1" step="0.05" value={editForm.excellent_threshold}
                onChange={e => setEditForm({ ...editForm, excellent_threshold: parseFloat(e.target.value) || 0.75 })}
                style={{ width: '80px', padding: '4px', marginLeft: '4px' }} />
            </div>
            <div>
              <label style={{ fontSize: '12px', color: '#666' }}>良好 &ge;</label>
              <input type="number" min="0" max="1" step="0.05" value={editForm.good_threshold}
                onChange={e => setEditForm({ ...editForm, good_threshold: parseFloat(e.target.value) || 0.55 })}
                style={{ width: '80px', padding: '4px', marginLeft: '4px' }} />
            </div>
            <div>
              <label style={{ fontSize: '12px', color: '#666' }}>合格 &ge;</label>
              <input type="number" min="0" max="1" step="0.05" value={editForm.qualified_threshold}
                onChange={e => setEditForm({ ...editForm, qualified_threshold: parseFloat(e.target.value) || 0.35 })}
                style={{ width: '80px', padding: '4px', marginLeft: '4px' }} />
            </div>
          </div>
          <div style={{ display: 'flex', gap: '8px' }}>
            <button onClick={handleSave} style={{ padding: '4px 16px', background: '#1890ff', color: 'white', border: 'none', borderRadius: '4px', cursor: 'pointer' }}>保存</button>
            <button onClick={() => { setEditing(false); setEditForm(config!); }} style={{ padding: '4px 16px', background: '#f5f5f5', border: '1px solid #d9d9d9', borderRadius: '4px', cursor: 'pointer' }}>取消</button>
          </div>
        </div>
      ) : (
        <div style={{ display: 'flex', gap: '24px' }}>
          <div style={{ textAlign: 'center' }}>
            <div style={{ fontSize: '12px', color: '#666' }}>优秀 &ge;</div>
            <div style={{ fontSize: '24px', fontWeight: 'bold', color: '#52c41a' }}>{config.excellent_threshold}</div>
          </div>
          <div style={{ textAlign: 'center' }}>
            <div style={{ fontSize: '12px', color: '#666' }}>良好 &ge;</div>
            <div style={{ fontSize: '24px', fontWeight: 'bold', color: '#1890ff' }}>{config.good_threshold}</div>
          </div>
          <div style={{ textAlign: 'center' }}>
            <div style={{ fontSize: '12px', color: '#666' }}>合格 &ge;</div>
            <div style={{ fontSize: '24px', fontWeight: 'bold', color: '#faad14' }}>{config.qualified_threshold}</div>
          </div>
          <div style={{ textAlign: 'center' }}>
            <div style={{ fontSize: '12px', color: '#666' }}>不可再制造 &lt;</div>
            <div style={{ fontSize: '24px', fontWeight: 'bold', color: '#ff4d4f' }}>{config.qualified_threshold}</div>
          </div>
        </div>
      )}
      {message && <div style={{ marginTop: '8px', color: message.includes('失败') ? '#ff4d4f' : '#52c41a', fontSize: '13px' }}>{message}</div>}
    </div>
  );
}
