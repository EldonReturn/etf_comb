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

    const benchmarkNavData = (metrics.benchmark_nav_series || []).map((nav, index) => ({
      index,
      value: nav,
    }));

    const allValues = [...navData.map(d => d.value), ...benchmarkNavData.map(d => d.value)];
    const maxNav = Math.max(...allValues);
    const minNav = Math.min(...allValues);
    const valueRange = maxNav - minNav || 1;

    const xLabels = [];
    const formatDate = (dateStr: string) => {
      const date = new Date(dateStr);
      const yy = date.getFullYear().toString().slice(2);
      const mm = (date.getMonth() + 1).toString().padStart(2, '0');
      const dd = date.getDate().toString().padStart(2, '0');
      return `${yy}${mm}${dd}`;
    };
    if (navData.length > 0) {
      const totalLen = navData.length - 1 || 1;
      if (navData.length === 1) {
        xLabels.push({
          index: 0,
          label: metrics.nav_dates?.[0] ? formatDate(metrics.nav_dates[0]) : '1',
        });
      } else {
        xLabels.push({
          index: 0,
          label: metrics.nav_dates?.[0] ? formatDate(metrics.nav_dates[0]) : '1',
        });
        xLabels.push({
          index: navData.length - 1,
          label: metrics.nav_dates?.[navData.length - 1]
            ? formatDate(metrics.nav_dates[navData.length - 1])
            : `${navData.length}`,
        });
      }
    }

    const yLabels = [];
    for (let i = 0; i <= 4; i++) {
      const value = minNav + (valueRange * i) / 4;
      yLabels.push({ value: value.toFixed(2), y: 190 - (i / 4) * 170 });
    }

    const rightYLabels = [];
    const navInitialValue = navData[0]?.value || 1;
    const benchmarkInitialValue = benchmarkNavData[0]?.value || 1;
    const excessValues = navData.map((d, i) => {
      const benchmarkValue = benchmarkNavData[i]?.value || d.value;
      return ((d.value - benchmarkValue - (navInitialValue - benchmarkInitialValue)) / benchmarkInitialValue) * 100;
    });
    const maxExcess = Math.max(...excessValues);
    const minExcess = Math.min(...excessValues);
    const excessRange = Math.max(Math.abs(maxExcess), Math.abs(minExcess), 0.01);
    for (let i = 0; i <= 4; i++) {
      const pct = -excessRange + (excessRange * 2 * i) / 4;
      rightYLabels.push({ value: `${pct >= 0 ? '+' : ''}${pct.toFixed(1)}%`, y: 190 - (i / 4) * 170 });
    }

    return (
      <svg viewBox="0 0 540 220" className="chart-svg">
        <line x1="50" y1="15" x2="50" y2="190" stroke="var(--border)" strokeWidth="1" />
        <line x1="50" y1="190" x2="535" y2="190" stroke="var(--border)" strokeWidth="1" />
        {xLabels.map(({ index, label }) => (
          <g key={index}>
            <line x1={50 + (index / (navData.length - 1)) * 485} y1="190" x2={50 + (index / (navData.length - 1)) * 485} y2="193" stroke="var(--border)" strokeWidth="1" />
            <text x={50 + (index / (navData.length - 1)) * 485} y="205" fontSize="10" fill="var(--text-light)" textAnchor="middle">{label}</text>
          </g>
        ))}
        {yLabels.map(({ value, y }) => (
          <g key={y}>
            <line x1="47" y1={y} x2="50" y2={y} stroke="var(--border)" strokeWidth="1" />
            <text x="45" y={y + 4} fontSize="10" fill="var(--text-light)" textAnchor="end">{value}</text>
          </g>
        ))}
        {rightYLabels.map(({ value, y }) => (
          <g key={y}>
            <line x1="535" y1={y} x2="538" y2={y} stroke="var(--border)" strokeWidth="1" />
            <text x="543" y={y + 4} fontSize="10" fill="#9b59b6" textAnchor="start">{value}</text>
          </g>
        ))}
        {benchmarkNavData.length > 0 && (
          <polyline
            points={benchmarkNavData.map((d) => `${50 + (d.index / (navData.length - 1)) * 485},${190 - ((d.value - minNav) / valueRange) * 170}`).join(' ')}
            fill="none"
            stroke="#555"
            strokeWidth="2"
          />
        )}
        {excessValues.length > 0 && (
          <polyline
            points={excessValues.map((v, i) => `${50 + (i / (navData.length - 1)) * 485},${190 - ((v / excessRange) + 1) * 85}`).join(' ')}
            fill="none"
            stroke="#9b59b6"
            strokeWidth="2"
          />
        )}
        <polyline
          points={navData.map((d) => `${50 + (d.index / (navData.length - 1)) * 485},${190 - ((d.value - minNav) / valueRange) * 170}`).join(' ')}
          fill="none"
          stroke="#e74c3c"
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

    const xLabels = [];
    const formatDate = (dateStr: string) => {
      const date = new Date(dateStr);
      const yy = date.getFullYear().toString().slice(2);
      const mm = (date.getMonth() + 1).toString().padStart(2, '0');
      const dd = date.getDate().toString().padStart(2, '0');
      return `${yy}${mm}${dd}`;
    };
    if (drawdownData.length > 0) {
      if (drawdownData.length === 1) {
        xLabels.push({
          index: 0,
          label: metrics.nav_dates?.[0] ? formatDate(metrics.nav_dates[0]) : '1',
        });
      } else {
        xLabels.push({
          index: 0,
          label: metrics.nav_dates?.[0] ? formatDate(metrics.nav_dates[0]) : '1',
        });
        xLabels.push({
          index: drawdownData.length - 1,
          label: metrics.nav_dates?.[drawdownData.length - 1]
            ? formatDate(metrics.nav_dates[drawdownData.length - 1])
            : `${drawdownData.length}`,
        });
      }
    }

    const yLabels = [];
    for (let i = 0; i <= 4; i++) {
      const value = ((Math.abs(maxDD) * i) / 4).toFixed(1);
      yLabels.push({ value, y: 190 - (i / 4) * 170 });
    }

    return (
      <svg viewBox="0 0 540 220" className="chart-svg">
        <line x1="50" y1="15" x2="50" y2="190" stroke="var(--border)" strokeWidth="1" />
        <line x1="50" y1="190" x2="535" y2="190" stroke="var(--border)" strokeWidth="1" />
        {xLabels.map(({ index, label }) => (
          <g key={index}>
            <line x1={50 + (index / (drawdownData.length - 1)) * 485} y1="190" x2={50 + (index / (drawdownData.length - 1)) * 485} y2="193" stroke="var(--border)" strokeWidth="1" />
            <text x={50 + (index / (drawdownData.length - 1)) * 485} y="205" fontSize="10" fill="var(--text-light)" textAnchor="middle">{label}</text>
          </g>
        ))}
        {yLabels.map(({ value, y }) => (
          <g key={y}>
            <line x1="47" y1={y} x2="50" y2={y} stroke="var(--border)" strokeWidth="1" />
            <text x="45" y={y + 4} fontSize="10" fill="var(--text-light)" textAnchor="end">{value}%</text>
          </g>
        ))}
        <polyline
          points={drawdownData.map((d) => `${50 + (d.index / (drawdownData.length - 1)) * 485},${190 - (Math.abs(d.value) / Math.abs(maxDD || 1)) * 170}`).join(' ')}
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