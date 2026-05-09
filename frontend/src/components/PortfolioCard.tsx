import { useState, useEffect } from 'react';
import type { Weights, PortfolioMetrics } from '../api';

/**
 * PortfolioCard - 组合详情卡片组件
 *
 * 功能：
 * - 显示组合的各项业绩指标
 * - 展示净值曲线图表
 * - 展示回撤曲线图表
 *
 * Props:
 * - weights: 组合权重
 * - id: 组合ID（用于标题）
 */

interface PortfolioCardProps {
  weights: Weights;
  id?: number;
  name?: string;
}

type MetricCardProps = {
  label: string;
  value: number;
  suffix?: string;
  color?: string;
};

function MetricCard({ label, value, suffix = '', color }: MetricCardProps) {
  const displayValue = value.toFixed(2);
  const isPositive = value > 0;
  const isNegative = value < 0;

  const valueColor = color || (isNegative ? '#e74c3c' : isPositive ? '#27ae60' : 'inherit');

  return (
    <div className="metric-card">
      <span className="metric-label">{label}</span>
      <span className="metric-value" style={{ color: valueColor }}>
        {isNegative && value !== 0 ? '-' : ''}
        {displayValue}
        {suffix}
      </span>
    </div>
  );
}

export function PortfolioCard({ weights, id, name }: PortfolioCardProps) {
  const [metrics, setMetrics] = useState<PortfolioMetrics | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [activeChart, setActiveChart] = useState<'nav' | 'drawdown'>('nav');

  useEffect(() => {
    if (Object.keys(weights).length === 0) {
      setMetrics(null);
      return;
    }

    const loadMetrics = async () => {
      setLoading(true);
      setError(null);
      try {
        const response = await fetch('/api/portfolio/evaluate', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ weights }),
        });
        if (!response.ok) throw new Error('评估失败');
        const data = await response.json();
        setMetrics(data);
      } catch (err) {
        setError(err instanceof Error ? err.message : '未知错误');
      } finally {
        setLoading(false);
      }
    };

    loadMetrics();
  }, [weights]);

  const renderNavChart = () => {
    if (!metrics?.nav_series || metrics.nav_series.length === 0) {
      return <div className="chart-placeholder">暂无净值数据</div>;
    }

    const navData = metrics.nav_series.map((nav, index) => ({
      index,
      value: nav,
    }));

    const maxNav = Math.max(...navData.map((d) => d.value));
    const minNav = Math.min(...navData.map((d) => d.value));
    const normalizedData = navData.map((d) => ({
      ...d,
      value: ((d.value - minNav) / (maxNav - minNav || 1)) * 100,
    }));

    return (
      <svg viewBox="0 0 400 150" className="chart-svg">
        <polyline
          points={normalizedData.map((d) => `${(d.index / (navData.length - 1)) * 380 + 10},${150 - d.value}`).join(' ')}
          fill="none"
          stroke="#3498db"
          strokeWidth="2"
        />
      </svg>
    );
  };

  const renderDrawdownChart = () => {
    if (!metrics?.nav_series || metrics.nav_series.length === 0) {
      return <div className="chart-placeholder">暂无回撤数据</div>;
    }

    const navSeries = metrics.nav_series;
    const drawdownData: { index: number; value: number }[] = [];

    let peak = navSeries[0];
    for (let i = 0; i < navSeries.length; i++) {
      if (navSeries[i] > peak) {
        peak = navSeries[i];
      }
      const drawdown = ((navSeries[i] - peak) / peak) * 100;
      drawdownData.push({ index: i, value: drawdown });
    }

    const maxDD = Math.min(...drawdownData.map((d) => d.value));
    const normalizedData = drawdownData.map((d) => ({
      ...d,
      value: d.value - maxDD,
    }));

    return (
      <svg viewBox="0 0 400 150" className="chart-svg">
        <polyline
          points={normalizedData.map((d) => `${(d.index / (drawdownData.length - 1)) * 380 + 10},${150 - Math.max(0, d.value)}`).join(' ')}
          fill="none"
          stroke="#e74c3c"
          strokeWidth="2"
        />
      </svg>
    );
  };

  if (Object.keys(weights).length === 0) {
    return (
      <div className="portfolio-card empty">
        <div className="card-header">
          <h3>{name || `组合${id || ''}`}</h3>
        </div>
        <div className="card-body">
          <div className="empty-message">请从左侧选择ETF构建组合</div>
        </div>
      </div>
    );
  }

  return (
    <div className="portfolio-card">
      <div className="card-header">
        <h3>{name || `组合${id || ''}`}</h3>
        {loading && <span className="loading-badge">评估中...</span>}
      </div>

      <div className="card-body">
        {error && <div className="error-message">{error}</div>}

        {metrics && (
          <>
            <div className="metrics-grid">
              <MetricCard
                label="累计收益"
                value={metrics.total_return}
                suffix="%"
              />
              <MetricCard
                label="年化收益"
                value={metrics.annualized_return}
                suffix="%"
              />
              <MetricCard
                label="波动率"
                value={metrics.volatility}
                suffix="%"
              />
              <MetricCard
                label="夏普比率"
                value={metrics.sharpe_ratio}
              />
              <MetricCard
                label="最大回撤"
                value={metrics.max_drawdown}
                suffix="%"
              />
              <MetricCard
                label="持有天数"
                value={metrics.holding_period}
              />
            </div>

            <div className="chart-section">
              <div className="chart-tabs">
                <button
                  className={`chart-tab ${activeChart === 'nav' ? 'active' : ''}`}
                  onClick={() => setActiveChart('nav')}
                >
                  净值曲线
                </button>
                <button
                  className={`chart-tab ${activeChart === 'drawdown' ? 'active' : ''}`}
                  onClick={() => setActiveChart('drawdown')}
                >
                  回撤曲线
                </button>
              </div>
              <div className="chart-container">
                {activeChart === 'nav' ? renderNavChart() : renderDrawdownChart()}
              </div>
            </div>

            <div className="etf-allocations">
              <h4>ETF配置</h4>
              <div className="allocation-list">
                {Object.entries(metrics.etf_metrics || {}).map(([code, etfMetrics]) => (
                  <div key={code} className="allocation-item">
                    <span className="allocation-code">{code}</span>
                    <span className="allocation-name">{etfMetrics.name}</span>
                    <div className="allocation-bar">
                      <div
                        className="allocation-fill"
                        style={{ width: `${etfMetrics.weight * 100}%` }}
                      />
                    </div>
                    <span className="allocation-weight">
                      {(etfMetrics.weight * 100).toFixed(1)}%
                    </span>
                  </div>
                ))}
              </div>
            </div>
          </>
        )}
      </div>
    </div>
  );
}