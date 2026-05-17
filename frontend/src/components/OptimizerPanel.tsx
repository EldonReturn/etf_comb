import { useState, useMemo, useEffect } from 'react';
import type { ETFInfo, OptimizationResult, Weights } from '../api';

const CATEGORIES = ['全部', '宽基指数', '行业指数', '债券', '商品', '境外'];

interface OptimizerPanelProps {
  availableETFs: ETFInfo[];
  onOptimized: (weights: Weights) => void;
  timeRange?: string;
  selectedETFs: string[];
  onSelectionChange: (codes: string[]) => void;
}

export function OptimizerPanel({ availableETFs, onOptimized, timeRange = '1y', selectedETFs: externalSelected, onSelectionChange }: OptimizerPanelProps) {
  const [maxWeight, setMaxWeight] = useState<number | undefined>(undefined);
  const [targetVolatility, setTargetVolatility] = useState<number | undefined>(undefined);
  const [optimizing, setOptimizing] = useState(false);
  const [result, setResult] = useState<OptimizationResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [category, setCategory] = useState('全部');
  const [searchTerm, setSearchTerm] = useState('');

  const selectedETFs = externalSelected;

  useEffect(() => {
    const insufficient = availableETFs.filter((e) => e.has_enough_data === false).map((e) => e.code);
    const filtered = selectedETFs.filter((code) => !insufficient.includes(code));
    if (filtered.length !== selectedETFs.length) {
      onSelectionChange(filtered);
    }
  }, [availableETFs, selectedETFs, onSelectionChange]);

  const filteredETFs = useMemo(() => {
    return availableETFs.filter((etf) => {
      const matchCategory = category === '全部' || etf.category === category;
      const matchSearch =
        !searchTerm ||
        etf.code.toLowerCase().includes(searchTerm.toLowerCase()) ||
        etf.name.toLowerCase().includes(searchTerm.toLowerCase());
      return matchCategory && matchSearch;
    });
  }, [availableETFs, category, searchTerm]);

  const handleETFChange = (code: string) => {
    const etf = availableETFs.find((e) => e.code === code);
    if (etf?.has_enough_data === false) return;
    const newSelected = selectedETFs.includes(code)
      ? selectedETFs.filter((c) => c !== code)
      : [...selectedETFs, code];
    onSelectionChange(newSelected);
  };

  const handleSelectAll = () => {
    const selectable = filteredETFs.filter((etf) => etf.has_enough_data !== false).map((etf) => etf.code);
    const newSelected = selectedETFs.length === selectable.length
      ? []
      : selectable;
    onSelectionChange(newSelected);
  };

  const handleSelectByCategory = (cat: string) => {
    let newCodes: string[];
    if (cat === '全部') {
      newCodes = filteredETFs.filter((etf) => etf.has_enough_data !== false).map((etf) => etf.code);
    } else {
      newCodes = filteredETFs.filter((etf) => etf.category === cat && etf.has_enough_data !== false).map((etf) => etf.code);
    }
    const newSelected = [...new Set([...selectedETFs, ...newCodes])];
    onSelectionChange(Array.from(newSelected));
  };

  const handleOptimize = async () => {
    if (selectedETFs.length < 2) {
      setError('请至少选择2只ETF进行优化');
      return;
    }

    setOptimizing(true);
    setError(null);
    setResult(null);

    try {
      const response = await fetch('/api/portfolio/optimize', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          etf_codes: selectedETFs,
          max_weight: maxWeight,
          target_volatility: targetVolatility,
          period: timeRange,
        }),
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || '优化失败');
      }

      const data: OptimizationResult = await response.json();
      setResult(data);

      if (data.success && data.weights) {
        onOptimized(data.weights);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : '优化失败');
    } finally {
      setOptimizing(false);
    }
  };

  const handleApplyResult = () => {
    if (result?.weights) {
      onOptimized(result.weights);
    }
  };

  return (
    <div className="optimizer-panel">
      <div className="panel-header">
        <h3>最优组合优化</h3>
      </div>

      <div className="panel-body">
        <div className="optimize-section">
          <div className="section-header">
            <h4>选择ETF范围</h4>
            <button className="btn-text" onClick={handleSelectAll}>
              {selectedETFs.length === filteredETFs.length ? '取消全选' : '全选'}
            </button>
          </div>

          <div className="optimizer-controls">
            <input
              type="text"
              placeholder="搜索ETF名称或代码..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="optimizer-search-input"
            />
            <select
              value={category}
              onChange={(e) => setCategory(e.target.value)}
              className="optimizer-category-select"
            >
              {CATEGORIES.map((cat) => (
                <option key={cat} value={cat}>
                  {cat}
                </option>
              ))}
            </select>
          </div>

          <div className="category-quick-select">
            {CATEGORIES.filter((c) => c !== '全部').map((cat) => (
              <button
                key={cat}
                className="btn-category"
                onClick={() => handleSelectByCategory(cat)}
              >
                {cat}
              </button>
            ))}
          </div>

          <div className="etf-checklist">
            {filteredETFs.map((etf) => (
              <label key={etf.code} className={`etf-checkbox ${etf.has_enough_data === false ? 'data-insufficient' : ''}`}>
                <input
                  type="checkbox"
                  checked={selectedETFs.includes(etf.code)}
                  disabled={etf.has_enough_data === false}
                  onChange={() => handleETFChange(etf.code)}
                />
                <span className="etf-code">{etf.code}</span>
                <span className="etf-name">{etf.name}</span>
                {etf.has_enough_data === false && <span className="etf-warning" title="数据不足当前周期">!</span>}
              </label>
            ))}
          </div>

          <div className="selected-count">
            已选择: {selectedETFs.length} 只ETF
          </div>
        </div>

        <div className="optimize-section">
          <h4>优化约束（可选）</h4>

          <div className="constraint-field">
            <label>
              单个ETF最大权重 (%)
              <input
                type="number"
                min="0"
                max="100"
                placeholder="不限制"
                value={maxWeight ?? ''}
                onChange={(e) =>
                  setMaxWeight(e.target.value ? parseFloat(e.target.value) : undefined)
                }
              />
            </label>
          </div>

          <div className="constraint-field">
            <label>
              目标波动率上限 (%)
              <input
                type="number"
                min="0"
                max="100"
                placeholder="不限制"
                value={targetVolatility ?? ''}
                onChange={(e) =>
                  setTargetVolatility(
                    e.target.value ? parseFloat(e.target.value) : undefined
                  )
                }
              />
            </label>
          </div>
        </div>

        {error && <div className="error-message">{error}</div>}

        <button
          className="btn-primary optimize-btn"
          onClick={handleOptimize}
          disabled={optimizing || selectedETFs.length < 2}
        >
          {optimizing ? '优化中...' : '开始优化'}
        </button>

        {result && (
          <div className={`optimize-result ${result.success ? 'success' : 'failure'}`}>
            <div className="result-header">
              <span className="result-status">
                {result.success ? '优化成功' : '优化失败'}
              </span>
              <span className="result-message">{result.message}</span>
            </div>

            {result.success && (
              <>
                <div className="result-metrics">
                  <div className="result-metric">
                    <span className="metric-label">预期收益</span>
                    <span className="metric-value">
                      {result.expected_return.toFixed(2)}%
                    </span>
                  </div>
                  <div className="result-metric">
                    <span className="metric-label">波动率</span>
                    <span className="metric-value">
                      {result.volatility.toFixed(2)}%
                    </span>
                  </div>
                  <div className="result-metric">
                    <span className="metric-label">夏普比率</span>
                    <span className="metric-value">
                      {result.sharpe_ratio.toFixed(4)}
                    </span>
                  </div>
                </div>

                <div className="result-weights">
                  <h5>最优权重</h5>
                  {Object.entries(result.weights).map(([code, weight]) => (
                    <div key={code} className="weight-item">
                      <span className="weight-code">{code}</span>
                      <span className="weight-value">
                        {(weight * 100).toFixed(1)}%
                      </span>
                      <div className="weight-bar">
                        <div
                          className="weight-fill"
                          style={{ width: `${weight * 100}%` }}
                        />
                      </div>
                    </div>
                  ))}
                </div>

                <button className="btn-secondary" onClick={handleApplyResult}>
                  应用此组合
                </button>
              </>
            )}
          </div>
        )}
      </div>
    </div>
  );
}