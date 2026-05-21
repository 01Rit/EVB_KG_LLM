import { useState, useEffect } from 'react';
import { evaluationApi, graphApi } from '../api/client';
import RadarChart from '../components/RadarChart';
import GradeConfigPanel from '../components/GradeConfigPanel';

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

interface DimensionScore {
  dimension: string;
  score?: number;
  rsr_value?: number;
  rank?: number;
  grade: string;
  matched_rules: number;
  total_rules: number;
}

interface GradeThreshold {
  excellent: number;
  good: number;
  qualified: number;
}

interface Assessment {
  assessment_id: string;
  version_id: string;
  overall_score: number;
  overall_grade: string;
  rule_matches: RuleMatch[];
  feedback_text: string;
  dimension_scores: DimensionScore[];
  evaluation_mode: string;
  grade_thresholds?: GradeThreshold;
}

interface RuleCondition {
  condition_type: string;
  target_label: string;
  effect?: number;
}

interface Rule {
  rule_id: string;
  name: string;
  description: string;
  conclusion_score: number;
  conclusion_grade: string;
  weight: number;
  status: string;
  conditions: RuleCondition[];
  hit_count: number;
  dimension: string;
  fuzzy_threshold: number;
}

interface RuleFormData {
  name: string;
  description: string;
  conclusion_score: number;
  conclusion_grade: string;
  weight: number;
  conditions: RuleCondition[];
  dimension: string;
  fuzzy_threshold: number;
}

interface Candidate {
  rule_id: string;
  name: string;
  description: string;
  conclusion_score: number;
  conclusion_grade: string;
  conditions: RuleCondition[];
}

export default function EvaluationPage() {
  const [activeTab, setActiveTab] = useState<Tab>('assessment');
  const [versions, setVersions] = useState<DesignVersion[]>([]);
  const [selectedVersion, setSelectedVersion] = useState<string>('');
  const [assessment, setAssessment] = useState<Assessment | null>(null);
  const [feedbackText, setFeedbackText] = useState<string>('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string>('');

  // Rules state
  const [rules, setRules] = useState<Rule[]>([]);
  const [ruleFilter, setRuleFilter] = useState<string>('');
  const [showRuleForm, setShowRuleForm] = useState(false);
  const [editingRule, setEditingRule] = useState<Rule | null>(null);
  const [ruleForm, setRuleForm] = useState<RuleFormData>({
    name: '', description: '', conclusion_score: 0.5, conclusion_grade: '合格',
    weight: 1.0, conditions: [], dimension: 'technical', fuzzy_threshold: 0.6,
  });
  const [deleteConfirm, setDeleteConfirm] = useState<string | null>(null);

  // Import state
  const [showImport, setShowImport] = useState(false);
  const [candidates, setCandidates] = useState<Candidate[]>([]);
  const [importDocIds, setImportDocIds] = useState('');

  // Batch assessment state
  const [batchMode, setBatchMode] = useState(false);
  const [selectedVersions, setSelectedVersions] = useState<string[]>([]);
  const [batchResults, setBatchResults] = useState<any[]>([]);

  // Version creation state
  const [showVersionForm, setShowVersionForm] = useState(false);
  const [versionForm, setVersionForm] = useState({ design_name: '', component_ids: [] as string[], connection_ids: [] as string[] });
  const [graphNodes, setGraphNodes] = useState<any[]>([]);
  const [graphEdges, setGraphEdges] = useState<any[]>([]);

  useEffect(() => {
    loadVersions();
  }, []);

  useEffect(() => {
    if (activeTab === 'rules') loadRules();
  }, [activeTab, ruleFilter]);

  async function loadVersions() {
    try {
      const res = await evaluationApi.listVersions();
      setVersions(res.data.data?.versions || []);
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
      setAssessment(res.data.data);
      const fbRes = await evaluationApi.getFeedbackText(res.data.data.assessment_id);
      setFeedbackText(fbRes.data.data?.feedback_text || '');
    } catch (e: any) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }

  async function handleBatchAssess() {
    if (selectedVersions.length === 0) return;
    setLoading(true);
    setError('');
    try {
      const res = await evaluationApi.batchAssess(selectedVersions);
      setBatchResults(res.data.data?.assessments || []);
    } catch (e: any) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }

  async function openVersionForm() {
    setShowVersionForm(true);
    setVersionForm({ design_name: '', component_ids: [], connection_ids: [] });
    try {
      const [nodesRes, edgesRes] = await Promise.all([
        graphApi.getNodes(),
        graphApi.getRelationships(),
      ]);
      setGraphNodes(nodesRes.data || []);
      setGraphEdges(edgesRes.data || []);
    } catch (e: any) {
      setError(e.message);
    }
  }

  async function handleCreateVersion() {
    if (!versionForm.design_name.trim()) return;
    setLoading(true);
    setError('');
    try {
      await evaluationApi.createVersion(versionForm);
      setShowVersionForm(false);
      loadVersions();
    } catch (e: any) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }

  function toggleComponent(id: string) {
    setVersionForm(prev => ({
      ...prev,
      component_ids: prev.component_ids.includes(id)
        ? prev.component_ids.filter(x => x !== id)
        : [...prev.component_ids, id],
    }));
  }

  function toggleConnection(from: string, to: string) {
    const key = `${from}->${to}`;
    setVersionForm(prev => ({
      ...prev,
      connection_ids: prev.connection_ids.includes(key)
        ? prev.connection_ids.filter(x => x !== key)
        : [...prev.connection_ids, key],
    }));
  }

  function getGradeColor(grade: string) {
    if (grade === '优秀') return '#52c41a';
    if (grade === '良好') return '#1890ff';
    if (grade === '合格') return '#faad14';
    return '#ff4d4f';
  }

  function getScoreColor(score: number) {
    if (score >= 0.75) return '#52c41a';
    if (score >= 0.55) return '#1890ff';
    if (score >= 0.35) return '#faad14';
    return '#ff4d4f';
  }

  // ── Rules Management ──

  async function loadRules() {
    try {
      const res = await evaluationApi.listRules(ruleFilter || undefined);
      setRules(res.data.data?.rules || []);
    } catch (e: any) {
      setError(e.message);
    }
  }

  function openCreateRule() {
    setEditingRule(null);
    setRuleForm({
      name: '', description: '', conclusion_score: 0.5, conclusion_grade: '合格',
      weight: 1.0, conditions: [], dimension: 'technical', fuzzy_threshold: 0.6,
    });
    setShowRuleForm(true);
  }

  function openEditRule(rule: Rule) {
    setEditingRule(rule);
    setRuleForm({
      name: rule.name,
      description: rule.description,
      conclusion_score: rule.conclusion_score,
      conclusion_grade: rule.conclusion_grade,
      weight: rule.weight,
      conditions: [...rule.conditions],
      dimension: rule.dimension || 'technical',
      fuzzy_threshold: rule.fuzzy_threshold ?? 0.6,
    });
    setShowRuleForm(true);
  }

  async function handleSaveRule() {
    try {
      if (editingRule) {
        await evaluationApi.updateRule(editingRule.rule_id, ruleForm);
      } else {
        await evaluationApi.createRule(ruleForm);
      }
      setShowRuleForm(false);
      loadRules();
    } catch (e: any) {
      setError(e.message);
    }
  }

  async function handleDeleteRule(ruleId: string) {
    try {
      await evaluationApi.deleteRule(ruleId);
      setDeleteConfirm(null);
      loadRules();
    } catch (e: any) {
      setError(e.message);
    }
  }

  async function handleToggleStatus(rule: Rule) {
    const newStatus = rule.status === 'active' ? 'disabled' : 'active';
    try {
      await evaluationApi.updateRule(rule.rule_id, { status: newStatus });
      loadRules();
    } catch (e: any) {
      setError(e.message);
    }
  }

  function addCondition() {
    setRuleForm({
      ...ruleForm,
      conditions: [...ruleForm.conditions, { condition_type: 'REQUIRES_CONNECTION', target_label: '' }],
    });
  }

  function updateCondition(index: number, field: keyof RuleCondition, value: string | number) {
    const updated = [...ruleForm.conditions];
    updated[index] = { ...updated[index], [field]: value };
    setRuleForm({ ...ruleForm, conditions: updated });
  }

  function removeCondition(index: number) {
    setRuleForm({
      ...ruleForm,
      conditions: ruleForm.conditions.filter((_, i) => i !== index),
    });
  }

  function recommendGrade(score: number) {
    if (score >= 0.75) return '优秀';
    if (score >= 0.55) return '良好';
    if (score >= 0.35) return '合格';
    return '不可再制造';
  }

  // ── Import Management ──

  async function handleExtractRules() {
    const docIds = importDocIds.split(',').map(s => s.trim()).filter(Boolean);
    if (docIds.length === 0) return;
    try {
      const res = await evaluationApi.extractRules(docIds);
      setCandidates(res.data.data?.candidates || []);
    } catch (e: any) {
      setError(e.message);
    }
  }

  async function loadCandidates() {
    try {
      const res = await evaluationApi.listCandidates();
      setCandidates(res.data.data?.candidates || []);
    } catch (e: any) {
      setError(e.message);
    }
  }

  async function handleApproveCandidate(id: string) {
    try {
      await evaluationApi.approveCandidate(id);
      loadCandidates();
      loadRules();
    } catch (e: any) {
      setError(e.message);
    }
  }

  async function handleRejectCandidate(id: string) {
    try {
      await evaluationApi.rejectCandidate(id);
      loadCandidates();
    } catch (e: any) {
      setError(e.message);
    }
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
          {/* Version Creation Modal */}
          {showVersionForm && (
            <div style={{
              position: 'fixed', top: 0, left: 0, right: 0, bottom: 0,
              background: 'rgba(0,0,0,0.5)', display: 'flex', alignItems: 'center',
              justifyContent: 'center', zIndex: 1000,
            }}>
              <div style={{
                background: 'white', borderRadius: '8px', padding: '24px',
                width: '600px', maxHeight: '80vh', overflow: 'auto',
              }}>
                <h3 style={{ marginTop: 0 }}>创建设计版本</h3>
                <div style={{ marginBottom: '12px' }}>
                  <label style={{ display: 'block', marginBottom: '4px', fontWeight: 500 }}>设计名称</label>
                  <input
                    value={versionForm.design_name}
                    onChange={e => setVersionForm(prev => ({ ...prev, design_name: e.target.value }))}
                    placeholder="例：电池包V1"
                    style={{ width: '100%', padding: '8px', borderRadius: '4px', border: '1px solid #d9d9d9', boxSizing: 'border-box' }}
                  />
                </div>
                <div style={{ marginBottom: '12px' }}>
                  <label style={{ display: 'block', marginBottom: '4px', fontWeight: 500 }}>
                    组件（L1，已选 {versionForm.component_ids.length}）
                  </label>
                  <div style={{
                    maxHeight: '150px', overflow: 'auto', border: '1px solid #d9d9d9',
                    borderRadius: '4px', padding: '8px',
                  }}>
                    {graphNodes.filter(n => n.type === 'L1').length === 0 && (
                      <div style={{ color: '#999', fontSize: '13px' }}>暂无 L1 组件</div>
                    )}
                    {graphNodes.filter(n => n.type === 'L1').map(n => (
                      <label key={n.id} style={{
                        display: 'inline-block', padding: '4px 10px', margin: '3px',
                        borderRadius: '4px', cursor: 'pointer', fontSize: '13px',
                        background: versionForm.component_ids.includes(n.id) ? '#e6f7ff' : '#f5f5f5',
                        border: versionForm.component_ids.includes(n.id) ? '1px solid #1890ff' : '1px solid #d9d9d9',
                      }}>
                        <input
                          type="checkbox"
                          checked={versionForm.component_ids.includes(n.id)}
                          onChange={() => toggleComponent(n.id)}
                          style={{ marginRight: '4px' }}
                        />
                        {n.name}
                      </label>
                    ))}
                  </div>
                </div>
                <div style={{ marginBottom: '16px' }}>
                  <label style={{ display: 'block', marginBottom: '4px', fontWeight: 500 }}>
                    连接（已选 {versionForm.connection_ids.length}）
                  </label>
                  <div style={{
                    maxHeight: '150px', overflow: 'auto', border: '1px solid #d9d9d9',
                    borderRadius: '4px', padding: '8px',
                  }}>
                    {(() => {
                      const l1Ids = new Set(graphNodes.filter(n => n.type === 'L1').map(n => n.id));
                      const l1Edges = graphEdges.filter(e => l1Ids.has(e.from_) && l1Ids.has(e.to));
                      if (l1Edges.length === 0) {
                        return <div style={{ color: '#999', fontSize: '13px' }}>暂无 L1 组件间连接</div>;
                      }
                      return l1Edges.map((e, i) => {
                      const fromNode = graphNodes.find(n => n.id === e.from_);
                      const toNode = graphNodes.find(n => n.id === e.to);
                      const key = `${e.from_}->${e.to}`;
                      const label = `${fromNode?.name || e.from_} → ${toNode?.name || e.to} (${e.type})`;
                      return (
                        <label key={i} style={{
                          display: 'inline-block', padding: '4px 10px', margin: '3px',
                          borderRadius: '4px', cursor: 'pointer', fontSize: '13px',
                          background: versionForm.connection_ids.includes(key) ? '#f6ffed' : '#f5f5f5',
                          border: versionForm.connection_ids.includes(key) ? '1px solid #52c41a' : '1px solid #d9d9d9',
                        }}>
                          <input
                            type="checkbox"
                            checked={versionForm.connection_ids.includes(key)}
                            onChange={() => toggleConnection(e.from_, e.to)}
                            style={{ marginRight: '4px' }}
                          />
                          {label}
                        </label>
                      );
                      });
                    })()}
                  </div>
                </div>
                <div style={{ display: 'flex', gap: '8px', justifyContent: 'flex-end' }}>
                  <button
                    onClick={() => setShowVersionForm(false)}
                    style={{ padding: '8px 16px', border: '1px solid #d9d9d9', borderRadius: '4px', background: '#fff', cursor: 'pointer' }}
                  >取消</button>
                  <button
                    onClick={handleCreateVersion}
                    disabled={!versionForm.design_name.trim() || loading}
                    style={{
                      padding: '8px 16px', background: '#1890ff', color: 'white',
                      border: 'none', borderRadius: '4px',
                      cursor: versionForm.design_name.trim() && !loading ? 'pointer' : 'not-allowed',
                    }}
                  >{loading ? '创建中...' : '创建'}</button>
                </div>
              </div>
            </div>
          )}

          <div style={{ marginBottom: '16px', display: 'flex', gap: '8px', alignItems: 'center', flexWrap: 'wrap' }}>
            <button
              onClick={openVersionForm}
              style={{
                padding: '8px 16px', background: '#52c41a', color: 'white',
                border: 'none', borderRadius: '4px', cursor: 'pointer',
              }}
            >
              + 创建版本
            </button>
            <select
              value={batchMode ? '' : selectedVersion}
              onChange={e => { setSelectedVersion(e.target.value); setBatchMode(false); }}
              disabled={batchMode}
              style={{ padding: '8px', minWidth: '200px', opacity: batchMode ? 0.5 : 1 }}
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
              disabled={!selectedVersion || loading || batchMode}
              style={{
                padding: '8px 16px', background: '#1890ff', color: 'white',
                border: 'none', borderRadius: '4px',
                cursor: selectedVersion && !loading && !batchMode ? 'pointer' : 'not-allowed',
              }}
            >
              {loading && !batchMode ? '评价中...' : '开始评价'}
            </button>
            <button
              onClick={() => { setBatchMode(!batchMode); setBatchResults([]); }}
              style={{
                padding: '8px 16px', background: batchMode ? '#722ed1' : '#fff',
                color: batchMode ? 'white' : '#722ed1',
                border: '1px solid #722ed1', borderRadius: '4px', cursor: 'pointer',
              }}
            >
              {batchMode ? '退出批量' : '批量评价'}
            </button>
          </div>

          {/* Batch Mode */}
          {batchMode && (
            <div style={{
              padding: '16px', background: '#f9f0ff', borderRadius: '8px',
              marginBottom: '16px', border: '1px solid #d3adf7',
            }}>
              <div style={{ display: 'flex', gap: '8px', alignItems: 'center', flexWrap: 'wrap', marginBottom: '12px' }}>
                <span style={{ fontWeight: 500 }}>选择版本（多选）:</span>
                {versions.map(v => (
                  <label key={v.version_id} style={{
                    padding: '4px 12px', borderRadius: '4px', cursor: 'pointer',
                    background: selectedVersions.includes(v.version_id) ? '#722ed1' : '#fff',
                    color: selectedVersions.includes(v.version_id) ? 'white' : '#333',
                    border: '1px solid #d9d9d9', fontSize: '13px',
                  }}>
                    <input
                      type="checkbox"
                      checked={selectedVersions.includes(v.version_id)}
                      onChange={e => {
                        if (e.target.checked) {
                          setSelectedVersions([...selectedVersions, v.version_id]);
                        } else {
                          setSelectedVersions(selectedVersions.filter(id => id !== v.version_id));
                        }
                      }}
                      style={{ display: 'none' }}
                    />
                    {v.design_name} V{v.version_number}
                  </label>
                ))}
              </div>
              <button
                onClick={handleBatchAssess}
                disabled={selectedVersions.length === 0 || loading}
                style={{
                  padding: '8px 24px', background: '#722ed1', color: 'white',
                  border: 'none', borderRadius: '4px',
                  cursor: selectedVersions.length > 0 && !loading ? 'pointer' : 'not-allowed',
                }}
              >
                {loading ? '批量评价中...' : `评价 ${selectedVersions.length} 个版本`}
              </button>

              {batchResults.length > 0 && (
                <div style={{ marginTop: '16px' }}>
                  <h4 style={{ marginTop: 0 }}>批量评价结果</h4>
                  <table style={{ width: '100%', borderCollapse: 'collapse' }}>
                    <thead>
                      <tr style={{ borderBottom: '2px solid #eee', background: '#fafafa' }}>
                        <th style={{ textAlign: 'left', padding: '8px' }}>版本</th>
                        <th style={{ textAlign: 'center', padding: '8px' }}>评分</th>
                        <th style={{ textAlign: 'center', padding: '8px' }}>等级</th>
                      </tr>
                    </thead>
                    <tbody>
                      {batchResults.map((r: any, i: number) => (
                        <tr key={i} style={{ borderBottom: '1px solid #f0f0f0' }}>
                          <td style={{ padding: '8px' }}>{r.version_id}</td>
                          <td style={{ textAlign: 'center', padding: '8px' }}>
                            <span style={{ color: getScoreColor(r.overall_score), fontWeight: 600 }}>
                              {(r.overall_score * 100).toFixed(0)}
                            </span>
                          </td>
                          <td style={{ textAlign: 'center', padding: '8px' }}>
                            <span style={{
                              display: 'inline-block', padding: '2px 8px', borderRadius: '4px',
                              background: getGradeColor(r.overall_grade), color: 'white', fontWeight: 500,
                            }}>
                              {r.overall_grade}
                            </span>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </div>
          )}

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

              {/* Radar Chart + Dimension Table */}
              {assessment.dimension_scores && assessment.dimension_scores.length > 0 && (
                <div style={{ display: 'flex', gap: '24px', marginBottom: '16px', flexWrap: 'wrap' }}>
                  <div style={{ padding: '16px', background: '#fafafa', borderRadius: '8px', flex: '0 0 auto' }}>
                    <h4 style={{ marginTop: 0, marginBottom: '8px' }}>维度雷达图</h4>
                    <RadarChart
                      data={assessment.dimension_scores.map(ds => ({
                        label: ds.dimension === 'technical' ? '技术' : ds.dimension === 'economic' ? '经济' : '环境',
                        value: ds.score ?? ds.rsr_value ?? 0,
                        color: getGradeColor(ds.grade),
                      }))}
                      size={250}
                    />
                  </div>
                  <div style={{ flex: 1, minWidth: '300px' }}>
                    <h4 style={{ marginTop: 0 }}>维度详情</h4>
                    <table style={{ width: '100%', borderCollapse: 'collapse' }}>
                      <thead>
                        <tr style={{ borderBottom: '2px solid #eee', background: '#fafafa' }}>
                          <th style={{ textAlign: 'left', padding: '8px' }}>维度</th>
                          <th style={{ textAlign: 'center', padding: '8px' }}>评分</th>
                          <th style={{ textAlign: 'center', padding: '8px' }}>等级</th>
                          <th style={{ textAlign: 'center', padding: '8px' }}>命中规则</th>
                        </tr>
                      </thead>
                      <tbody>
                        {assessment.dimension_scores.map((ds, i) => (
                          <tr key={i} style={{ borderBottom: '1px solid #f0f0f0' }}>
                            <td style={{ padding: '8px' }}>
                              <span style={{
                                display: 'inline-block', padding: '2px 8px', borderRadius: '4px',
                                background: ds.dimension === 'technical' ? '#e6f7ff' : ds.dimension === 'economic' ? '#f6ffed' : '#f9f0ff',
                                color: ds.dimension === 'technical' ? '#1890ff' : ds.dimension === 'economic' ? '#52c41a' : '#722ed1',
                                fontSize: '12px', fontWeight: 500,
                              }}>
                                {ds.dimension === 'technical' ? '技术' : ds.dimension === 'economic' ? '经济' : '环境'}
                              </span>
                            </td>
                            <td style={{ textAlign: 'center', padding: '8px' }}>
                              <span style={{ color: getScoreColor(ds.score ?? ds.rsr_value ?? 0), fontWeight: 600 }}>
                                {((ds.score ?? ds.rsr_value ?? 0) * 100).toFixed(0)}
                              </span>
                            </td>
                            <td style={{ textAlign: 'center', padding: '8px' }}>
                              <span style={{
                                display: 'inline-block', padding: '2px 8px', borderRadius: '4px',
                                background: getGradeColor(ds.grade), color: 'white', fontWeight: 500,
                              }}>
                                {ds.grade}
                              </span>
                            </td>
                            <td style={{ textAlign: 'center', padding: '8px' }}>{ds.matched_rules}/{ds.total_rules}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>
              )}

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
                <div style={{ padding: '16px', background: '#f6ffed', border: '1px solid #b7eb8f', borderRadius: '8px', marginBottom: '16px' }}>
                  <h3 style={{ marginTop: 0 }}>评价反馈</h3>
                  <p style={{ whiteSpace: 'pre-wrap', margin: 0 }}>{feedbackText}</p>
                </div>
              )}

              {/* Grade Config Panel */}
              <div style={{ marginTop: '16px' }}>
                <GradeConfigPanel />
              </div>
            </div>
          )}

          {/* Show GradeConfigPanel even without assessment for configuration */}
          {!assessment && (
            <div style={{ marginTop: '16px' }}>
              <GradeConfigPanel />
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

      {/* Tab 3: Rules Management */}
      {activeTab === 'rules' && (
        <div>
          {/* Header */}
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
            <div style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
              <span>状态筛选:</span>
              <select
                value={ruleFilter}
                onChange={e => setRuleFilter(e.target.value)}
                style={{ padding: '6px 12px', borderRadius: '4px', border: '1px solid #d9d9d9' }}
              >
                <option value="">全部</option>
                <option value="pending_review">待审核</option>
                <option value="active">启用</option>
                <option value="disabled">禁用</option>
              </select>
            </div>
            <div style={{ display: 'flex', gap: '8px' }}>
              <button
                onClick={() => { setShowImport(!showImport); if (!showImport) loadCandidates(); }}
                style={{
                  padding: '6px 12px', background: '#fff', color: '#666',
                  border: '1px solid #d9d9d9', borderRadius: '4px', cursor: 'pointer',
                }}
              >
                {showImport ? '收起导入' : '导入知识库'}
              </button>
              <button
                onClick={openCreateRule}
                style={{
                  padding: '6px 16px', background: '#1890ff', color: 'white',
                  border: 'none', borderRadius: '4px', cursor: 'pointer',
                }}
              >
                + 创建规则
              </button>
            </div>
          </div>

          {/* Import Section */}
          {showImport && (
            <div style={{
              padding: '16px', background: '#f9f9f9', borderRadius: '8px',
              marginBottom: '16px', border: '1px solid #eee',
            }}>
              <h4 style={{ marginTop: 0 }}>从 L2 文档提取规则</h4>
              <div style={{ display: 'flex', gap: '8px', marginBottom: '12px' }}>
                <input
                  value={importDocIds}
                  onChange={e => setImportDocIds(e.target.value)}
                  placeholder="文档ID（多个用逗号分隔）"
                  style={{ flex: 1, padding: '6px 12px', borderRadius: '4px', border: '1px solid #d9d9d9' }}
                />
                <button
                  onClick={handleExtractRules}
                  style={{
                    padding: '6px 16px', background: '#722ed1', color: 'white',
                    border: 'none', borderRadius: '4px', cursor: 'pointer',
                  }}
                >
                  提取候选规则
                </button>
              </div>
              {candidates.length > 0 && (
                <div>
                  <h4>候选规则列表</h4>
                  {candidates.map(c => (
                    <div key={c.rule_id} style={{
                      padding: '12px', background: 'white', borderRadius: '4px',
                      marginBottom: '8px', border: '1px solid #eee',
                      display: 'flex', justifyContent: 'space-between', alignItems: 'center',
                    }}>
                      <div>
                        <strong>{c.name}</strong> — 评分: {c.conclusion_score} | 等级: {c.conclusion_grade}
                        <div style={{ color: '#666', fontSize: '12px' }}>{c.description}</div>
                      </div>
                      <div style={{ display: 'flex', gap: '8px' }}>
                        <button
                          onClick={() => handleApproveCandidate(c.rule_id)}
                          style={{
                            padding: '4px 12px', background: '#52c41a', color: 'white',
                            border: 'none', borderRadius: '4px', cursor: 'pointer',
                          }}
                        >
                          通过
                        </button>
                        <button
                          onClick={() => handleRejectCandidate(c.rule_id)}
                          style={{
                            padding: '4px 12px', background: '#ff4d4f', color: 'white',
                            border: 'none', borderRadius: '4px', cursor: 'pointer',
                          }}
                        >
                          拒绝
                        </button>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}

          {/* Rules Table */}
          <table style={{ width: '100%', borderCollapse: 'collapse' }}>
            <thead>
              <tr style={{ borderBottom: '2px solid #eee', background: '#fafafa' }}>
                <th style={{ textAlign: 'left', padding: '12px 8px' }}>名称</th>
                <th style={{ textAlign: 'center', padding: '12px 8px' }}>维度</th>
                <th style={{ textAlign: 'center', padding: '12px 8px' }}>评分</th>
                <th style={{ textAlign: 'center', padding: '12px 8px' }}>等级</th>
                <th style={{ textAlign: 'center', padding: '12px 8px' }}>权重</th>
                <th style={{ textAlign: 'center', padding: '12px 8px' }}>模糊阈值</th>
                <th style={{ textAlign: 'center', padding: '12px 8px' }}>条件数</th>
                <th style={{ textAlign: 'center', padding: '12px 8px' }}>状态</th>
                <th style={{ textAlign: 'center', padding: '12px 8px' }}>命中</th>
                <th style={{ textAlign: 'center', padding: '12px 8px' }}>操作</th>
              </tr>
            </thead>
            <tbody>
              {rules.length === 0 ? (
                <tr>
                  <td colSpan={10} style={{ padding: '24px', textAlign: 'center', color: '#999' }}>
                    暂无规则，请点击"创建规则"添加
                  </td>
                </tr>
              ) : (
                rules.map(rule => (
                  <tr key={rule.rule_id} style={{ borderBottom: '1px solid #f0f0f0' }}>
                    <td style={{ padding: '12px 8px' }}>
                      <div style={{ fontWeight: 500 }}>{rule.name}</div>
                      {rule.description && (
                        <div style={{ color: '#999', fontSize: '12px', marginTop: '4px' }}>
                          {rule.description.length > 50 ? rule.description.slice(0, 50) + '...' : rule.description}
                        </div>
                      )}
                    </td>
                    <td style={{ textAlign: 'center', padding: '12px 8px' }}>
                      <span style={{
                        display: 'inline-block', padding: '2px 8px', borderRadius: '4px',
                        background: rule.dimension === 'technical' ? '#e6f7ff' : rule.dimension === 'economic' ? '#f6ffed' : '#f9f0ff',
                        color: rule.dimension === 'technical' ? '#1890ff' : rule.dimension === 'economic' ? '#52c41a' : '#722ed1',
                        fontSize: '12px', fontWeight: 500,
                      }}>
                        {rule.dimension === 'technical' ? '技术' : rule.dimension === 'economic' ? '经济' : '环境'}
                      </span>
                    </td>
                    <td style={{ textAlign: 'center', padding: '12px 8px' }}>
                      <span style={{
                        display: 'inline-block', padding: '2px 8px', borderRadius: '4px',
                        background: getScoreColor(rule.conclusion_score) + '20',
                        color: getScoreColor(rule.conclusion_score), fontWeight: 500,
                      }}>
                        {rule.conclusion_score.toFixed(2)}
                      </span>
                    </td>
                    <td style={{ textAlign: 'center', padding: '12px 8px' }}>
                      <span style={{
                        display: 'inline-block', padding: '2px 8px', borderRadius: '4px',
                        background: getGradeColor(rule.conclusion_grade),
                        color: 'white', fontWeight: 500,
                      }}>
                        {rule.conclusion_grade}
                      </span>
                    </td>
                    <td style={{ textAlign: 'center', padding: '12px 8px' }}>{rule.weight}</td>
                    <td style={{ textAlign: 'center', padding: '12px 8px' }}>{rule.fuzzy_threshold?.toFixed(2) ?? '0.60'}</td>
                    <td style={{ textAlign: 'center', padding: '12px 8px' }}>
                      {rule.conditions.length > 0 ? (
                        <span title={rule.conditions.map(c => `${c.condition_type}: ${c.target_label}`).join('\n')}>
                          {rule.conditions.length}
                        </span>
                      ) : (
                        <span style={{ color: '#ccc' }}>0</span>
                      )}
                    </td>
                    <td style={{ textAlign: 'center', padding: '12px 8px' }}>
                      <span style={{
                        display: 'inline-block', padding: '2px 8px', borderRadius: '4px',
                        background: rule.status === 'active' ? '#f6ffed' : rule.status === 'disabled' ? '#fff1f0' : '#fffbe6',
                        color: rule.status === 'active' ? '#52c41a' : rule.status === 'disabled' ? '#ff4d4f' : '#faad14',
                        fontWeight: 500, cursor: 'pointer',
                      }} onClick={() => handleToggleStatus(rule)}>
                        {rule.status === 'active' ? '启用' : rule.status === 'disabled' ? '禁用' : '待审核'}
                      </span>
                    </td>
                    <td style={{ textAlign: 'center', padding: '12px 8px' }}>{rule.hit_count}</td>
                    <td style={{ textAlign: 'center', padding: '12px 8px' }}>
                      <div style={{ display: 'flex', gap: '8px', justifyContent: 'center' }}>
                        <button
                          onClick={() => openEditRule(rule)}
                          style={{
                            padding: '4px 12px', background: '#1890ff', color: 'white',
                            border: 'none', borderRadius: '4px', cursor: 'pointer', fontSize: '12px',
                          }}
                        >
                          编辑
                        </button>
                        {deleteConfirm === rule.rule_id ? (
                          <>
                            <button
                              onClick={() => handleDeleteRule(rule.rule_id)}
                              style={{
                                padding: '4px 12px', background: '#ff4d4f', color: 'white',
                                border: 'none', borderRadius: '4px', cursor: 'pointer', fontSize: '12px',
                              }}
                            >
                              确认删除
                            </button>
                            <button
                              onClick={() => setDeleteConfirm(null)}
                              style={{
                                padding: '4px 12px', background: '#f5f5f5', color: '#666',
                                border: '1px solid #d9d9d9', borderRadius: '4px', cursor: 'pointer', fontSize: '12px',
                              }}
                            >
                              取消
                            </button>
                          </>
                        ) : (
                          <button
                            onClick={() => setDeleteConfirm(rule.rule_id)}
                            style={{
                              padding: '4px 12px', background: '#ff4d4f', color: 'white',
                              border: 'none', borderRadius: '4px', cursor: 'pointer', fontSize: '12px',
                            }}
                          >
                            删除
                          </button>
                        )}
                      </div>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>

          {/* Rule Create/Edit Modal */}
          {showRuleForm && (
            <div style={{
              position: 'fixed', top: 0, left: 0, right: 0, bottom: 0,
              background: 'rgba(0,0,0,0.5)', display: 'flex', alignItems: 'center', justifyContent: 'center',
              zIndex: 1000,
            }}>
              <div style={{
                background: 'white', borderRadius: '8px', padding: '24px',
                width: '600px', maxHeight: '80vh', overflow: 'auto',
              }}>
                <h3 style={{ marginTop: 0 }}>{editingRule ? '编辑规则' : '创建规则'}</h3>

                {/* Name */}
                <div style={{ marginBottom: '16px' }}>
                  <label style={{ display: 'block', marginBottom: '4px', fontWeight: 500 }}>名称 *</label>
                  <input
                    value={ruleForm.name}
                    onChange={e => setRuleForm({ ...ruleForm, name: e.target.value })}
                    style={{ width: '100%', padding: '8px', borderRadius: '4px', border: '1px solid #d9d9d9' }}
                  />
                </div>

                {/* Description */}
                <div style={{ marginBottom: '16px' }}>
                  <label style={{ display: 'block', marginBottom: '4px', fontWeight: 500 }}>描述</label>
                  <textarea
                    value={ruleForm.description}
                    onChange={e => setRuleForm({ ...ruleForm, description: e.target.value })}
                    rows={2}
                    style={{ width: '100%', padding: '8px', borderRadius: '4px', border: '1px solid #d9d9d9', resize: 'vertical' }}
                  />
                </div>

                {/* Dimension */}
                <div style={{ marginBottom: '16px' }}>
                  <label style={{ display: 'block', marginBottom: '4px', fontWeight: 500 }}>评价维度</label>
                  <select
                    value={ruleForm.dimension}
                    onChange={e => setRuleForm({ ...ruleForm, dimension: e.target.value })}
                    style={{ width: '100%', padding: '8px', borderRadius: '4px', border: '1px solid #d9d9d9' }}
                  >
                    <option value="technical">技术维度</option>
                    <option value="economic">经济维度</option>
                    <option value="environmental">环境维度</option>
                  </select>
                </div>

                {/* Score & Grade */}
                <div style={{ display: 'flex', gap: '16px', marginBottom: '16px' }}>
                  <div style={{ flex: 1 }}>
                    <label style={{ display: 'block', marginBottom: '4px', fontWeight: 500 }}>
                      结论评分: {ruleForm.conclusion_score.toFixed(2)}
                    </label>
                    <input
                      type="range" min="0" max="1" step="0.1"
                      value={ruleForm.conclusion_score}
                      onChange={e => {
                        const score = parseFloat(e.target.value);
                        setRuleForm({
                          ...ruleForm,
                          conclusion_score: score,
                          conclusion_grade: recommendGrade(score),
                        });
                      }}
                      style={{ width: '100%' }}
                    />
                    <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '12px', color: '#999' }}>
                      <span>0 (不可再制造)</span><span>0.5 (合格)</span><span>1.0 (优秀)</span>
                    </div>
                  </div>
                  <div style={{ width: '120px' }}>
                    <label style={{ display: 'block', marginBottom: '4px', fontWeight: 500 }}>结论等级</label>
                    <select
                      value={ruleForm.conclusion_grade}
                      onChange={e => setRuleForm({ ...ruleForm, conclusion_grade: e.target.value })}
                      style={{ width: '100%', padding: '8px', borderRadius: '4px', border: '1px solid #d9d9d9' }}
                    >
                      <option value="优秀">优秀</option>
                      <option value="良好">良好</option>
                      <option value="合格">合格</option>
                      <option value="不可再制造">不可再制造</option>
                    </select>
                  </div>
                </div>

                {/* Weight */}
                <div style={{ marginBottom: '16px' }}>
                  <label style={{ display: 'block', marginBottom: '4px', fontWeight: 500 }}>权重</label>
                  <input
                    type="number" min="0" step="0.1"
                    value={ruleForm.weight}
                    onChange={e => setRuleForm({ ...ruleForm, weight: parseFloat(e.target.value) || 1.0 })}
                    style={{ width: '120px', padding: '8px', borderRadius: '4px', border: '1px solid #d9d9d9' }}
                  />
                </div>

                {/* Fuzzy Threshold */}
                <div style={{ marginBottom: '16px' }}>
                  <label style={{ display: 'block', marginBottom: '4px', fontWeight: 500 }}>
                    模糊匹配阈值: {ruleForm.fuzzy_threshold.toFixed(2)}
                  </label>
                  <input
                    type="range" min="0" max="1" step="0.05"
                    value={ruleForm.fuzzy_threshold}
                    onChange={e => setRuleForm({ ...ruleForm, fuzzy_threshold: parseFloat(e.target.value) || 0.6 })}
                    style={{ width: '100%' }}
                  />
                  <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '12px', color: '#999' }}>
                    <span>0 (宽松)</span><span>0.5</span><span>1.0 (严格)</span>
                  </div>
                </div>

                {/* Conditions */}
                <div style={{ marginBottom: '16px' }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px' }}>
                    <label style={{ fontWeight: 500 }}>条件列表</label>
                    <button
                      onClick={addCondition}
                      style={{
                        padding: '4px 12px', background: '#1890ff', color: 'white',
                        border: 'none', borderRadius: '4px', cursor: 'pointer', fontSize: '12px',
                      }}
                    >
                      + 添加条件
                    </button>
                  </div>
                  {ruleForm.conditions.map((cond, i) => (
                    <div key={i} style={{
                      display: 'flex', gap: '8px', marginBottom: '8px', alignItems: 'center',
                      padding: '8px', background: '#f9f9f9', borderRadius: '4px',
                    }}>
                      <select
                        value={cond.condition_type}
                        onChange={e => updateCondition(i, 'condition_type', e.target.value)}
                        style={{ padding: '6px', borderRadius: '4px', border: '1px solid #d9d9d9' }}
                      >
                        <option value="REQUIRES_CONNECTION">连接方式 (REQUIRES_CONNECTION)</option>
                        <option value="REQUIRES_TOOL">工具要求 (REQUIRES_TOOL)</option>
                        <option value="REQUIRES_STRUCTURE">结构特征 (REQUIRES_STRUCTURE)</option>
                        <option value="CONSTRAINED_BY">约束条件 (CONSTRAINED_BY)</option>
                      </select>
                      <input
                        value={cond.target_label}
                        onChange={e => updateCondition(i, 'target_label', e.target.value)}
                        placeholder="目标标签（如：螺栓连接）"
                        style={{ flex: 1, padding: '6px', borderRadius: '4px', border: '1px solid #d9d9d9' }}
                      />
                      <button
                        onClick={() => removeCondition(i)}
                        style={{
                          padding: '4px 8px', background: '#ff4d4f', color: 'white',
                          border: 'none', borderRadius: '4px', cursor: 'pointer',
                        }}
                      >
                        ×
                      </button>
                    </div>
                  ))}
                  {ruleForm.conditions.length === 0 && (
                    <div style={{ color: '#999', fontSize: '12px', padding: '8px' }}>
                      无条件 — 规则将始终匹配
                    </div>
                  )}
                </div>

                {/* Actions */}
                <div style={{ display: 'flex', gap: '8px', justifyContent: 'flex-end', marginTop: '24px' }}>
                  <button
                    onClick={() => setShowRuleForm(false)}
                    style={{
                      padding: '8px 16px', background: '#f5f5f5', color: '#666',
                      border: '1px solid #d9d9d9', borderRadius: '4px', cursor: 'pointer',
                    }}
                  >
                    取消
                  </button>
                  <button
                    onClick={handleSaveRule}
                    disabled={!ruleForm.name}
                    style={{
                      padding: '8px 16px', background: ruleForm.name ? '#1890ff' : '#d9d9d9',
                      color: 'white', border: 'none', borderRadius: '4px',
                      cursor: ruleForm.name ? 'pointer' : 'not-allowed',
                    }}
                  >
                    {editingRule ? '保存修改' : '创建规则'}
                  </button>
                </div>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
