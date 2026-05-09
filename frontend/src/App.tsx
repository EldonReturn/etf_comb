/**
 * ETF组合推荐系统 - 主应用组件
 *
 * 功能布局：
 * - 左侧：ETF选择器
 * - 中间：当前组合详情
 * - 右侧：最优组合优化
 * - 底部：多组合对比
 */

import { useState, useEffect } from 'react';
import type { ETFInfo, Weights } from './api';
import { ETFSelector, PortfolioCard, CompareTable, OptimizerPanel } from './components';
import './App.css';

type ViewMode = 'single' | 'compare';

function App() {
  const [etfList, setEtfList] = useState<ETFInfo[]>([]);
  const [currentWeights, setCurrentWeights] = useState<Weights>({});
  const [savedPortfolios, setSavedPortfolios] = useState<Weights[]>([]);
  const [viewMode, setViewMode] = useState<ViewMode>('single');
  const [systemStatus, setSystemStatus] = useState<string>('检查中...');

  useEffect(() => {
    const checkStatus = async () => {
      try {
        const response = await fetch('/api/../');
        if (response.ok) {
          const data = await response.json();
          setSystemStatus(data.status || 'running');
        }
      } catch {
        setSystemStatus('disconnected');
      }
    };
    checkStatus();
    const interval = setInterval(checkStatus, 30000);
    return () => clearInterval(interval);
  }, []);

  const handleWeightsChange = (weights: Weights) => {
    setCurrentWeights(weights);
  };

  const handleOptimized = (weights: Weights) => {
    setCurrentWeights(weights);
  };

  const handleSavePortfolio = () => {
    if (Object.keys(currentWeights).length > 0) {
      setSavedPortfolios((prev) => [...prev, { ...currentWeights }]);
    }
  };

  const handleRemovePortfolio = (index: number) => {
    setSavedPortfolios((prev) => prev.filter((_, i) => i !== index));
  };

  const availableETFCodes = etfList.map((e) => e.code);

  return (
    <div className="app">
      <header className="app-header">
        <h1>ETF组合推荐系统</h1>
        <div className="header-status">
          <span className={`status-indicator ${systemStatus}`} />
          <span className="status-text">
            {systemStatus === 'running' ? '系统正常' : systemStatus === 'disconnected' ? '未连接后端' : systemStatus}
          </span>
        </div>
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

        {viewMode === 'single' && Object.keys(currentWeights).length > 0 && (
          <button className="btn-secondary" onClick={handleSavePortfolio}>
            保存当前组合
          </button>
        )}
      </div>

      <main className="app-main">
        <aside className="sidebar-left">
          <ETFSelector selectedETFs={currentWeights} onChange={handleWeightsChange} />
        </aside>

        <section className="main-content">
          {viewMode === 'single' ? (
            <PortfolioCard weights={currentWeights} name="当前组合" />
          ) : (
            <div className="compare-mode-content">
              <div className="current-portfolio">
                <PortfolioCard weights={currentWeights} name="当前组合" />
              </div>

              {savedPortfolios.length > 0 && (
                <CompareTable
                  portfolios={[currentWeights, ...savedPortfolios]}
                  onRemove={handleRemovePortfolio}
                />
              )}
            </div>
          )}
        </section>

        <aside className="sidebar-right">
          <OptimizerPanel
            availableETFs={availableETFCodes}
            onOptimized={handleOptimized}
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
              />
            ))}
          </div>
          <CompareTable portfolios={savedPortfolios} onRemove={handleRemovePortfolio} />
        </section>
      )}
    </div>
  );
}

export default App;