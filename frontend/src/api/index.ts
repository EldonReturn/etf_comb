/**
 * ETF组合推荐系统 - API接口定义
 *
 * 本模块定义与后端API交互的类型和接口函数。
 */

/**
 * ETF基本信息
 */
export interface ETFInfo {
  code: string;
  name: string;
  category: string;
  updated_at: string | null;
}

/**
 * 净值历史记录
 */
export interface NAVHistory {
  date: string;
  nav: number;
  accum_nav: number;
}

/**
 * 组合权重
 */
export type Weights = Record<string, number>;

/**
 * 单只ETF业绩指标
 */
export interface ETFFMetrics {
  code: string;
  name: string;
  weight: number;
  total_return: number;
  annualized_return: number;
  volatility: number;
  sharpe_ratio: number;
  max_drawdown: number;
}

/**
 * 组合业绩指标
 */
export interface PortfolioMetrics {
  total_return: number;
  annualized_return: number;
  volatility: number;
  sharpe_ratio: number;
  max_drawdown: number;
  holding_period: number;
  nav_series: number[];
  nav_dates: string[];
  benchmark_nav_series: number[];
  daily_returns: number[];
  etf_metrics: Record<string, ETFFMetrics>;
}

/**
 * 优化结果
 */
export interface OptimizationResult {
  success: boolean;
  weights: Weights;
  expected_return: number;
  volatility: number;
  sharpe_ratio: number;
  message: string;
}

/**
 * API响应类型
 */
export interface ETFListResponse {
  total: number;
  etfs: ETFInfo[];
}

export interface NAVHistoryResponse {
  code: string;
  total: number;
  history: NAVHistory[];
}

export interface SyncResponse {
  status: string;
  etf_count: number;
  nav_count: number;
  errors: number;
}

const API_BASE = '/api';

/**
 * 获取ETF列表
 * @param category 可选，按分类筛选
 * @param search 可选，搜索关键词
 */
export async function fetchETFList(
  category?: string,
  search?: string
): Promise<ETFListResponse> {
  const params = new URLSearchParams();
  if (category) params.append('category', category);
  if (search) params.append('search', search);

  const url = `${API_BASE}/etfs${params.toString() ? '?' + params.toString() : ''}`;
  const response = await fetch(url);
  if (!response.ok) {
    throw new Error(`获取ETF列表失败: ${response.statusText}`);
  }
  return response.json();
}

/**
 * 获取ETF历史净值
 * @param code ETF代码
 * @param startDate 起始日期
 * @param endDate 结束日期
 */
export async function fetchETFHistory(
  code: string,
  startDate?: string,
  endDate?: string
): Promise<NAVHistoryResponse> {
  const params = new URLSearchParams();
  if (startDate) params.append('start_date', startDate);
  if (endDate) params.append('end_date', endDate);

  const url = `${API_BASE}/etf/${code}/history${params.toString() ? '?' + params.toString() : ''}`;
  const response = await fetch(url);
  if (!response.ok) {
    throw new Error(`获取ETF历史数据失败: ${response.statusText}`);
  }
  return response.json();
}

/**
 * 评估组合表现
 * @param weights ETF权重字典
 */
export async function evaluatePortfolio(weights: Weights): Promise<PortfolioMetrics> {
  const response = await fetch(`${API_BASE}/portfolio/evaluate`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ weights }),
  });
  if (!response.ok) {
    throw new Error(`评估组合失败: ${response.statusText}`);
  }
  return response.json();
}

/**
 * 比较多个组合
 * @param portfolios 多个组合的权重列表
 */
export async function comparePortfolios(
  portfolios: Weights[]
): Promise<{ portfolios: PortfolioMetrics[] }> {
  const response = await fetch(`${API_BASE}/portfolio/compare`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ portfolios }),
  });
  if (!response.ok) {
    throw new Error(`对比组合失败: ${response.statusText}`);
  }
  return response.json();
}

/**
 * 优化最大收益组合
 * @param etfCodes 可选ETF代码列表
 * @param maxWeight 单个ETF最大权重
 * @param targetVolatility 目标波动率
 */
export async function optimizePortfolio(
  etfCodes: string[],
  maxWeight?: number,
  targetVolatility?: number
): Promise<OptimizationResult> {
  const response = await fetch(`${API_BASE}/portfolio/optimize`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      etf_codes: etfCodes,
      max_weight: maxWeight,
      target_volatility: targetVolatility,
    }),
  });
  if (!response.ok) {
    throw new Error(`优化组合失败: ${response.statusText}`);
  }
  return response.json();
}

/**
 * 手动同步ETF数据
 */
export async function syncETFData(): Promise<SyncResponse> {
  const response = await fetch(`${API_BASE}/admin/sync`, {
    method: 'POST',
  });
  if (!response.ok) {
    throw new Error(`同步数据失败: ${response.statusText}`);
  }
  return response.json();
}

/**
 * 获取系统状态
 */
export async function fetchSystemStatus(): Promise<{ status: string }> {
  const response = await fetch(`${API_BASE}/../`);
  if (!response.ok) {
    throw new Error(`获取系统状态失败: ${response.statusText}`);
  }
  return response.json();
}