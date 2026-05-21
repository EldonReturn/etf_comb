"""
ETF组合推荐系统 - FastAPI主应用

本模块是整个后端应用的主入口，提供RESTful API接口。

主要功能：
1. ETF信息查询（列表、历史净值）
2. 组合评估（收益率、夏普比率、最大回撤）
3. 组合对比（多组合并列比较）
4. 最优组合优化（最大收益组合求解）
5. 数据同步管理（手动触发/定时任务）

启动方式：
    uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000

API文档：
    启动后访问 http://localhost:8000/docs 查看交互式API文档

作者: ETF组合系统
版本: 1.0.0
"""

import logging
from datetime import date, datetime
from contextlib import asynccontextmanager
from pathlib import Path
from typing import List, Dict, Optional

from dotenv import load_dotenv
load_dotenv(dotenv_path=Path(__file__).resolve().parent / '.env')

from fastapi import FastAPI, Depends, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from backend.db.database import (
    init_session_factories,
    ensure_data_dir,
    close_all_sessions,
    get_session,
)
from backend.db.models import create_database, ETFInfo, ETFNavHistory
from backend.services import (
    get_etf_info_from_db,
    get_etf_history_from_db,
    sync_all_etf_data,
    evaluate_portfolio,
    compare_portfolios,
    optimize_max_return,
    optimize_with_constraints,
    fetch_trade_dates,
)
from backend.routes.admin import router as admin_router
from backend.routes.auth import router as auth_router, require_auth

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    应用生命周期管理器

    在应用启动时初始化数据库，
    在应用关闭时清理资源。
    """
    logger.info("应用启动中...")
    ensure_data_dir()
    create_database()
    init_session_factories()
    logger.info("数据库初始化完成")

    yield

    logger.info("应用关闭中...")
    close_all_sessions()
    logger.info("资源清理完成")


app = FastAPI(
    title="ETF组合推荐系统",
    description="""
## ETF组合推荐系统 API

提供以下功能：

- **ETF查询**: 获取ETF列表、历史净值
- **组合评估**: 计算组合的收益率、夏普比率、最大回撤等指标
- **组合对比**: 多组合并列比较
- **最优组合**: 使用均值-方差优化寻找最大收益组合
- **数据同步**: 从TickFlow同步ETF数据到本地数据库
    """,
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(admin_router)
app.include_router(auth_router)


class PortfolioEvaluateRequest(BaseModel):
    """组合评估请求模型"""
    weights: Dict[str, float] = Field(
        ...,
        description="ETF权重字典，键为ETF代码，值为权重(0-1之间)",
        example={"510300": 0.6, "510500": 0.4}
    )
    period: Optional[str] = Field(
        None,
        description="时间区段，如 '1m', '3m', '6m', '1y', '2y', '3y', '5y'",
        example="1y"
    )
    benchmark_code: Optional[str] = Field(
        None,
        description="基准ETF代码，默认510310",
        example="510310"
    )


class PortfolioCompareRequest(BaseModel):
    """组合对比请求模型"""
    portfolios: List[Dict[str, float]] = Field(
        ...,
        description="多个组合的权重列表",
        example=[
            {"510300": 1.0},
            {"510300": 0.5, "510500": 0.5}
        ]
    )
    period: Optional[str] = Field(
        None,
        description="时间区段，如 '1m', '3m', '6m', '1y', '2y', '3y', '5y'",
        example="1y"
    )
    benchmark_code: Optional[str] = Field(
        None,
        description="基准ETF代码，默认510310",
        example="510310"
    )


class OptimizeRequest(BaseModel):
    """优化请求模型"""
    etf_codes: List[str] = Field(
        ...,
        description="可选ETF代码列表",
        example=["510300", "510500", "159915"]
    )
    max_weight: Optional[float] = Field(
        None,
        description="单个ETF最大权重限制（可选）",
        example=0.3
    )
    target_volatility: Optional[float] = Field(
        None,
        description="目标波动率上限（可选，百分比形式）",
        example=20.0
    )
    period: Optional[str] = Field(
        None,
        description="时间区段，如 '1m', '3m', '6m', '1y', '2y', '3y', '5y'",
        example="1y"
    )


class SyncRequest(BaseModel):
    """同步请求模型"""
    period: Optional[str] = Field(
        None,
        description="同步时间区段，如 '1m', '3m', '6m', '1y', '2y', '3y', '5y'",
        example="1y"
    )


class ETFListResponse(BaseModel):
    """ETF列表响应模型"""
    total: int
    etfs: List[Dict]


class SyncResponse(BaseModel):
    """同步响应模型"""
    status: str
    etf_count: int
    nav_count: int
    errors: int


@app.get("/", tags=["首页"])
async def root():
    """
    首页

    返回系统欢迎信息和基本状态。
    """
    return {
        "name": "ETF组合推荐系统",
        "version": "1.0.0",
        "status": "running",
        "docs": "/docs"
    }


@app.get("/api/etfs", response_model=ETFListResponse, tags=["ETF查询"])
async def get_etfs(
    category: Optional[str] = Query(None, description="按分类筛选ETF"),
    search: Optional[str] = Query(None, description="搜索ETF名称或代码"),
    period: Optional[str] = Query(None, description="时间区段，用于检查数据是否充足"),
    session_id: str = Depends(require_auth),
):
    """
    获取ETF列表

    返回数据库中所有已同步的ETF信息。
    支持按分类和关键词筛选。
    支持按时间区段检查数据是否充足。

    参数:
        category: ETF分类（宽基指数/行业指数/债券/商品/境外）
        search: 搜索关键词（匹配代码或名称）
        period: 时间区段（如 '1m', '3m', '6m', '1y', '2y', '3y', '5y'）

    返回:
        ETFListResponse: 包含总数和ETF列表
    """
    with get_session() as session:
        etfs = get_etf_info_from_db(session, period)

        if category:
            etfs = [e for e in etfs if e["category"] == category]

        if search:
            search = search.upper()
            etfs = [
                e for e in etfs
                if search in e["code"].upper() or search in e["name"].upper()
            ]

        return ETFListResponse(total=len(etfs), etfs=etfs)


@app.get("/api/etf/{code}/history", tags=["ETF查询"])
async def get_etf_history(
    code: str,
    start_date: Optional[date] = Query(None, description="起始日期"),
    end_date: Optional[date] = Query(None, description="结束日期"),
    session_id: str = Depends(require_auth),
):
    """
    获取ETF历史净值

    从数据库读取指定ETF的历史净值数据。

    参数:
        code: ETF代码，如 "510300"
        start_date: 起始日期（可选）
        end_date: 结束日期（可选）

    返回:
        净值记录列表
    """
    with get_session() as session:
        history = get_etf_history_from_db(
            session, code, start_date, end_date
        )

        if not history:
            raise HTTPException(status_code=404, detail=f"ETF {code} 没有找到历史数据")

        return {
            "code": code,
            "total": len(history),
            "history": history
        }


@app.post("/api/portfolio/evaluate", tags=["组合评估"])
async def evaluate_portfolio_api(portfolio_request: PortfolioEvaluateRequest, session_id: str = Depends(require_auth)):
    """
    评估组合表现

    根据各ETF的权重计算组合的加权业绩指标。

    参数:
        request: PortfolioEvaluateRequest，包含权重字典和时间区段

    返回:
        组合业绩指标
    """
    try:
        result = evaluate_portfolio(portfolio_request.weights, period=portfolio_request.period, benchmark_code=portfolio_request.benchmark_code)
        return result
    except Exception as e:
        logger.error(f"组合评估失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/portfolio/compare", tags=["组合对比"])
async def compare_portfolios_api(compare_request: PortfolioCompareRequest, session_id: str = Depends(require_auth)):
    """
    比较多个组合

    将多个组合并列比较，返回各自的业绩指标。

    参数:
        request: PortfolioCompareRequest，包含多个组合的权重和时间区段

    返回:
        多个组合的业绩指标列表
    """
    try:
        results = compare_portfolios(compare_request.portfolios, period=compare_request.period, benchmark_code=compare_request.benchmark_code)
        return {"portfolios": results}
    except Exception as e:
        logger.error(f"组合对比失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/portfolio/optimize", tags=["最优组合"])
async def optimize_portfolio_api(optimize_request: OptimizeRequest, session_id: str = Depends(require_auth)):
    """
    优化求解最大收益组合

    在给定可选ETF范围内，使用均值-方差优化寻找最大收益组合。

    参数:
        optimize_request: OptimizeRequest，包含可选ETF列表、约束条件和时间区段

    返回:
        最优组合的权重和预期业绩指标
    """
    try:
        has_constraints = optimize_request.max_weight is not None or optimize_request.target_volatility is not None
        if has_constraints:
            result = optimize_with_constraints(
                etf_codes=optimize_request.etf_codes,
                max_weight=optimize_request.max_weight / 100 if optimize_request.max_weight is not None else None,
                target_volatility=optimize_request.target_volatility / 100 if optimize_request.target_volatility is not None else None,
                period=optimize_request.period,
            )
        else:
            result = optimize_max_return(
                etf_codes=optimize_request.etf_codes,
                period=optimize_request.period,
            )

        if not result.success:
            raise HTTPException(status_code=400, detail=result.message)

        return {
            "success": result.success,
            "weights": result.weights,
            "expected_return": result.expected_return,
            "volatility": result.volatility,
            "sharpe_ratio": result.sharpe_ratio,
            "message": result.message,
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"组合优化失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/admin/trade_dates/sync", tags=["数据管理"])
async def sync_trade_dates_api():
    """
    手工同步交易日历

    从AkShare获取沪深交易所历史交易日历并写入本地数据库。
    仅新增不存在的日期，不覆盖已有数据。

    返回:
        新增的交易日数量
    """
    try:
        count = fetch_trade_dates()
        return {"status": "completed", "new_trade_dates": count}
    except Exception as e:
        logger.error(f"交易日历同步失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)