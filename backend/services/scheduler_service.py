"""
定时任务服务模块

本模块提供ETF数据的定时同步功能。

主要功能：
1. 每日定时从AkShare同步ETF数据到数据库
2. 支持手动触发同步任务
3. 提供进度回调机制

调度策略：
- 默认每日16:00执行（A股收盘后）
- 首次启动时会执行一次全量同步

作者: ETF组合系统
版本: 1.0.0
"""

import logging
from datetime import datetime, time
from typing import Callable, Optional

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

from backend.services.etf_data_service import sync_all_etf_data

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

scheduler = BackgroundScheduler()


def sync_etf_data_job():
    """
    定时同步ETF数据任务

    这是每日定时执行的任务函数。
    记录开始和结束时间，方便追踪同步状态。
    """
    start_time = datetime.now()
    logger.info(f"========== 开始执行ETF数据同步任务 ==========")
    logger.info(f"开始时间: {start_time.strftime('%Y-%m-%d %H:%M:%S')}")

    try:
        def progress_callback(current: int, total: int, message: str):
            if current % 50 == 0 or current == total:
                logger.info(f"进度: [{current}/{total}] {message}")

        stats = sync_all_etf_data(progress_callback=progress_callback)

        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()

        logger.info(f"========== ETF数据同步完成 ==========")
        logger.info(f"结束时间: {end_time.strftime('%Y-%m-%d %H:%M:%S')}")
        logger.info(f"耗时: {duration:.1f}秒")
        logger.info(f"ETF总数: {stats['etf_count']}")
        logger.info(f"净值记录: {stats['nav_count']}")
        logger.info(f"失败数量: {stats['errors']}")

    except Exception as e:
        logger.error(f"ETF数据同步任务执行失败: {e}", exc_info=True)


def start_scheduler(hour: int = 16, minute: int = 0):
    """
    启动定时调度器

    参数:
        hour: 执行小时（默认16:00，A股收盘后）
        minute: 执行分钟

    示例:
        >>> start_scheduler()  # 每日16:00执行
        >>> start_scheduler(hour=8, minute=30)  # 每日8:30执行
    """
    if scheduler.running:
        logger.warning("调度器已在运行中")
        return

    trigger = CronTrigger(hour=hour, minute=minute)

    scheduler.add_job(
        sync_etf_data_job,
        trigger=trigger,
        id='sync_etf_data',
        name='每日ETF数据同步',
        replace_existing=True,
        misfire_grace_time=3600
    )

    scheduler.start()
    logger.info(f"定时调度器已启动，下次执行时间: {hour:02d}:{minute:02d}")

    sync_etf_data_job()


def stop_scheduler():
    """
    停止定时调度器

    在应用关闭时调用，确保调度器正确停止。
    """
    if scheduler.running:
        scheduler.shutdown(wait=False)
        logger.info("定时调度器已停止")


def run_sync_now() -> dict:
    """
    立即执行一次数据同步（手动触发）

    返回:
        dict: 同步统计信息

    示例:
        >>> stats = run_sync_now()
        >>> print(f"同步了{stats['nav_count']}条记录")
    """
    logger.info("手动触发ETF数据同步...")
    sync_etf_data_job()
    return {"status": "completed"}


def get_next_run_time() -> Optional[str]:
    """
    获取下次调度执行时间

    返回:
        Optional[str]: 下次执行时间的ISO格式字符串，如果未在运行返回None
    """
    job = scheduler.get_job('sync_etf_data')
    if job and job.next_run_time:
        return job.next_run_time.isoformat()
    return None


def get_scheduler_status() -> dict:
    """
    获取调度器状态

    返回:
        dict: 包含调度器运行状态和下次执行时间
    """
    job = scheduler.get_job('sync_etf_data')
    return {
        "running": scheduler.running,
        "next_run_time": job.next_run_time.isoformat() if job and job.next_run_time else None,
        "job_id": "sync_etf_data",
        "job_name": "每日ETF数据同步"
    }


if __name__ == "__main__":
    print("定时任务服务模块测试...")
    print("执行一次同步任务...")
    sync_etf_data_job()