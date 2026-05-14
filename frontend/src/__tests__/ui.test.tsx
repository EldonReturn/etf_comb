/**
 * ETF组合推荐系统 - UI测试用例
 *
 * 基于页面访问及前后端代码逻辑撰写，覆盖：
 * 1. App组件整体渲染
 * 2. ETFSelector 搜索/筛选/选择/权重调整
 * 3. PortfolioCard 空态/加载/错误/指标/图表/配置
 * 4. OptimizerPanel 勾选/约束/优化/结果/应用
 * 5. CompareTable 空态/表格/柱状图/雷达图
 * 6. 集成流程
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, fireEvent, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import App from '../App';
import { ETFSelector } from '../components/ETFSelector';
import { PortfolioCard } from '../components/PortfolioCard';
import { CompareTable } from '../components/CompareTable';
import { OptimizerPanel } from '../components/OptimizerPanel';

// ─── Mock Data ───────────────────────────────────────────────

const mockETFList = {
  total: 4,
  etfs: [
    { code: '510300.SH', name: '沪深300ETF', category: '宽基指数', updated_at: '2024-12-01T00:00:00' },
    { code: '510500.SH', name: '中证500ETF', category: '宽基指数', updated_at: '2024-12-01T00:00:00' },
    { code: '159915.SZ', name: '创业板ETF', category: '宽基指数', updated_at: '2024-12-01T00:00:00' },
    { code: '510880.SH', name: '红利ETF', category: '宽基指数', updated_at: '2024-12-01T00:00:00' },
  ],
};

const mockPortfolioMetrics = {
  total_return: 15.50,
  annualized_return: 12.30,
  volatility: 18.70,
  sharpe_ratio: 0.67,
  max_drawdown: -8.20,
  holding_period: 252,
  nav_series: [1.0000, 1.0120, 1.0250, 1.0400, 1.0550, 1.0700, 1.0850, 1.1000, 1.1150, 1.1300, 1.1450, 1.1550],
  daily_returns: [0.0120, 0.0128, 0.0146, 0.0144, 0.0142, 0.0140, 0.0138, 0.0136, 0.0135, 0.0133, 0.0087],
  etf_metrics: {
    '510300.SH': { code: '510300.SH', name: '沪深300ETF', weight: 0.6, total_return: 10.0, annualized_return: 8.0, volatility: 20.0, sharpe_ratio: 0.4, max_drawdown: -10.0 },
    '510500.SH': { code: '510500.SH', name: '中证500ETF', weight: 0.4, total_return: 18.0, annualized_return: 14.0, volatility: 25.0, sharpe_ratio: 0.56, max_drawdown: -15.0 },
  },
};

const mockOptimizationResult = {
  success: true,
  weights: { '510300.SH': 0.45, '510500.SH': 0.35, '159915.SZ': 0.20 },
  expected_return: 13.50,
  volatility: 17.20,
  sharpe_ratio: 0.72,
  message: '优化成功，基于均值-方差模型',
};

const mockComparisonResult = {
  portfolios: [
    {
      ...mockPortfolioMetrics,
      portfolioId: 0,
      portfolioName: '组合A',
    },
    {
      ...mockPortfolioMetrics,
      total_return: 22.0,
      annualized_return: 18.0,
      volatility: 22.0,
      sharpe_ratio: 0.81,
      max_drawdown: -12.0,
      holding_period: 252,
      nav_series: [1, 1.1, 1.2],
      daily_returns: [0.1, 0.09],
      etf_metrics: {},
      portfolioId: 1,
      portfolioName: '组合B',
    },
  ],
};

const mockHealthResponse = { status: 'healthy' };

// ─── Fetch Mock Helpers ──────────────────────────────────────

function mockFetchSuccess(data: unknown, ok = true) {
  return Promise.resolve({
    ok,
    json: () => Promise.resolve(data),
    status: ok ? 200 : 400,
    statusText: ok ? 'OK' : 'Bad Request',
  });
}

function mockFetchError() {
  return Promise.reject(new Error('Network error'));
}

function mockFetchSequential(...responses: Array<Record<string, unknown>>) {
  let calls = 0;
  globalThis.fetch = vi.fn(() => {
    const resp = responses[Math.min(calls, responses.length - 1)];
    calls++;
    return Promise.resolve({
      ok: true,
      json: () => Promise.resolve(resp),
      status: 200,
      statusText: 'OK',
    });
  }) as unknown as typeof fetch;
}

// ─── State reset between tests ───────────────────────────────

beforeEach(() => {
  globalThis.fetch = vi.fn() as unknown as typeof fetch;
});

afterEach(() => {
  vi.restoreAllMocks();
});

// ======================================================================
//                         App 整体组件测试
// ======================================================================

describe('App 整体渲染', () => {
  it('应渲染标题"ETF组合推荐系统"', async () => {
    (fetch as ReturnType<typeof vi.fn>).mockResolvedValueOnce(mockFetchSuccess(mockHealthResponse));
    render(<App />);

    expect(screen.getByRole('heading', { name: 'ETF组合推荐系统' })).toBeInTheDocument();
  });

  it('应渲染视图切换按钮"单组合"和"对比模式"', async () => {
    (fetch as ReturnType<typeof vi.fn>).mockResolvedValue(mockFetchSuccess(mockHealthResponse));
    render(<App />);

    expect(screen.getByRole('button', { name: '单组合' })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: '对比模式' })).toBeInTheDocument();
  });

  it('"单组合"按钮默认处于激活状态', async () => {
    (fetch as ReturnType<typeof vi.fn>).mockResolvedValue(mockFetchSuccess(mockHealthResponse));
    render(<App />);

    const singleBtn = screen.getByRole('button', { name: '单组合' });
    expect(singleBtn.classList.contains('active')).toBe(true);
  });

  it('点击"对比模式"后该按钮应激活', async () => {
    (fetch as ReturnType<typeof vi.fn>).mockResolvedValue(mockFetchSuccess(mockHealthResponse));
    render(<App />);

    fireEvent.click(screen.getByRole('button', { name: '对比模式' }));

    const compareBtn = screen.getByRole('button', { name: '对比模式' });
    expect(compareBtn.classList.contains('active')).toBe(true);
  });

  it('应显示系统健康状态', async () => {
    (fetch as ReturnType<typeof vi.fn>)
      .mockResolvedValueOnce(mockFetchSuccess(mockHealthResponse))
      .mockResolvedValueOnce(mockFetchSuccess(mockETFList));
    render(<App />);

    await waitFor(() => {
      expect(screen.getByText('系统正常')).toBeInTheDocument();
    });
  });

  it('系统断开连接时应显示"未连接后端"', async () => {
    (fetch as ReturnType<typeof vi.fn>).mockRejectedValueOnce(new Error('Network error'));
    render(<App />);

    await waitFor(() => {
      expect(screen.getByText('未连接后端')).toBeInTheDocument();
    });
  });

  it('系统状态应默认显示"检查中..."', async () => {
    (fetch as ReturnType<typeof vi.fn>).mockImplementation(
      () => new Promise(() => {}), // never resolves
    );
    render(<App />);

    expect(screen.getByText('检查中...')).toBeInTheDocument();
  });

  it('布局应包含左侧ETF选择器和右侧优化面板', async () => {
    (fetch as ReturnType<typeof vi.fn>).mockResolvedValue(mockFetchSuccess(mockHealthResponse));
    render(<App />);

    expect(screen.getByRole('heading', { name: '选择ETF' })).toBeInTheDocument();
    expect(screen.getByRole('heading', { name: '最优组合优化' })).toBeInTheDocument();
  });

  it('无选中ETF时不应显示"保存当前组合"按钮', async () => {
    (fetch as ReturnType<typeof vi.fn>).mockResolvedValue(mockFetchSuccess(mockHealthResponse));
    render(<App />);

    await waitFor(() => {
      expect(screen.queryByText('保存当前组合')).not.toBeInTheDocument();
    });
  });
});

// ======================================================================
//                         ETFSelector 组件测试
// ======================================================================

describe('ETFSelector 组件', () => {
  it('应渲染搜索输入框', async () => {
    (fetch as ReturnType<typeof vi.fn>).mockResolvedValueOnce(mockFetchSuccess(mockETFList));
    const onChange = vi.fn();
    render(<ETFSelector selectedETFs={{}} onChange={onChange} />);

    expect(screen.getByPlaceholderText('搜索ETF名称或代码...')).toBeInTheDocument();
  });

  it('应渲染分类下拉框（6个选项）', async () => {
    (fetch as ReturnType<typeof vi.fn>).mockResolvedValueOnce(mockFetchSuccess(mockETFList));
    render(<ETFSelector selectedETFs={{}} onChange={vi.fn()} />);

    const select = screen.getByRole('combobox');
    expect(select).toBeInTheDocument();
    const options = within(select).getAllByRole('option');
    expect(options).toHaveLength(6);
    expect(options[0]).toHaveTextContent('全部');
    expect(options[1]).toHaveTextContent('宽基指数');
    expect(options[2]).toHaveTextContent('行业指数');
    expect(options[3]).toHaveTextContent('债券');
    expect(options[4]).toHaveTextContent('商品');
    expect(options[5]).toHaveTextContent('境外');
  });

  it('加载中应显示"加载中..."', () => {
    (fetch as ReturnType<typeof vi.fn>).mockImplementation(
      () => new Promise(() => {}),
    );
    render(<ETFSelector selectedETFs={{}} onChange={vi.fn()} />);

    expect(screen.getByText('加载中...')).toBeInTheDocument();
  });

  it('加载出错应显示错误信息', async () => {
    (fetch as ReturnType<typeof vi.fn>).mockRejectedValueOnce(new Error('Network error'));
    render(<ETFSelector selectedETFs={{}} onChange={vi.fn()} />);

    await waitFor(() => {
      expect(screen.getByText('Network error')).toBeInTheDocument();
    });
  });

  it('API返回400时应显示错误', async () => {
    (fetch as ReturnType<typeof vi.fn>).mockResolvedValueOnce(mockFetchSuccess(null, false));
    render(<ETFSelector selectedETFs={{}} onChange={vi.fn()} />);

    await waitFor(() => {
      expect(screen.getByText('获取ETF列表失败')).toBeInTheDocument();
    });
  });

  it('应渲染ETF列表并显示ETF代码和名称', async () => {
    (fetch as ReturnType<typeof vi.fn>).mockResolvedValueOnce(mockFetchSuccess(mockETFList));
    render(<ETFSelector selectedETFs={{}} onChange={vi.fn()} />);

    await waitFor(() => {
      expect(screen.getByText('沪深300ETF')).toBeInTheDocument();
      expect(screen.getByText('中证500ETF')).toBeInTheDocument();
      expect(screen.getByText('创业板ETF')).toBeInTheDocument();
      expect(screen.getByText('红利ETF')).toBeInTheDocument();
    });
  });

  it('点击ETF可切换选中状态——选中项应有"selected"样式', async () => {
    (fetch as ReturnType<typeof vi.fn>).mockResolvedValueOnce(mockFetchSuccess(mockETFList));
    const onChange = vi.fn();
    render(<ETFSelector selectedETFs={{}} onChange={onChange} />);

    await waitFor(() => screen.getByText('沪深300ETF'));
    const etfItem = screen.getByText('沪深300ETF').closest('.etf-item')!;
    fireEvent.click(etfItem);

    expect(onChange).toHaveBeenCalledTimes(1);
    const newWeights = onChange.mock.calls[0][0];
    expect(newWeights['510300.SH']).toBe(1);
  });

  it('选中ETF后再次点击应取消选择', async () => {
    (fetch as ReturnType<typeof vi.fn>).mockResolvedValueOnce(mockFetchSuccess(mockETFList));
    const onChange = vi.fn();
    render(<ETFSelector selectedETFs={{ '510300.SH': 1.0 }} onChange={onChange} />);

    await waitFor(() => screen.getAllByText('沪深300ETF'));
    const etfItem = screen.getAllByText('沪深300ETF')[0].closest('.etf-item')!;
    fireEvent.click(etfItem);

    expect(onChange).toHaveBeenCalledTimes(1);
    const newWeights = onChange.mock.calls[0][0];
    expect(newWeights['510300.SH']).toBeUndefined();
  });

  it('选择多只ETF时应均分权重', async () => {
    (fetch as ReturnType<typeof vi.fn>).mockResolvedValueOnce(mockFetchSuccess(mockETFList));
    const onChange = vi.fn();
    render(<ETFSelector selectedETFs={{ '510300.SH': 0.5, '510500.SH': 0.5 }} onChange={onChange} />);

    await waitFor(() => screen.getByText('红利ETF'));
    fireEvent.click(screen.getByText('红利ETF').closest('.etf-item')!);

    const newWeights = onChange.mock.calls[0][0];
    expect(newWeights['510300.SH']).toBeCloseTo(1 / 3, 5);
    expect(newWeights['510500.SH']).toBeCloseTo(1 / 3, 5);
    expect(newWeights['510880.SH']).toBeCloseTo(1 / 3, 5);
  });

  it('已选ETF应显示权重输入框', async () => {
    (fetch as ReturnType<typeof vi.fn>).mockResolvedValueOnce(mockFetchSuccess(mockETFList));
    render(<ETFSelector selectedETFs={{ '510300.SH': 0.6 }} onChange={vi.fn()} />);

    await waitFor(() => screen.getAllByText('沪深300ETF'));
    const weightInput = screen.getByRole('spinbutton');
    expect(weightInput).toBeInTheDocument();
    expect(parseFloat(weightInput.getAttribute('value')!)).toBeCloseTo(60, 0);
  });

  it('修改权重应触发onChange并维持总和为1', async () => {
    (fetch as ReturnType<typeof vi.fn>).mockResolvedValueOnce(mockFetchSuccess(mockETFList));
    const onChange = vi.fn();
    render(
      <ETFSelector
        selectedETFs={{ '510300.SH': 0.6, '510500.SH': 0.4 }}
        onChange={onChange}
      />,
    );

    await waitFor(() => screen.getAllByText('沪深300ETF'));
    const weightInputs = screen.getAllByRole('spinbutton');
    fireEvent.change(weightInputs[0], { target: { value: '70' } });

    const newWeights = onChange.mock.calls[0][0];
    expect(newWeights['510300.SH']).toBeCloseTo(0.7, 5);
    expect(newWeights['510500.SH']).toBeCloseTo(0.3, 5);
  });

  it('有选中ETF时应显示"已选组合"区域及数量', async () => {
    (fetch as ReturnType<typeof vi.fn>).mockResolvedValueOnce(mockFetchSuccess(mockETFList));
    render(<ETFSelector selectedETFs={{ '510300.SH': 1.0 }} onChange={vi.fn()} />);

    await waitFor(() => {
      expect(screen.getByText(/已选组合/)).toBeInTheDocument();
      expect(screen.getByText(/\(1只\)/)).toBeInTheDocument();
    });
  });

  it('更改分类筛选应重新获取ETF', async () => {
    (fetch as ReturnType<typeof vi.fn>).mockResolvedValueOnce(mockFetchSuccess(mockETFList));
    (fetch as ReturnType<typeof vi.fn>).mockResolvedValueOnce(mockFetchSuccess({ total: 1, etfs: [mockETFList.etfs[0]] }));

    render(<ETFSelector selectedETFs={{}} onChange={vi.fn()} />);
    await waitFor(() => screen.getByText('沪深300ETF'));

    fireEvent.change(screen.getByRole('combobox'), { target: { value: '行业指数' } });

    expect(fetch).toHaveBeenCalledWith(
      expect.stringContaining('category=%E8%A1%8C%E4%B8%9A%E6%8C%87%E6%95%B0'),
    );
  });

  it('输入搜索词应发起带search参数的请求', async () => {
    (fetch as ReturnType<typeof vi.fn>).mockResolvedValueOnce(mockFetchSuccess(mockETFList));
    (fetch as ReturnType<typeof vi.fn>).mockResolvedValueOnce(mockFetchSuccess({ total: 1, etfs: [mockETFList.etfs[0]] }));

    render(<ETFSelector selectedETFs={{}} onChange={vi.fn()} />);
    await waitFor(() => screen.getByText('沪深300ETF'));

    const searchInput = screen.getByPlaceholderText('搜索ETF名称或代码...');
    fireEvent.change(searchInput, { target: { value: '沪深' } });

    // Wait for debounced effect
    await waitFor(() => {
      expect(fetch).toHaveBeenCalledWith(expect.stringContaining('search=%E6%B2%AA%E6%B7%B1'));
    });
  });
});

// ======================================================================
//                      PortfolioCard 组件测试
// ======================================================================

describe('PortfolioCard 组件', () => {
  it('无ETF时应显示空态提示', () => {
    render(<PortfolioCard weights={{}} />);

    expect(screen.getByText('请从左侧选择ETF构建组合')).toBeInTheDocument();
  });

  it('应显示组合标题——name参数优先', () => {
    render(<PortfolioCard weights={{ '510300.SH': 1.0 }} name="测试组合" />);

    expect(screen.getByText('测试组合')).toBeInTheDocument();
  });

  it('无name时应显示"组合[id]"', () => {
    render(<PortfolioCard weights={{ '510300.SH': 1.0 }} id={3} />);

    expect(screen.getByText('组合3')).toBeInTheDocument();
  });

  it('评估中应显示"评估中..."标记', () => {
    (fetch as ReturnType<typeof vi.fn>).mockImplementation(
      () => new Promise(() => {}),
    );
    render(<PortfolioCard weights={{ '510300.SH': 1.0 }} />);

    expect(screen.getByText('评估中...')).toBeInTheDocument();
  });

  it('评估成功后应显示6项指标', async () => {
    (fetch as ReturnType<typeof vi.fn>).mockResolvedValueOnce(mockFetchSuccess(mockPortfolioMetrics));
    render(<PortfolioCard weights={{ '510300.SH': 0.6, '510500.SH': 0.4 }} />);

    await waitFor(() => {
      expect(screen.getByText('累计收益')).toBeInTheDocument();
      expect(screen.getByText('年化收益')).toBeInTheDocument();
      expect(screen.getByText('波动率')).toBeInTheDocument();
      expect(screen.getByText('夏普比率')).toBeInTheDocument();
      expect(screen.getByText('最大回撤')).toBeInTheDocument();
      expect(screen.getByText('持有天数')).toBeInTheDocument();
    });
  });

  it('应正确显示各项指标数值', async () => {
    (fetch as ReturnType<typeof vi.fn>).mockResolvedValueOnce(mockFetchSuccess(mockPortfolioMetrics));
    render(<PortfolioCard weights={{ '510300.SH': 0.6, '510500.SH': 0.4 }} />);

    await waitFor(() => {
      expect(screen.getByText('15.50%')).toBeInTheDocument();
      expect(screen.getByText('12.30%')).toBeInTheDocument();
      expect(screen.getByText('18.70%')).toBeInTheDocument();
      expect(screen.getByText('0.67')).toBeInTheDocument();
      expect(screen.getByText('252.00')).toBeInTheDocument(); // holding_period toFixed(2)
    });
  });

  it('评估失败应显示错误信息', async () => {
    (fetch as ReturnType<typeof vi.fn>).mockRejectedValueOnce(new Error('评估失败'));
    render(<PortfolioCard weights={{ '510300.SH': 1.0 }} />);

    await waitFor(() => {
      expect(screen.getByText('评估失败')).toBeInTheDocument();
    });
  });

  it('应渲染"净值曲线"和"回撤曲线"切换按钮', async () => {
    (fetch as ReturnType<typeof vi.fn>).mockResolvedValueOnce(mockFetchSuccess(mockPortfolioMetrics));
    render(<PortfolioCard weights={{ '510300.SH': 0.6, '510500.SH': 0.4 }} />);

    await waitFor(() => {
      expect(screen.getByRole('button', { name: '净值曲线' })).toBeInTheDocument();
      expect(screen.getByRole('button', { name: '回撤曲线' })).toBeInTheDocument();
    });
  });

  it('默认应显示净值曲线图表', async () => {
    (fetch as ReturnType<typeof vi.fn>).mockResolvedValueOnce(mockFetchSuccess(mockPortfolioMetrics));
    const { container } = render(
      <PortfolioCard weights={{ '510300.SH': 0.6, '510500.SH': 0.4 }} />,
    );

    await waitFor(() => {
      const svg = container.querySelector('.chart-svg');
      expect(svg).toBeInTheDocument();
      const polyline = svg!.querySelector('polyline');
      expect(polyline).toBeInTheDocument();
      expect(polyline!.getAttribute('stroke')).toBe('#3498db'); // 净值曲线为蓝色
    });
  });

  it('点击"回撤曲线"应切换到回撤图表', async () => {
    (fetch as ReturnType<typeof vi.fn>).mockResolvedValueOnce(mockFetchSuccess(mockPortfolioMetrics));
    const { container } = render(
      <PortfolioCard weights={{ '510300.SH': 0.6, '510500.SH': 0.4 }} />,
    );

    await waitFor(() => screen.getByRole('button', { name: '回撤曲线' }));
    fireEvent.click(screen.getByRole('button', { name: '回撤曲线' }));

    const polyline = container.querySelector('.chart-svg polyline');
    expect(polyline!.getAttribute('stroke')).toBe('#e74c3c'); // 回撤曲线为红色
  });

  it('应显示ETF配置区域及权重条形图', async () => {
    (fetch as ReturnType<typeof vi.fn>).mockResolvedValueOnce(mockFetchSuccess(mockPortfolioMetrics));
    render(<PortfolioCard weights={{ '510300.SH': 0.6, '510500.SH': 0.4 }} />);

    await waitFor(() => {
      expect(screen.getByText('ETF配置')).toBeInTheDocument();
      expect(screen.getByText('60.0%')).toBeInTheDocument();
      expect(screen.getByText('40.0%')).toBeInTheDocument();
    });
  });

  it('净值数据为空时应显示"暂无净值数据"', async () => {
    const emptyMetrics = { ...mockPortfolioMetrics, nav_series: [] };
    (fetch as ReturnType<typeof vi.fn>).mockResolvedValueOnce(mockFetchSuccess(emptyMetrics));
    render(<PortfolioCard weights={{ '510300.SH': 1.0 }} />);

    await waitFor(() => {
      expect(screen.getByText('暂无净值数据')).toBeInTheDocument();
    });
  });

  it('权重变化时应重新请求评估接口', async () => {
    (fetch as ReturnType<typeof vi.fn>)
      .mockResolvedValueOnce(mockFetchSuccess(mockPortfolioMetrics))
      .mockResolvedValueOnce(mockFetchSuccess({ ...mockPortfolioMetrics, total_return: 20.0 }));

    const { rerender } = render(<PortfolioCard weights={{ '510300.SH': 1.0 }} />);

    await waitFor(() => screen.getByText('15.50%'));

    rerender(<PortfolioCard weights={{ '510300.SH': 0.5, '510500.SH': 0.5 }} />);

    await waitFor(() => {
      expect(fetch).toHaveBeenCalledTimes(2);
      expect(screen.getByText('20.00%')).toBeInTheDocument();
    });
  });
});

// ======================================================================
//                      OptimizerPanel 组件测试
// ======================================================================

describe('OptimizerPanel 组件', () => {
  const mockAvailableETFs = mockETFList.etfs;

  it('应渲染可勾选ETF列表', () => {
    render(<OptimizerPanel availableETFs={mockAvailableETFs} onOptimized={vi.fn()} />);

    const checkboxes = screen.getAllByRole('checkbox');
    expect(checkboxes).toHaveLength(4);
    checkboxes.forEach((cb, i) => {
      expect(cb.parentElement).toHaveTextContent(mockAvailableETFs[i].code);
    });
  });

  it('应显示"已选择: N 只ETF"计数', () => {
    render(<OptimizerPanel availableETFs={mockAvailableETFs} onOptimized={vi.fn()} />);

    expect(screen.getByText('已选择: 0 只ETF')).toBeInTheDocument();
  });

  it('勾选ETF后计数应更新', () => {
    render(<OptimizerPanel availableETFs={mockAvailableETFs} onOptimized={vi.fn()} />);

    const checkboxes = screen.getAllByRole('checkbox');
    fireEvent.click(checkboxes[0]);
    fireEvent.click(checkboxes[1]);

    expect(screen.getByText('已选择: 2 只ETF')).toBeInTheDocument();
  });

  it('"全选"按钮应勾选所有ETF', () => {
    render(<OptimizerPanel availableETFs={mockAvailableETFs} onOptimized={vi.fn()} />);

    fireEvent.click(screen.getByRole('button', { name: '全选' }));

    const checkboxes = screen.getAllByRole('checkbox');
    checkboxes.forEach((cb) => expect(cb).toBeChecked());
    expect(screen.getByText('已选择: 4 只ETF')).toBeInTheDocument();
  });

  it('全选后按钮文字应变为"取消全选"', () => {
    render(<OptimizerPanel availableETFs={mockAvailableETFs} onOptimized={vi.fn()} />);

    fireEvent.click(screen.getByRole('button', { name: '全选' }));

    expect(screen.getByRole('button', { name: '取消全选' })).toBeInTheDocument();
  });

  it('"取消全选"应取消所有勾选', () => {
    render(<OptimizerPanel availableETFs={mockAvailableETFs} onOptimized={vi.fn()} />);

    fireEvent.click(screen.getByRole('button', { name: '全选' }));
    fireEvent.click(screen.getByRole('button', { name: '取消全选' }));

    const checkboxes = screen.getAllByRole('checkbox');
    checkboxes.forEach((cb) => expect(cb).not.toBeChecked());
    expect(screen.getByText('已选择: 0 只ETF')).toBeInTheDocument();
  });

  it('应渲染约束输入框（最大权重、目标波动率）', () => {
    render(<OptimizerPanel availableETFs={mockAvailableETFs} onOptimized={vi.fn()} />);

    const spinbuttons = screen.getAllByRole('spinbutton');
    expect(spinbuttons).toHaveLength(2);
    expect(spinbuttons[0].getAttribute('placeholder')).toBe('不限制');
    expect(spinbuttons[1].getAttribute('placeholder')).toBe('不限制');
  });

  it('少于2只ETF时"开始优化"按钮应禁用', () => {
    render(<OptimizerPanel availableETFs={mockAvailableETFs} onOptimized={vi.fn()} />);

    const optimizeBtn = screen.getByRole('button', { name: '开始优化' });
    expect(optimizeBtn).toBeDisabled();
  });

  it('少于2只ETF时"开始优化"按钮应禁用（防止无效请求）', () => {
    render(<OptimizerPanel availableETFs={mockAvailableETFs} onOptimized={vi.fn()} />);

    const optimizeBtn = screen.getByRole('button', { name: '开始优化' });
    expect(optimizeBtn).toBeDisabled();
  });

  it('选择2只及以上ETF时"开始优化"应可用', () => {
    render(<OptimizerPanel availableETFs={mockAvailableETFs} onOptimized={vi.fn()} />);

    fireEvent.click(screen.getAllByRole('checkbox')[0]);
    fireEvent.click(screen.getAllByRole('checkbox')[1]);

    expect(screen.getByRole('button', { name: '开始优化' })).toBeEnabled();
  });

  it('优化中应显示"优化中..."并禁用按钮', () => {
    (fetch as ReturnType<typeof vi.fn>).mockImplementation(
      () => new Promise(() => {}),
    );

    render(<OptimizerPanel availableETFs={mockAvailableETFs} onOptimized={vi.fn()} />);

    fireEvent.click(screen.getAllByRole('checkbox')[0]);
    fireEvent.click(screen.getAllByRole('checkbox')[1]);
    fireEvent.click(screen.getByRole('button', { name: '开始优化' }));

    const btn = screen.getByRole('button', { name: '优化中...' });
    expect(btn).toBeInTheDocument();
    expect(btn).toBeDisabled();
  });

  it('优化成功应显示结果面板（状态、指标、权重）', async () => {
    (fetch as ReturnType<typeof vi.fn>).mockResolvedValueOnce(mockFetchSuccess(mockOptimizationResult));
    const onOptimized = vi.fn();

    render(<OptimizerPanel availableETFs={mockAvailableETFs} onOptimized={onOptimized} />);

    fireEvent.click(screen.getAllByRole('checkbox')[0]);
    fireEvent.click(screen.getAllByRole('checkbox')[1]);
    fireEvent.click(screen.getAllByRole('checkbox')[2]);
    fireEvent.click(screen.getByRole('button', { name: '开始优化' }));

    await waitFor(() => {
      expect(screen.getByText('优化成功')).toBeInTheDocument();
      expect(screen.getByText('预期收益')).toBeInTheDocument();
      expect(screen.getByText('13.50%')).toBeInTheDocument();
      expect(screen.getByText('17.20%')).toBeInTheDocument();
      expect(screen.getByText('0.7200')).toBeInTheDocument();
      expect(screen.getByText('45.0%')).toBeInTheDocument();
    });

    expect(onOptimized).toHaveBeenCalledWith(mockOptimizationResult.weights);
  });

  it('优化成功后点击"应用此组合"应调用onOptimized', async () => {
    (fetch as ReturnType<typeof vi.fn>).mockResolvedValueOnce(mockFetchSuccess(mockOptimizationResult));
    const onOptimized = vi.fn();

    render(<OptimizerPanel availableETFs={mockAvailableETFs} onOptimized={onOptimized} />);

    fireEvent.click(screen.getAllByRole('checkbox')[0]);
    fireEvent.click(screen.getAllByRole('checkbox')[1]);
    fireEvent.click(screen.getByRole('button', { name: '开始优化' }));

    await waitFor(() => screen.getByRole('button', { name: '应用此组合' }));
    fireEvent.click(screen.getByRole('button', { name: '应用此组合' }));

    expect(onOptimized).toHaveBeenCalledTimes(2);
    expect(onOptimized).toHaveBeenLastCalledWith(mockOptimizationResult.weights);
  });

  it('优化失败应显示"优化失败"及失败消息', async () => {
    (fetch as ReturnType<typeof vi.fn>).mockResolvedValueOnce(
      mockFetchSuccess({ ...mockOptimizationResult, success: false, message: '数据不足' }),
    );

    render(<OptimizerPanel availableETFs={mockAvailableETFs} onOptimized={vi.fn()} />);

    fireEvent.click(screen.getAllByRole('checkbox')[0]);
    fireEvent.click(screen.getAllByRole('checkbox')[1]);
    fireEvent.click(screen.getByRole('button', { name: '开始优化' }));

    await waitFor(() => {
      expect(screen.getByText('优化失败')).toBeInTheDocument();
      expect(screen.getByText('数据不足')).toBeInTheDocument();
    });
  });

  it('API请求失败应显示错误信息', async () => {
    (fetch as ReturnType<typeof vi.fn>).mockResolvedValueOnce({
      ok: false,
      json: () => Promise.resolve({ detail: '服务器内部错误' }),
      status: 500,
    });

    render(<OptimizerPanel availableETFs={mockAvailableETFs} onOptimized={vi.fn()} />);

    fireEvent.click(screen.getAllByRole('checkbox')[0]);
    fireEvent.click(screen.getAllByRole('checkbox')[1]);
    fireEvent.click(screen.getByRole('button', { name: '开始优化' }));

    await waitFor(() => {
      expect(screen.getByText('服务器内部错误')).toBeInTheDocument();
    });
  });

  it('空ETF列表应渲染无勾选项', () => {
    render(<OptimizerPanel availableETFs={[]} onOptimized={vi.fn()} />);

    expect(screen.queryAllByRole('checkbox')).toHaveLength(0);
    expect(screen.getByText('已选择: 0 只ETF')).toBeInTheDocument();
  });
});

// ======================================================================
//                      CompareTable 组件测试
// ======================================================================

describe('CompareTable 组件', () => {
  const mockComparisonResult = {
    portfolios: [
      {
        ...mockPortfolioMetrics,
        portfolioId: 0,
        portfolioName: '组合A',
      },
      {
        ...mockPortfolioMetrics,
        total_return: 22.0,
        annualized_return: 18.0,
        volatility: 22.0,
        sharpe_ratio: 0.81,
        max_drawdown: -12.0,
        holding_period: 252,
        nav_series: [1, 1.1, 1.2],
        daily_returns: [0.1, 0.09],
        etf_metrics: {},
        portfolioId: 1,
        portfolioName: '组合B',
      },
    ],
  };

  it('无组合时应显示空态提示', () => {
    render(<CompareTable portfolios={[]} />);

    expect(screen.getByText('请先添加多个组合进行对比')).toBeInTheDocument();
  });

  it('加载中应显示"对比分析中..."', () => {
    (fetch as ReturnType<typeof vi.fn>).mockImplementation(
      () => new Promise(() => {}),
    );
    render(<CompareTable portfolios={[{ '510300.SH': 1.0 }]} />);

    expect(screen.getByText('对比分析中...')).toBeInTheDocument();
  });

  it('应渲染三种视图切换按钮（表格/柱状图/雷达图）', async () => {
    (fetch as ReturnType<typeof vi.fn>).mockResolvedValueOnce(mockFetchSuccess(mockComparisonResult));
    render(<CompareTable portfolios={[{ '510300.SH': 1.0 }, { '510500.SH': 1.0 }]} />);

    await waitFor(() => {
      expect(screen.getByRole('button', { name: '表格' })).toBeInTheDocument();
      expect(screen.getByRole('button', { name: '柱状图' })).toBeInTheDocument();
      expect(screen.getByRole('button', { name: '雷达图' })).toBeInTheDocument();
    });
  });

  it('默认应显示表格视图', async () => {
    (fetch as ReturnType<typeof vi.fn>).mockResolvedValueOnce(mockFetchSuccess(mockComparisonResult));
    render(<CompareTable portfolios={[{ '510300.SH': 1.0 }, { '510500.SH': 1.0 }]} />);

    await waitFor(() => {
      const table = screen.getByRole('table');
      expect(table).toBeInTheDocument();
    });
  });

  it('表格应包含所有6个指标行', async () => {
    (fetch as ReturnType<typeof vi.fn>).mockResolvedValueOnce(mockFetchSuccess(mockComparisonResult));
    render(<CompareTable portfolios={[{ '510300.SH': 1.0 }, { '510500.SH': 1.0 }]} />);

    await waitFor(() => {
      expect(screen.getByText('累计收益')).toBeInTheDocument();
      expect(screen.getByText('年化收益')).toBeInTheDocument();
      expect(screen.getByText('波动率')).toBeInTheDocument();
      expect(screen.getByText('夏普比率')).toBeInTheDocument();
      expect(screen.getByText('最大回撤')).toBeInTheDocument();
      expect(screen.getByText('持有天数')).toBeInTheDocument();
    });
  });

  it('表格表头应展示各组合名称', async () => {
    (fetch as ReturnType<typeof vi.fn>).mockResolvedValueOnce(mockFetchSuccess(mockComparisonResult));
    render(<CompareTable portfolios={[{ '510300.SH': 1.0 }, { '510500.SH': 1.0 }]} />);

    await waitFor(() => {
      expect(screen.getByText('组合A')).toBeInTheDocument();
      expect(screen.getByText('组合B')).toBeInTheDocument();
    });
  });

  it('点击"柱状图"应切换到柱状图视图', async () => {
    (fetch as ReturnType<typeof vi.fn>).mockResolvedValueOnce(mockFetchSuccess(mockComparisonResult));
    const { container } = render(
      <CompareTable portfolios={[{ '510300.SH': 1.0 }, { '510500.SH': 1.0 }]} />,
    );

    await waitFor(() => screen.getByRole('button', { name: '柱状图' }));
    fireEvent.click(screen.getByRole('button', { name: '柱状图' }));

    expect(container.querySelector('.bar-chart')).toBeInTheDocument();
  });

  it('柱状图应包含年化收益、波动率、夏普比率三组', async () => {
    (fetch as ReturnType<typeof vi.fn>).mockResolvedValueOnce(mockFetchSuccess(mockComparisonResult));
    const { container } = render(
      <CompareTable portfolios={[{ '510300.SH': 1.0 }, { '510500.SH': 1.0 }]} />,
    );

    await waitFor(() => screen.getByRole('button', { name: '柱状图' }));
    fireEvent.click(screen.getByRole('button', { name: '柱状图' }));

    const barGroups = container.querySelectorAll('.bar-chart-group');
    expect(barGroups).toHaveLength(3);
  });

  it('点击"雷达图"应切换到雷达图视图', async () => {
    (fetch as ReturnType<typeof vi.fn>).mockResolvedValueOnce(mockFetchSuccess(mockComparisonResult));
    const { container } = render(
      <CompareTable portfolios={[{ '510300.SH': 1.0 }, { '510500.SH': 1.0 }]} />,
    );

    await waitFor(() => screen.getByRole('button', { name: '雷达图' }));
    fireEvent.click(screen.getByRole('button', { name: '雷达图' }));

    expect(container.querySelector('.radar-chart')).toBeInTheDocument();
    expect(container.querySelector('.radar-legend')).toBeInTheDocument();
  });

  it('雷达图应在4个轴上渲染标签', async () => {
    (fetch as ReturnType<typeof vi.fn>).mockResolvedValueOnce(mockFetchSuccess(mockComparisonResult));
    const { container } = render(
      <CompareTable portfolios={[{ '510300.SH': 1.0 }, { '510500.SH': 1.0 }]} />,
    );

    await waitFor(() => screen.getByRole('button', { name: '雷达图' }));
    fireEvent.click(screen.getByRole('button', { name: '雷达图' }));

    const svg = container.querySelector('.radar-chart')!;
    const texts = svg.querySelectorAll('text');
    const labels = Array.from(texts).map((t) => t.textContent);
    expect(labels).toContain('年化收益');
    expect(labels).toContain('波动率');
    expect(labels).toContain('夏普比率');
    expect(labels).toContain('最大回撤');
  });

  it('对比失败应显示错误信息', async () => {
    (fetch as ReturnType<typeof vi.fn>).mockRejectedValueOnce(new Error('对比失败'));
    render(<CompareTable portfolios={[{ '510300.SH': 1.0 }, { '510500.SH': 1.0 }]} />);

    await waitFor(() => {
      expect(screen.getByText('对比失败')).toBeInTheDocument();
    });
  });

  it('portfolios列表为空数组时不发起API请求', () => {
    (fetch as ReturnType<typeof vi.fn>).mockResolvedValue(mockFetchSuccess({}));
    render(<CompareTable portfolios={[]} />);

    expect(fetch).not.toHaveBeenCalled();
  });

  it('雷达图应渲染legend色块图例', async () => {
    (fetch as ReturnType<typeof vi.fn>).mockResolvedValueOnce(mockFetchSuccess(mockComparisonResult));
    const { container } = render(
      <CompareTable portfolios={[{ '510300.SH': 1.0 }, { '510500.SH': 1.0 }]} />,
    );

    await waitFor(() => screen.getByRole('button', { name: '雷达图' }));
    fireEvent.click(screen.getByRole('button', { name: '雷达图' }));

    const legendItems = container.querySelectorAll('.legend-item');
    expect(legendItems).toHaveLength(2);
  });

  it('点击"表格"可从其他视图切回表格', async () => {
    (fetch as ReturnType<typeof vi.fn>).mockResolvedValueOnce(mockFetchSuccess(mockComparisonResult));
    const { container } = render(
      <CompareTable portfolios={[{ '510300.SH': 1.0 }, { '510500.SH': 1.0 }]} />,
    );

    await waitFor(() => screen.getByRole('button', { name: '雷达图' }));
    fireEvent.click(screen.getByRole('button', { name: '雷达图' }));
    expect(container.querySelector('.radar-chart')).toBeInTheDocument();

    fireEvent.click(screen.getByRole('button', { name: '表格' }));
    expect(screen.getByRole('table')).toBeInTheDocument();
  });
});

// ======================================================================
//                 集成流程测试
// ======================================================================

describe('集成流程', () => {
  it('选择ETF → 评估 → 显示指标（完整流程）', async () => {
    (fetch as ReturnType<typeof vi.fn>).mockImplementation((url: RequestInfo | URL) => {
      const urlStr = url.toString();
      if (urlStr.includes('/health')) return mockFetchSuccess(mockHealthResponse);
      if (urlStr.includes('/api/etfs')) return mockFetchSuccess(mockETFList);
      if (urlStr.includes('/api/portfolio/evaluate')) return mockFetchSuccess(mockPortfolioMetrics);
      return mockFetchSuccess({});
    });

    render(<App />);

    // Wait for ETF list to load
    const etfName = await screen.findByText('沪深300ETF', {}, { timeout: 5000 });

    // Click ETF item to select it
    fireEvent.click(etfName.closest('.etf-item')!);

    // Wait for evaluation to complete (metrics should appear)
    // Note: loading state may not be visible due to fast mock resolution
    expect(await screen.findByText('累计收益', {}, { timeout: 5000 })).toBeInTheDocument();
    expect(screen.getByText('15.50%')).toBeInTheDocument();
    expect(screen.getByText('18.70%')).toBeInTheDocument();
  });

  it('保存组合后按钮仍存在', async () => {
    (fetch as ReturnType<typeof vi.fn>).mockImplementation((url: RequestInfo | URL) => {
      const urlStr = url.toString();
      if (urlStr.includes('/health')) return mockFetchSuccess(mockHealthResponse);
      if (urlStr.includes('/api/etfs')) return mockFetchSuccess(mockETFList);
      if (urlStr.includes('/api/portfolio/evaluate')) return mockFetchSuccess(mockPortfolioMetrics);
      return mockFetchSuccess({});
    });

    render(<App />);

    const etfName = await screen.findByText('沪深300ETF', {}, { timeout: 5000 });
    fireEvent.click(etfName.closest('.etf-item')!);

    // Wait for save button to appear
    const saveBtn = await screen.findByRole('button', { name: '保存当前组合' }, { timeout: 5000 });
    fireEvent.click(saveBtn);

    // Save button should still exist
    expect(screen.getByRole('button', { name: '保存当前组合' })).toBeInTheDocument();
  });

  it('切换至对比模式后应展示对比组件', async () => {
    (fetch as ReturnType<typeof vi.fn>).mockImplementation((url: RequestInfo | URL) => {
      const urlStr = url.toString();
      if (urlStr.includes('/health')) return mockFetchSuccess(mockHealthResponse);
      if (urlStr.includes('/api/etfs')) return mockFetchSuccess(mockETFList);
      return mockFetchSuccess({});
    });

    render(<App />);

    fireEvent.click(screen.getByRole('button', { name: '对比模式' }));

    expect(screen.getByText('请从左侧选择ETF构建组合')).toBeInTheDocument();
  });
});

// ======================================================================
//                 边界条件测试
// ======================================================================

describe('边界条件', () => {
  it('ETF权重为负值时输入框value不应为负', async () => {
    (fetch as ReturnType<typeof vi.fn>).mockResolvedValueOnce(mockFetchSuccess(mockETFList));
    render(<ETFSelector selectedETFs={{ '510300.SH': 0.6 }} onChange={vi.fn()} />);

    await waitFor(() => screen.getAllByText('沪深300ETF'));
    const weightInput = screen.getByRole('spinbutton');

    fireEvent.change(weightInput, { target: { value: '-10' } });

    expect(weightInput.getAttribute('min')).toBe('0');
  });

  it('ETF权重超过100%时输入框应有max=100', async () => {
    (fetch as ReturnType<typeof vi.fn>).mockResolvedValueOnce(mockFetchSuccess(mockETFList));
    render(<ETFSelector selectedETFs={{ '510300.SH': 0.6 }} onChange={vi.fn()} />);

    await waitFor(() => screen.getAllByText('沪深300ETF'));
    const weightInput = screen.getByRole('spinbutton');

    expect(weightInput.getAttribute('max')).toBe('100');
  });

  it('PortfolioCard无id无name时应显示"组合"', () => {
    render(<PortfolioCard weights={{ '510300.SH': 1.0 }} />);

    expect(screen.getByText('组合')).toBeInTheDocument();
  });

  it('OptimizerPanel约束输入清空后应传undefined', async () => {
    const onOptimized = vi.fn();
    const fetchSpy = vi.fn().mockResolvedValueOnce(mockFetchSuccess(mockOptimizationResult));
    globalThis.fetch = fetchSpy as unknown as typeof fetch;

    render(<OptimizerPanel availableETFs={mockETFList.etfs.slice(0, 2)} onOptimized={onOptimized} />);

    const inputs = screen.getAllByRole('spinbutton');
    fireEvent.change(inputs[0], { target: { value: '30' } });
    fireEvent.change(inputs[0], { target: { value: '' } });

    fireEvent.click(screen.getAllByRole('checkbox')[0]);
    fireEvent.click(screen.getAllByRole('checkbox')[1]);
    fireEvent.click(screen.getByRole('button', { name: '开始优化' }));

    await waitFor(() => {
      const bodyJson = JSON.parse(fetchSpy.mock.calls[0][1].body);
      expect(bodyJson.max_weight).toBeUndefined();
    });
  });

  it('选择单只ETF再取消后选择区域应隐藏', async () => {
    (fetch as ReturnType<typeof vi.fn>).mockResolvedValueOnce(mockFetchSuccess(mockETFList));
    const { rerender } = render(
      <ETFSelector selectedETFs={{ '510300.SH': 1.0 }} onChange={vi.fn()} />,
    );

    await waitFor(() => {
      expect(screen.getByText(/已选组合/)).toBeInTheDocument();
    });

    rerender(<ETFSelector selectedETFs={{}} onChange={vi.fn()} />);

    expect(screen.queryByText(/已选组合/)).not.toBeInTheDocument();
  });

  it('ETF列表API返回空etfs数组时不显示列表项', async () => {
    (fetch as ReturnType<typeof vi.fn>).mockResolvedValueOnce(mockFetchSuccess({ total: 0, etfs: [] }));
    render(<ETFSelector selectedETFs={{}} onChange={vi.fn()} />);

    await waitFor(() => {
      const etfList = document.querySelector('.etf-list');
      expect(etfList?.children.length).toBe(0);
    });
  });
});

// ======================================================================
//                 可访问性测试
// ======================================================================

describe('可访问性', () => {
  it('搜索输入框应有placeholder文本', () => {
    (fetch as ReturnType<typeof vi.fn>).mockResolvedValueOnce(mockFetchSuccess(mockETFList));
    render(<ETFSelector selectedETFs={{}} onChange={vi.fn()} />);

    expect(screen.getByPlaceholderText('搜索ETF名称或代码...')).toBeInTheDocument();
  });

  it('视图切换按钮应有明确文本', () => {
    (fetch as ReturnType<typeof vi.fn>).mockResolvedValueOnce(mockFetchSuccess(mockHealthResponse));
    render(<App />);

    expect(screen.getByRole('button', { name: '单组合' })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: '对比模式' })).toBeInTheDocument();
  });

  it('优化按钮禁用时应为disabled状态', () => {
    render(<OptimizerPanel availableETFs={mockETFList.etfs.slice(0, 1)} onOptimized={vi.fn()} />);

    expect(screen.getByRole('button', { name: '开始优化' })).toBeDisabled();
  });

  it('对比视图切换按钮应有active状态标识', async () => {
    (fetch as ReturnType<typeof vi.fn>).mockResolvedValueOnce(mockFetchSuccess(mockComparisonResult));
    render(<CompareTable portfolios={[{ '510300.SH': 1.0 }, { '510500.SH': 1.0 }]} />);

    await waitFor(() => {
      const tableBtn = screen.getByRole('button', { name: '表格' });
      expect(tableBtn.classList.contains('active')).toBe(true);
    });
  });
});
