import { useState, useEffect, useCallback } from 'react';
import type { ETFInfo, Weights } from '../api';

/**
 * ETFSelector - ETF多选组件
 *
 * 功能：
 * - 支持搜索过滤ETF
 * - 支持按分类筛选
 * - 支持多选组成组合
 * - 显示已选ETF及权重调整
 *
 * Props:
 * - selectedETFs: 已选择的ETF及其权重
 * - onChange: 权重变化回调
 */

interface ETFSelectorProps {
  selectedETFs: Weights;
  onChange: (weights: Weights) => void;
  period?: string;
}

const CATEGORIES = ['全部', '宽基指数', '行业指数', '债券', '商品', '境外'];

export function ETFSelector({ selectedETFs, onChange, period }: ETFSelectorProps) {
  const [etfList, setEtfList] = useState<ETFInfo[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [searchTerm, setSearchTerm] = useState('');
  const [category, setCategory] = useState('全部');

  const loadETFList = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const params = new URLSearchParams();
      if (category !== '全部') params.append('category', category);
      if (searchTerm) params.append('search', searchTerm);
      if (period) params.append('period', period);

      const url = `/api/etfs${params.toString() ? '?' + params.toString() : ''}`;
      const response = await fetch(url);
      if (!response.ok) throw new Error('获取ETF列表失败');
      const data = await response.json();
      setEtfList(data.etfs || []);
    } catch (err) {
      setError(err instanceof Error ? err.message : '未知错误');
      setEtfList([]);
    } finally {
      setLoading(false);
    }
  }, [category, searchTerm, period]);

  useEffect(() => {
    loadETFList();
  }, [loadETFList]);

  const handleETFToggle = (code: string) => {
    const newWeights = { ...selectedETFs };
    if (newWeights[code]) {
      delete newWeights[code];
      const remainingKeys = Object.keys(newWeights);
      if (remainingKeys.length > 0) {
        const total = Object.values(newWeights).reduce((a, b) => a + b, 0);
        remainingKeys.forEach((k) => {
          newWeights[k] = newWeights[k] / total;
        });
      }
    } else {
      newWeights[code] = 1 / (Object.keys(selectedETFs).length + 1);
      const otherCount = Object.keys(newWeights).length - 1;
      if (otherCount > 0) {
        const equalWeight = 1 / (otherCount + 1);
        Object.keys(newWeights).forEach((k) => {
          newWeights[k] = equalWeight;
        });
      }
    }
    onChange(newWeights);
  };

  const handleWeightChange = (code: string, newWeight: number) => {
    const newWeights = { ...selectedETFs };
    const oldWeight = newWeights[code] || 0;
    const diff = newWeight - oldWeight;

    if (diff > 0) {
      const otherKeys = Object.keys(newWeights).filter((k) => k !== code);
      if (otherKeys.length > 0) {
        const reduceAmount = diff / otherKeys.length;
        otherKeys.forEach((k) => {
          newWeights[k] = Math.max(0, newWeights[k] - reduceAmount);
        });
      }
    } else {
      const otherKeys = Object.keys(newWeights).filter((k) => k !== code);
      if (otherKeys.length > 0) {
        const addAmount = -diff / otherKeys.length;
        otherKeys.forEach((k) => {
          newWeights[k] = Math.max(0, newWeights[k] + addAmount);
        });
      }
    }

    newWeights[code] = Math.max(0, Math.min(1, newWeight));
    const total = Object.values(newWeights).reduce((a, b) => a + b, 0);
    if (total > 0) {
      Object.keys(newWeights).forEach((k) => {
        newWeights[k] = newWeights[k] / total;
      });
    }

    onChange(newWeights);
  };

  const selectedCodes = Object.keys(selectedETFs);

  return (
    <div className="etf-selector">
      <div className="selector-header">
        <h3>选择ETF</h3>
        <div className="selector-controls">
          <input
            type="text"
            placeholder="搜索ETF名称或代码..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="search-input"
          />
          <select
            value={category}
            onChange={(e) => setCategory(e.target.value)}
            className="category-select"
          >
            {CATEGORIES.map((cat) => (
              <option key={cat} value={cat}>
                {cat}
              </option>
            ))}
          </select>
        </div>
      </div>

      <div className="selector-body">
        {loading && <div className="loading">加载中...</div>}
        {error && <div className="error">{error}</div>}

        <div className="etf-list">
          {(() => {
            const sufficientEtfs = etfList.filter(e => e.has_enough_data !== false);
            const insufficientEtfs = etfList.filter(e => e.has_enough_data === false);
            const sortedList = [...sufficientEtfs, ...insufficientEtfs];

            return sortedList.map((etf) => {
              const isSelected = !!selectedETFs[etf.code];
              return (
                <div
                  key={etf.code}
                  className={`etf-item ${isSelected ? 'selected' : ''} ${etf.has_enough_data === false ? 'data-insufficient' : ''}`}
                  onClick={() => handleETFToggle(etf.code)}
                >
                  <div className="etf-info">
                    <span className="etf-code">{etf.code}</span>
                    <span className="etf-name">{etf.name}</span>
                    <span className="etf-category">{etf.category}</span>
                    {etf.has_enough_data === false && (
                      <span className="etf-warning" title="数据不足当前周期">!</span>
                    )}
                  </div>
                  {isSelected && (
                    <div className="etf-weight" onClick={(e) => e.stopPropagation()}>
                      <input
                        type="number"
                        min="0"
                        max="100"
                        value={(selectedETFs[etf.code] * 100).toFixed(1)}
                        onChange={(e) =>
                          handleWeightChange(etf.code, parseFloat(e.target.value) / 100)
                        }
                        className="weight-input"
                      />
                      <span className="weight-unit">%</span>
                    </div>
                  )}
                </div>
              );
            });
          })()}
        </div>
      </div>

      <div className="selected-section">
        <h4>已选组合 ({selectedCodes.length}只)</h4>
        <div className="selected-list">
          {selectedCodes.length > 0 ? (
            selectedCodes.map((code) => {
              const etf = etfList.find((e) => e.code === code);
              return (
                <div key={code} className="selected-item">
                  <span className="selected-code">{code}</span>
                  <span className="selected-name">{etf?.name || ''}</span>
                  <span className="selected-weight">
                    {(selectedETFs[code] * 100).toFixed(1)}%
                  </span>
                  <button
                    className="selected-remove"
                    onClick={() => handleETFToggle(code)}
                    title="移除"
                  >
                    ×
                  </button>
                </div>
              );
            })
          ) : (
            <div className="selected-empty">暂无选择，请在上方列表中点击ETF进行选择</div>
          )}
        </div>
      </div>
    </div>
  );
}