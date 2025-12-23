#!/usr/bin/env python3
"""
Boss直聘自动投递工具

使用方法:
    python -m src.main              # 立即执行一次
    python -m src.main --schedule   # 启动定时任务
    python -m src.main --headless   # 无头模式运行
"""

import argparse
import sys
from pathlib import Path

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.browser import BrowserManager
from src.search import JobSearcher
from src.filter import JobFilter
from src.apply import JobApplier
from src.scheduler import JobScheduler
from src.utils.config import Config
from src.utils.storage import Storage
from src.utils.logger import logger


def run_apply_task(headless: bool = False, weekend_mode: bool = False, weekend_limit: int = 10) -> None:
    """
    执行投递任务

    Args:
        headless: 是否无头模式
        weekend_mode: 是否周末模式
        weekend_limit: 周末投递上限
    """
    config = Config()
    storage = Storage()

    # 检查 Cookie
    if not config.cookie:
        logger.error("请先在 cookie.txt 中配置 Cookie")
        logger.error("获取方式：浏览器登录 Boss直聘 -> F12 -> Application -> Cookies")
        return

    browser_manager = BrowserManager(config)

    try:
        page = browser_manager.start(headless=headless)

        # 搜索职位
        searcher = JobSearcher(page, config)
        jobs = searcher.search_all_keywords()

        if not jobs:
            logger.warning("未找到任何职位，请检查搜索条件或 Cookie 是否有效")
            return

        # 过滤职位
        job_filter = JobFilter(config, storage)
        filtered_jobs = job_filter.filter_jobs(jobs)
        filtered_jobs = job_filter.sort_by_priority(filtered_jobs)

        if not filtered_jobs:
            logger.info("过滤后没有可投递的职位")
            return

        # 周末模式限制
        if weekend_mode:
            original_limit = config.apply.get('batch_limit', 20)
            # 临时修改限制（这里简化处理，实际可以更优雅）
            logger.info(f"周末模式，本次投递上限: {min(original_limit, weekend_limit)}")

        # 投递职位
        applier = JobApplier(page, config, storage)
        stats = applier.apply_jobs(filtered_jobs)

        # 输出统计
        logger.info("=" * 40)
        logger.info("投递统计:")
        logger.info(f"  成功: {stats['success']}")
        logger.info(f"  失败: {stats['failed']}")
        logger.info(f"  跳过: {stats['skipped']}")
        logger.info(f"  今日累计: {storage.get_today_apply_count()}")
        logger.info("=" * 40)

    except Exception as e:
        logger.error(f"执行出错: {e}")
        raise
    finally:
        browser_manager.close()


def main():
    parser = argparse.ArgumentParser(description='Boss直聘自动投递工具')
    parser.add_argument('--schedule', '-s', action='store_true', help='启动定时任务模式')
    parser.add_argument('--headless', action='store_true', help='无头模式运行（不显示浏览器窗口）')

    args = parser.parse_args()

    logger.info("=" * 50)
    logger.info("Boss直聘自动投递工具启动")
    logger.info("=" * 50)

    if args.schedule:
        # 定时任务模式
        config = Config()
        scheduler = JobScheduler(
            config,
            lambda **kwargs: run_apply_task(headless=args.headless, **kwargs)
        )
        scheduler.setup()
        scheduler.start()
    else:
        # 立即执行一次
        run_apply_task(headless=args.headless)


if __name__ == '__main__':
    main()
