/**
 * ETF组合推荐系统 - 主应用组件
 *
 * 功能布局：
 * - 左侧：ETF选择器
 * - 中间：当前组合详情
 * - 右侧：最优组合优化
 * - 底部：多组合对比
 */

import { useState, useEffect, useCallback } from 'react';
import type { ETFInfo, Weights } from './api';
import { ETFSelector, PortfolioCard, CompareTable, OptimizerPanel } from './components';
import './App.css';

type ViewMode = 'single' | 'compare';

type TimeRange = '1m' | '3m' | '6m' | '1y' | '2y' | '3y' | '5y';

const TIME_RANGES: { value: TimeRange; label: string }[] = [
  { value: '1m', label: '1个月' },
  { value: '3m', label: '3个月' },
  { value: '6m', label: '6个月' },
  { value: '1y', label: '1年' },
  { value: '2y', label: '2年' },
  { value: '3y', label: '3年' },
  { value: '5y', label: '5年' },
];

function App() {
  const [etfList, setEtfList] = useState<ETFInfo[]>([]);
  const [currentWeights, setCurrentWeights] = useState<Weights>({});
  const [optimizerSelected, setOptimizerSelected] = useState<string[]>([]);
  const [savedPortfolios, setSavedPortfolios] = useState<Weights[]>([]);
  const [viewMode, setViewMode] = useState<ViewMode>('single');
  const [timeRange, setTimeRange] = useState<TimeRange>('1y');
  const [syncing, setSyncing] = useState(false);
  const [syncMsg, setSyncMsg] = useState<string | null>(null);
  const [benchmarkCode, setBenchmarkCode] = useState<string>('510310');

  useEffect(() => {
    const fetchETFList = async () => {
      try {
        const response = await fetch(`/api/etfs?period=${timeRange}`);
        if (response.ok) {
          const data = await response.json();
          setEtfList(data.etfs || []);
        }
      } catch {
        setEtfList([]);
      }
    };
    fetchETFList();
  }, [timeRange]);

  const handleWeightsChange = (weights: Weights) => {
    setCurrentWeights(weights);
    setOptimizerSelected(Object.keys(weights));
  };

  const handleOptimized = (weights: Weights) => {
    setCurrentWeights(weights);
    setOptimizerSelected(Object.keys(weights));
  };

  const handleOptimizerSelectionChange = useCallback((codes: string[]) => {
    setOptimizerSelected(codes);
  }, []);

  const handleSavePortfolio = () => {
    if (Object.keys(currentWeights).length > 0) {
      setSavedPortfolios((prev) => [...prev, { ...currentWeights }]);
    }
  };

  const handleRemovePortfolio = (index: number) => {
    setSavedPortfolios((prev) => prev.filter((_, i) => i !== index));
  };

  const handleSync = async () => {
    setSyncing(true);
    setSyncMsg(null);
    try {
      const response = await fetch('/api/admin/sync', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ period: timeRange }),
      });
      const data = await response.json();
      if (response.ok) {
        setSyncMsg(`同步成功: ${data.etf_count}只ETF, ${data.nav_count}条净值`);
        setTimeout(() => setSyncMsg(null), 3000);
      } else {
        setSyncMsg(`同步失败: ${data.detail || '未知错误'}`);
      }
    } catch {
      setSyncMsg('同步失败: 网络错误');
    } finally {
      setSyncing(false);
    }
  };

  return (
    <div className="app">
      <header className="app-header">
        <h1>ETF组合推荐系统</h1>
      </header>

      <div className="app-toolbar">
        <div className="view-toggle">
          <button
            className={`toggle-btn ${viewMode === 'single' ? 'active' : ''}`}
            onClick={() => setViewMode('single')}
          >
            单组合
          </button>
          <button
            className={`toggle-btn ${viewMode === 'compare' ? 'active' : ''}`}
            onClick={() => setViewMode('compare')}
          >
            对比模式
          </button>
        </div>

        <div className="time-range-selector">
          <select
            value={timeRange}
            onChange={(e) => setTimeRange(e.target.value as TimeRange)}
            className="optimizer-category-select"
          >
            {TIME_RANGES.map((tr) => (
              <option key={tr.value} value={tr.value}>
                {tr.label}
              </option>
            ))}
          </select>
          <select
            value={benchmarkCode}
            onChange={(e) => setBenchmarkCode(e.target.value)}
            className="optimizer-category-select"
            title="基准ETF"
          >
            {etfList
              .filter((etf) => etf.has_enough_data !== false)
              .map((etf) => (
                <option key={etf.code} value={etf.code}>
                  基准: {etf.code} {etf.name}
                </option>
              ))}
          </select>
          <button
            className="btn-secondary"
            onClick={handleSync}
            disabled={syncing}
          >
            {syncing ? '同步中...' : '同步数据'}
          </button>
          {syncMsg && <span className="sync-message">{syncMsg}</span>}
        </div>

        {viewMode === 'single' && Object.keys(currentWeights).length > 0 && (
          <button className="btn-secondary" onClick={handleSavePortfolio}>
            保存当前组合
          </button>
        )}
      </div>

      <main className="app-main">
        <aside className="sidebar-left">
          <ETFSelector selectedETFs={currentWeights} onChange={handleWeightsChange} period={timeRange} />
        </aside>

        <section className="main-content">
          {viewMode === 'single' ? (
            <PortfolioCard weights={currentWeights} name="当前组合" timeRange={timeRange} benchmarkCode={benchmarkCode} />
          ) : (
            <div className="compare-mode-content">
              <div className="current-portfolio">
                <PortfolioCard weights={currentWeights} name="当前组合" timeRange={timeRange} benchmarkCode={benchmarkCode} />
              </div>

              {savedPortfolios.length > 0 && (
                <CompareTable
                  portfolios={[currentWeights, ...savedPortfolios]}
                  onRemove={handleRemovePortfolio}
                  timeRange={timeRange}
                  benchmarkCode={benchmarkCode}
                />
              )}
            </div>
          )}
        </section>

        <aside className="sidebar-right">
          <OptimizerPanel
            availableETFs={etfList}
            onOptimized={handleOptimized}
            timeRange={timeRange}
            selectedETFs={optimizerSelected}
            onSelectionChange={handleOptimizerSelectionChange}
          />
        </aside>
      </main>

      {savedPortfolios.length > 0 && viewMode === 'single' && (
        <section className="saved-portfolios">
          <h3>已保存的组合</h3>
          <div className="saved-list">
            {savedPortfolios.map((weights, index) => (
              <PortfolioCard
                key={index}
                weights={weights}
                id={index + 1}
                name={`已保存组合${index + 1}`}
                timeRange={timeRange}
                benchmarkCode={benchmarkCode}
              />
            ))}
          </div>
          <CompareTable portfolios={savedPortfolios} onRemove={handleRemovePortfolio} timeRange={timeRange} benchmarkCode={benchmarkCode} />
        </section>
      )}
    </div>
  );
}

export default App;