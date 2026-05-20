import { useState, useEffect } from 'react';
import { evaluationApi } from '../api/client';

type Tab = 'assessment' | 'workbench' | 'rules';

interface DesignVersion {
  version_id: string;
  design_name: string;
  version_number: number;
  status: string;
}

interface RuleMatch {
  rule_id: string;
  rule_name: string;
  matched: boolean;
  score_contribution: number;
  reason: string;
}

interface Assessment {
  assessment_id: string;
  version_id: string;
  overall_score: number;
  overall_grade: string;
  rule_matches: RuleMatch[];
  feedback_text: string;
}

export default function EvaluationPage() {
  const [activeTab, setActiveTab] = useState<Tab>('assessment');
  const [versions, setVersions] = useState<DesignVersion[]>([]);
  const [selectedVersion, setSelectedVersion] = useState<string>('');
  const [assessment, setAssessment] = useState<Assessment | null>(null);
  const [feedbackText, setFeedbackText] = useState<string>('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string>('');

  useEffect(() => {
    loadVersions();
  }, []);

  async function loadVersions() {
    try {
      const res = await evaluationApi.listVersions();
      setVersions(res.data.data || []);
    } catch (e: any) {
      setError(e.message);
    }
  }

  async function handleAssess() {
    if (!selectedVersion) return;
    setLoading(true);
    setError('');
    try {
      const res = await evaluationApi.assess(selectedVersion);
      setAssessment(res.data.data.assessment);
      const fbRes = await evaluationApi.getFeedbackText(res.data.data.assessment.assessment_id);
      setFeedbackText(fbRes.data.data.feedback_text);
    } catch (e: any) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }

  function getGradeColor(grade: string) {
    if (grade === '高') return '#52c41a';
    if (grade === '中') return '#faad14';
    return '#ff4d4f';
  }

  function getScoreColor(score: number) {
    if (score >= 0.7) return '#52c41a';
    if (score >= 0.4) return '#faad14';
    return '#ff4d4f';
  }

  const tabs = [
    { key: 'assessment' as Tab, label: '评价看板' },
    { key: 'workbench' as Tab, label: '闭环工作台' },
    { key: 'rules' as Tab, label: '规则库管理' },
  ];

  return (
    <div style={{ padding: '24px' }}>
      <h2>可拆卸性评价</h2>

      {/* Tab Navigation */}
      <div style={{ display: 'flex', gap: '8px', marginBottom: '24px', borderBottom: '1px solid #eee', paddingBottom: '8px' }}>
        {tabs.map(tab => (
          <button
            key={tab.key}
            onClick={() => setActiveTab(tab.key)}
            style={{
              padding: '8px 16px', border: 'none',
              borderBottom: activeTab === tab.key ? '2px solid #1890ff' : '2px solid transparent',
              background: 'none', cursor: 'pointer',
              fontWeight: activeTab === tab.key ? 'bold' : 'normal',
              color: activeTab === tab.key ? '#1890ff' : '#666',
            }}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {error && <div style={{ color: 'red', marginBottom: '16px' }}>{error}</div>}

      {/* Tab 1: Assessment Dashboard */}
      {activeTab === 'assessment' && (
        <div>
          <div style={{ marginBottom: '16px', display: 'flex', gap: '8px', alignItems: 'center' }}>
            <select
              value={selectedVersion}
              onChange={e => setSelectedVersion(e.target.value)}
              style={{ padding: '8px', minWidth: '200px' }}
            >
              <option value="">选择设计版本...</option>
              {versions.map(v => (
                <option key={v.version_id} value={v.version_id}>
                  {v.design_name} V{v.version_number} ({v.status})
                </option>
              ))}
            </select>
            <button
              onClick={handleAssess}
              disabled={!selectedVersion || loading}
              style={{
                padding: '8px 16px', background: '#1890ff', color: 'white',
                border: 'none', borderRadius: '4px',
                cursor: selectedVersion && !loading ? 'pointer' : 'not-allowed',
              }}
            >
              {loading ? '评价中...' : '开始评价'}
            </button>
          </div>

          {assessment && (
            <div>
              {/* Score Overview */}
              <div style={{
                padding: '24px', background: '#fafafa', borderRadius: '8px',
                marginBottom: '16px', display: 'flex', alignItems: 'center', gap: '24px',
              }}>
                <div style={{ textAlign: 'center' }}>
                  <div style={{ fontSize: '48px', fontWeight: 'bold', color: getScoreColor(assessment.overall_score) }}>
                    {(assessment.overall_score * 100).toFixed(0)}
                  </div>
                  <div style={{ color: '#666' }}>综合评分</div>
                </div>
                <div style={{
                  padding: '12px 24px', background: getGradeColor(assessment.overall_grade),
                  color: 'white', borderRadius: '8px', fontSize: '24px', fontWeight: 'bold',
                }}>
                  {assessment.overall_grade}
                </div>
                <div style={{ flex: 1 }}>
                  <div style={{ height: '8px', background: '#eee', borderRadius: '4px' }}>
                    <div style={{
                      height: '100%', width: `${assessment.overall_score * 100}%`,
                      background: getScoreColor(assessment.overall_score),
                      borderRadius: '4px', transition: 'width 0.5s',
                    }} />
                  </div>
                </div>
              </div>

              {/* Rule Matches */}
              <div style={{ marginBottom: '16px' }}>
                <h3>规则匹配详情</h3>
                <table style={{ width: '100%', borderCollapse: 'collapse' }}>
                  <thead>
                    <tr style={{ borderBottom: '1px solid #eee' }}>
                      <th style={{ textAlign: 'left', padding: '8px' }}>规则</th>
                      <th style={{ textAlign: 'center', padding: '8px' }}>匹配</th>
                      <th style={{ textAlign: 'right', padding: '8px' }}>贡献分</th>
                      <th style={{ textAlign: 'left', padding: '8px' }}>说明</th>
                    </tr>
                  </thead>
                  <tbody>
                    {assessment.rule_matches.map((m, i) => (
                      <tr key={i} style={{ borderBottom: '1px solid #f5f5f5' }}>
                        <td style={{ padding: '8px' }}>{m.rule_name}</td>
                        <td style={{ textAlign: 'center', padding: '8px' }}>{m.matched ? '✅' : '❌'}</td>
                        <td style={{ textAlign: 'right', padding: '8px' }}>{m.score_contribution.toFixed(2)}</td>
                        <td style={{ padding: '8px', color: '#666' }}>{m.reason}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>

              {/* Feedback */}
              {feedbackText && (
                <div style={{ padding: '16px', background: '#f6ffed', border: '1px solid #b7eb8f', borderRadius: '8px' }}>
                  <h3 style={{ marginTop: 0 }}>评价反馈</h3>
                  <p style={{ whiteSpace: 'pre-wrap', margin: 0 }}>{feedbackText}</p>
                </div>
              )}
            </div>
          )}
        </div>
      )}

      {/* Tab 2: Workbench */}
      {activeTab === 'workbench' && (
        <div style={{ padding: '24px', textAlign: 'center', color: '#999' }}>
          闭环工作台 — 专家修正 + 优化操作 + 版本迭代
        </div>
      )}

      {/* Tab 3: Rules */}
      {activeTab === 'rules' && (
        <div style={{ padding: '24px', textAlign: 'center', color: '#999' }}>
          规则库管理 — 规则 CRUD + 知识导入
        </div>
      )}
    </div>
  );
}
