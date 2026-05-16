import { useState, useEffect } from 'react';
import type { Weights, PortfolioMetrics } from '../api';

/**
 * CompareTable - 多组合对比表格组件
 *
 * 功能：
 * - 并列显示多个组合的业绩指标
 * - 支持柱状图对比
 * - 支持雷达图对比
 *
 * Props:
 * - portfolios: 多个组合的权重列表
 */

interface CompareTableProps {
  portfolios: Weights[];
  onRemove?: (index: number) => void;
  timeRange?: string;
}

type CompareView = 'table' | 'bar' | 'radar';

interface PortfolioResult extends PortfolioMetrics {
  portfolioId: number;
  portfolioName: string;
}

export function CompareTable({ portfolios, onRemove, timeRange = '1y' }: CompareTableProps) {
  const [results, setResults] = useState<PortfolioResult[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [view, setView] = useState<CompareView>('table');

  useEffect(() => {
    if (portfolios.length === 0) {
      setResults([]);
      return;
    }

    const comparePortfolios = async () => {
      setLoading(true);
      setError(null);
      try {
        const response = await fetch('/api/portfolio/compare', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ portfolios, period: timeRange }),
        });
        if (!response.ok) throw new Error('对比失败');
        const data = await response.json();
        setResults(data.portfolios || []);
      } catch (err) {
        setError(err instanceof Error ? err.message : '未知错误');
      } finally {
        setLoading(false);
      }
    };

    comparePortfolios();
  }, [portfolios, timeRange]);

  const renderTableView = () => (
    <div className="compare-table-container">
      <table className="compare-table">
        <thead>
          <tr>
            <th>指标</th>
            {results.map((p) => (
              <th key={p.portfolioId}>{p.portfolioName}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          <tr>
            <td className="metric-name">累计收益</td>
            {results.map((p) => (
              <td
                key={p.portfolioId}
                className={p.total_return >= 0 ? 'positive' : 'negative'}
              >
                {p.total_return.toFixed(2)}%
              </td>
            ))}
          </tr>
          <tr>
            <td className="metric-name">年化收益</td>
            {results.map((p) => (
              <td
                key={p.portfolioId}
                className={p.annualized_return >= 0 ? 'positive' : 'negative'}
              >
                {p.annualized_return.toFixed(2)}%
              </td>
            ))}
          </tr>
          <tr>
            <td className="metric-name">波动率</td>
            {results.map((p) => (
              <td key={p.portfolioId}>{p.volatility.toFixed(2)}%</td>
            ))}
          </tr>
          <tr>
            <td className="metric-name">夏普比率</td>
            {results.map((p) => (
              <td
                key={p.portfolioId}
                className={p.sharpe_ratio >= 0 ? 'positive' : 'negative'}
              >
                {p.sharpe_ratio.toFixed(4)}
              </td>
            ))}
          </tr>
          <tr>
            <td className="metric-name">最大回撤</td>
            {results.map((p) => (
              <td key={p.portfolioId} className="negative">
                {p.max_drawdown.toFixed(2)}%
              </td>
            ))}
          </tr>
          <tr>
            <td className="metric-name">持有天数</td>
            {results.map((p) => (
              <td key={p.portfolioId}>{p.holding_period}</td>
            ))}
          </tr>
        </tbody>
      </table>
    </div>
  );

  const renderBarView = () => {
    const metrics = [
      { key: 'annualized_return', label: '年化收益', suffix: '%' },
      { key: 'volatility', label: '波动率', suffix: '%' },
      { key: 'sharpe_ratio', label: '夏普比率', suffix: '' },
    ] as const;

    const maxValues: Record<string, number> = {};
    metrics.forEach(({ key }) => {
      maxValues[key] = Math.max(...results.map((p) => Math.abs(p[key])));
    });

    return (
      <div className="compare-bar-container">
        {metrics.map(({ key, label, suffix }) => (
          <div key={key} className="bar-chart-group">
            <h4>{label}</h4>
            <div className="bar-chart">
              {results.map((p) => (
                <div key={p.portfolioId} className="bar-item">
                  <span className="bar-label">{p.portfolioName}</span>
                  <div className="bar-track">
                    <div
                      className={`bar-fill ${p[key] < 0 ? 'negative' : ''}`}
                      style={{
                        width: `${(Math.abs(p[key]) / (maxValues[key] || 1)) * 100}%`,
                      }}
                    />
                  </div>
                  <span className="bar-value">
                    {p[key] >= 0 ? '+' : ''}
                    {p[key].toFixed(2)}
                    {suffix}
                  </span>
                </div>
              ))}
            </div>
          </div>
        ))}
      </div>
    );
  };

  const renderRadarView = () => {
    const labels = ['年化收益', '波动率', '夏普比率', '最大回撤'];
    const dataKeys = [
      'annualized_return',
      'volatility',
      'sharpe_ratio',
      'max_drawdown',
    ] as const;

    const maxValues: Record<string, number> = {};
    dataKeys.forEach((key) => {
      maxValues[key] = Math.max(...results.map((p) => Math.abs(p[key])));
    });

    const radarRadius = 80;
    const centerX = 120;
    const centerY = 100;

    const getPoint = (index: number, value: number, max: number) => {
      const angle = (Math.PI * 2 * index) / labels.length - Math.PI / 2;
      const normalizedValue = (Math.abs(value) / (max || 1)) * radarRadius;
      return {
        x: centerX + normalizedValue * Math.cos(angle),
        y: centerY + normalizedValue * Math.sin(angle),
      };
    };

    return (
      <div className="compare-radar-container">
        <svg viewBox="0 0 240 200" className="radar-chart">
          {labels.map((_, i) => {
            const angle = (Math.PI * 2 * i) / labels.length - Math.PI / 2;
            const x2 = centerX + radarRadius * Math.cos(angle);
            const y2 = centerY + radarRadius * Math.sin(angle);
            return (
              <line
                key={i}
                x1={centerX}
                y1={centerY}
                x2={x2}
                y2={y2}
                stroke="#ddd"
                strokeWidth="1"
              />
            );
          })}

          {[0.25, 0.5, 0.75, 1].map((scale) => (
            <circle
              key={scale}
              cx={centerX}
              cy={centerY}
              r={radarRadius * scale}
              fill="none"
              stroke="#ddd"
              strokeWidth="1"
            />
          ))}

          {results.map((portfolio, pIndex) => {
            const points = dataKeys.map((key, i) => {
              const point = getPoint(i, portfolio[key], maxValues[key]);
              return `${point.x},${point.y}`;
            });
            return (
              <polygon
                key={portfolio.portfolioId}
                points={points.join(' ')}
                fill={`rgba(${50 + pIndex * 60}, ${150 - pIndex * 30}, ${200 - pIndex * 40}, 0.3)`}
                stroke={['#3498db', '#e74c3c', '#2ecc71', '#f39c12'][pIndex % 4]}
                strokeWidth="2"
              />
            );
          })}

          {labels.map((label, i) => {
            const angle = (Math.PI * 2 * i) / labels.length - Math.PI / 2;
            const x = centerX + (radarRadius + 15) * Math.cos(angle);
            const y = centerY + (radarRadius + 15) * Math.sin(angle);
            return (
              <text
                key={i}
                x={x}
                y={y}
                textAnchor="middle"
                dominantBaseline="middle"
                fontSize="10"
              >
                {label}
              </text>
            );
          })}
        </svg>
        <div className="radar-legend">
          {results.map((p, i) => (
            <div key={p.portfolioId} className="legend-item">
              <span
                className="legend-color"
                style={{
                  background: ['#3498db', '#e74c3c', '#2ecc71', '#f39c12'][i % 4],
                }}
              />
              <span>{p.portfolioName}</span>
            </div>
          ))}
        </div>
      </div>
    );
  };

  if (portfolios.length === 0) {
    return (
      <div className="compare-table empty">
        <div className="empty-message">请先添加多个组合进行对比</div>
      </div>
    );
  }

  return (
    <div className="compare-table">
      <div className="compare-header">
        <h3>组合对比</h3>
        <div className="view-tabs">
          <button
            className={`view-tab ${view === 'table' ? 'active' : ''}`}
            onClick={() => setView('table')}
          >
            表格
          </button>
          <button
            className={`view-tab ${view === 'bar' ? 'active' : ''}`}
            onClick={() => setView('bar')}
          >
            柱状图
          </button>
          <button
            className={`view-tab ${view === 'radar' ? 'active' : ''}`}
            onClick={() => setView('radar')}
          >
            雷达图
          </button>
        </div>
      </div>

      <div className="compare-body">
        {loading && <div className="loading">对比分析中...</div>}
        {error && <div className="error">{error}</div>}

        {!loading && !error && results.length > 0 && (
          <>
            {view === 'table' && renderTableView()}
            {view === 'bar' && renderBarView()}
            {view === 'radar' && renderRadarView()}
          </>
        )}
      </div>
    </div>
  );
}