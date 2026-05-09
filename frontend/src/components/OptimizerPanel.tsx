import { useState } from 'react';
import type { OptimizationResult, Weights } from '../api';

/**
 * OptimizerPanel - 最优组合优化面板组件
 *
 * 功能：
 * - 选择用于优化的ETF范围
 * - 设置优化约束条件
 * - 触发优化计算
 * - 显示最优组合结果
 *
 * Props:
 * - availableETFs: 可选的ETF代码列表
 * - onOptimized: 最优组合结果回调
 */

interface OptimizerPanelProps {
  availableETFs: string[];
  onOptimized: (weights: Weights) => void;
}

export function OptimizerPanel({ availableETFs, onOptimized }: OptimizerPanelProps) {
  const [selectedETFs, setSelectedETFs] = useState<string[]>([]);
  const [maxWeight, setMaxWeight] = useState<number | undefined>(undefined);
  const [targetVolatility, setTargetVolatility] = useState<number | undefined>(undefined);
  const [optimizing, setOptimizing] = useState(false);
  const [result, setResult] = useState<OptimizationResult | null>(null);
  const [error, setError] = useState<string | null>(null);

  const handleETFChange = (code: string) => {
    setSelectedETFs((prev) => {
      if (prev.includes(code)) {
        return prev.filter((c) => c !== code);
      }
      return [...prev, code];
    });
  };

  const handleSelectAll = () => {
    if (selectedETFs.length === availableETFs.length) {
      setSelectedETFs([]);
    } else {
      setSelectedETFs([...availableETFs]);
    }
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
              {selectedETFs.length === availableETFs.length ? '取消全选' : '全选'}
            </button>
          </div>

          <div className="etf-checklist">
            {availableETFs.map((code) => (
              <label key={code} className="etf-checkbox">
                <input
                  type="checkbox"
                  checked={selectedETFs.includes(code)}
                  onChange={() => handleETFChange(code)}
                />
                <span>{code}</span>
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