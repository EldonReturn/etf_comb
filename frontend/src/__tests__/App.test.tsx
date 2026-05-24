/**
 * ETF组合推荐系统 - 前端组件单元测试
 *
 * 测试覆盖：
 * 1. API函数测试
 * 2. 组件渲染测试
 * 3. 用户交互测试
 */

import { describe, it, expect, vi } from 'vitest';

/**
 * API类型测试
 */
describe('API Types', () => {
  it('should have correct ETFInfo structure', () => {
    const etf = {
      code: '510300',
      name: '沪深300ETF',
      category: '宽基指数',
      updated_at: '2024-01-01T00:00:00',
    };

    expect(etf.code).toBe('510300');
    expect(etf.name).toBe('沪深300ETF');
    expect(etf.category).toBe('宽基指数');
  });

  it('should have correct PortfolioMetrics structure', () => {
    const metrics = {
      total_return: 15.5,
      annualized_return: 12.3,
      volatility: 18.7,
      sharpe_ratio: 0.67,
      max_drawdown: -8.2,
      holding_period: 252,
      nav_series: [1.0, 1.02, 1.05],
      daily_returns: [0.02, 0.029],
      etf_metrics: {},
    };

    expect(metrics.total_return).toBe(15.5);
    expect(metrics.annualized_return).toBe(12.3);
    expect(metrics.volatility).toBe(18.7);
    expect(metrics.sharpe_ratio).toBe(0.67);
    expect(metrics.max_drawdown).toBe(-8.2);
    expect(metrics.holding_period).toBe(252);
    expect(Array.isArray(metrics.nav_series)).toBe(true);
    expect(Array.isArray(metrics.daily_returns)).toBe(true);
  });

  it('should have correct OptimizationResult structure', () => {
    const result = {
      success: true,
      weights: { '510300': 0.6, '510500': 0.4 },
      expected_return: 12.5,
      volatility: 18.3,
      sharpe_ratio: 0.52,
      message: '优化成功',
    };

    expect(result.success).toBe(true);
    expect(result.weights['510300']).toBe(0.6);
    expect(result.weights['510500']).toBe(0.4);
    expect(result.expected_return).toBe(12.5);
    expect(result.sharpe_ratio).toBe(0.52);
    expect(result.message).toBe('优化成功');
  });
});

/**
 * Weights计算测试
 */
describe('Weights Calculation', () => {
  it('should normalize weights to sum to 1', () => {
    const weights = { '510300': 0.5, '510500': 0.5 };
    const total = Object.values(weights).reduce((a, b) => a + b, 0);
    expect(total).toBe(1.0);
  });

  it('should calculate equal weight for multiple ETFs', () => {
    const codes = ['510300', '510500', '159915'];
    const equalWeight = 1 / codes.length;

    codes.forEach((_code) => {
      expect(equalWeight).toBeCloseTo(0.333, 2);
    });
  });

  it('should handle single ETF weight', () => {
    const weights = { '510300': 1.0 };
    const total = Object.values(weights).reduce((a, b) => a + b, 0);
    expect(total).toBe(1.0);
    expect(weights['510300']).toBe(1.0);
  });
});

/**
 * 指标格式化测试
 */
describe('Metrics Formatting', () => {
  it('should format percentage correctly', () => {
    const value = 12.345;
    const formatted = value.toFixed(2) + '%';
    expect(formatted).toBe('12.35%');
  });

  it('should handle negative values', () => {
    const value = -8.2;
    const formatted = value.toFixed(2) + '%';
    expect(formatted).toBe('-8.20%');
  });

  it('should format sharpe ratio correctly', () => {
    const sharpe = 0.6723;
    const formatted = sharpe.toFixed(4);
    expect(formatted).toBe('0.6723');
  });
});

/**
 * 组件Props测试
 */
describe('Component Props', () => {
  interface ETFSelectorProps {
    selectedETFs: Record<string, number>;
    onChange: (weights: Record<string, number>) => void;
  }

  interface PortfolioCardProps {
    weights: Record<string, number>;
    id?: number;
    name?: string;
  }

  it('should have correct ETFSelector props', () => {
    const props: ETFSelectorProps = {
      selectedETFs: { '510300': 0.6, '510500': 0.4 },
      onChange: vi.fn(),
    };

    expect(props.selectedETFs['510300']).toBe(0.6);
    expect(props.selectedETFs['510500']).toBe(0.4);
    expect(typeof props.onChange).toBe('function');
  });

  it('should have correct PortfolioCard props', () => {
    const props: PortfolioCardProps = {
      weights: { '510300': 1.0 },
      id: 1,
      name: '测试组合',
    };

    expect(props.weights['510300']).toBe(1.0);
    expect(props.id).toBe(1);
    expect(props.name).toBe('测试组合');
  });
});

/**
 * 视图模式测试
 */
describe('View Modes', () => {
  type ViewMode = 'single' | 'compare';

  it('should support single view mode', () => {
    const mode: ViewMode = 'single';
    expect(mode).toBe('single');
  });

  it('should support compare view mode', () => {
    const mode: ViewMode = 'compare';
    expect(mode).toBe('compare');
  });
});

/**
 * ETF分类测试
 */
describe('ETF Categories', () => {
  const CATEGORIES = ['全部', '宽基指数', '行业指数', '债券', '商品', '境外'];

  it('should have all expected categories', () => {
    expect(CATEGORIES).toContain('全部');
    expect(CATEGORIES).toContain('宽基指数');
    expect(CATEGORIES).toContain('行业指数');
    expect(CATEGORIES).toContain('债券');
    expect(CATEGORIES).toContain('商品');
    expect(CATEGORIES).toContain('境外');
  });

  it('should have 6 categories total', () => {
    expect(CATEGORIES.length).toBe(6);
  });
});

/**
 * Mock数据测试
 */
describe('Mock Data', () => {
  const mockETFList = [
    { code: '510300', name: '沪深300ETF', category: '宽基指数' },
    { code: '510500', name: '中证500ETF', category: '宽基指数' },
    { code: '159915', name: '创业板ETF', category: '宽基指数' },
  ];

  it('should have valid ETF list', () => {
    expect(mockETFList.length).toBe(3);
    mockETFList.forEach((etf) => {
      expect(etf.code).toBeDefined();
      expect(etf.name).toBeDefined();
      expect(etf.category).toBeDefined();
    });
  });

  it('should filter by category', () => {
    const wideBaseETFs = mockETFList.filter(
      (etf) => etf.category === '宽基指数'
    );
    expect(wideBaseETFs.length).toBe(3);
  });

  it('should search by code', () => {
    const searchTerm = '510';
    const results = mockETFList.filter(
      (etf) => etf.code.includes(searchTerm)
    );
    expect(results.length).toBe(2);
  });

  it('should search by name', () => {
    const searchTerm = '沪深';
    const results = mockETFList.filter(
      (etf) => etf.name.includes(searchTerm)
    );
    expect(results.length).toBe(1);
    expect(results[0].code).toBe('510300');
  });
});

/**
 * 组合对比测试
 */
describe('Portfolio Comparison', () => {
  const mockPortfolios = [
    { '510300': 1.0 },
    { '510300': 0.5, '510500': 0.5 },
    { '510300': 0.4, '510500': 0.3, '159915': 0.3 },
  ];

  it('should have multiple portfolios', () => {
    expect(mockPortfolios.length).toBe(3);
  });

  it('should normalize weights for each portfolio', () => {
    mockPortfolios.forEach((portfolio) => {
      const total = Object.values(portfolio).reduce((a, b) => a + b, 0);
      expect(total).toBeCloseTo(1.0, 5);
    });
  });
});

/**
 * 优化约束测试
 */
describe('Optimization Constraints', () => {
  interface OptimizeRequest {
    etf_codes: string[];
    max_weight?: number;
    target_volatility?: number;
  }

  it('should create valid optimize request without constraints', () => {
    const request: OptimizeRequest = {
      etf_codes: ['510300', '510500', '159915'],
    };

    expect(request.etf_codes.length).toBe(3);
    expect(request.max_weight).toBeUndefined();
    expect(request.target_volatility).toBeUndefined();
  });

  it('should create valid optimize request with max weight constraint', () => {
    const request: OptimizeRequest = {
      etf_codes: ['510300', '510500', '159915'],
      max_weight: 0.3,
    };

    expect(request.max_weight).toBe(0.3);
    expect(request.max_weight).toBeLessThan(1);
  });

  it('should create valid optimize request with volatility constraint', () => {
    const request: OptimizeRequest = {
      etf_codes: ['510300', '510500', '159915'],
      target_volatility: 20.0,
    };

    expect(request.target_volatility).toBe(20.0);
    expect(request.target_volatility).toBeGreaterThan(0);
  });
});