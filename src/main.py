#!/usr/bin/env python3
"""
多平台自动投递工具

支持平台：Boss直聘、猎聘网

使用方法:
    python -m src.main                      # 运行所有启用的平台
    python -m src.main --platform boss      # 只运行 Boss直聘
    python -m src.main --platform liepin    # 只运行猎聘网
    python -m src.main --schedule           # 启动定时任务
    python -m src.main --headless           # 无头模式运行
"""

import argparse
import sys
import random
import time
from pathlib import Path
from typing import List, Dict, Any

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.browser import BrowserManager
from src.filter import JobFilter
from src.scheduler import JobScheduler
from src.platforms import BossPlatform, LiepinPlatform
from src.utils.config import Config
from src.utils.storage import Storage
from src.utils.logger import logger


# 平台映射
PLATFORM_CLASSES = {
    'boss': BossPlatform,
    'liepin': LiepinPlatform,
}


def run_platform_task(
    platform_name: str,
    config: Config,
    headless: bool = False,
    weekend_mode: bool = False,
    weekend_limit: int = 10
) -> Dict[str, int]:
    """
    执行单个平台的投递任务

    Args:
        platform_name: 平台名称
        config: 配置对象
        headless: 是否无头模式
        weekend_mode: 是否周末模式
        weekend_limit: 周末投递上限

    Returns:
        投递统计
    """
    stats = {'success': 0, 'failed': 0, 'skipped': 0}

    platform_config = config.get_platform_config(platform_name)
    cookie = config.get_cookie(platform_name)
    storage = Storage(platform=platform_name)

    platform_display = "Boss直聘" if platform_name == "boss" else "猎聘网"

    # 检查 Cookie
    if not cookie:
        cookie_file = "cookie.txt" if platform_name == "boss" else f"cookie_{platform_name}.txt"
        logger.error(f"[{platform_display}] 请先在 {cookie_file} 中配置 Cookie")
        return stats

    # 获取平台类
    PlatformClass = PLATFORM_CLASSES.get(platform_name)
    if not PlatformClass:
        logger.error(f"不支持的平台: {platform_name}")
        return stats

    logger.info(f"[{platform_display}] 开始投递任务")

    # 创建浏览器管理器（使用平台对应的 Cookie）
    browser_manager = BrowserManager(config, platform=platform_name)

    try:
        page = browser_manager.start(headless=headless)

        # 创建平台实例
        platform = PlatformClass(page, platform_config)

        # 搜索职位
        keywords = platform_config.get('search', {}).get('keywords', [])
        jobs = platform.search_all_keywords(keywords)

        if not jobs:
            logger.warning(f"[{platform_display}] 未找到任何职位")
            return stats

        # 过滤职位
        job_filter = JobFilter(platform_config, storage)
        filtered_jobs = job_filter.filter_jobs(jobs)
        filtered_jobs = job_filter.sort_by_priority(filtered_jobs)

        if not filtered_jobs:
            logger.info(f"[{platform_display}] 过滤后没有可投递的职位")
            return stats

        # 投递配置
        apply_config = platform_config.get('apply', {})
        batch_limit = apply_config.get('batch_limit', 20)
        daily_limit = apply_config.get('daily_limit', 50)
        interval_min = apply_config.get('interval_min', 30)
        interval_max = apply_config.get('interval_max', 60)

        # 周末模式限制
        if weekend_mode:
            batch_limit = min(batch_limit, weekend_limit)
            logger.info(f"[{platform_display}] 周末模式，本次投递上限: {batch_limit}")

        # 检查今日投递数量
        today_count = storage.get_today_apply_count()
        if today_count >= daily_limit:
            logger.warning(f"[{platform_display}] 今日已达投递上限 ({daily_limit})")
            return stats

        remaining = min(batch_limit, daily_limit - today_count)
        logger.info(f"[{platform_display}] 今日已投递 {today_count} 个，本次最多投递 {remaining} 个")

        # 投递职位
        for i, job in enumerate(filtered_jobs[:remaining]):
            job_name = job.get('job_name', '')
            company = job.get('company', '')

            logger.info(f"[{platform_display}] [{i + 1}/{remaining}] 投递: {job_name} - {company}")

            try:
                success = platform.apply_job(job)
                if success:
                    stats['success'] += 1
                    storage.add_applied_job(job['job_id'], {
                        'job_name': job_name,
                        'company': company,
                        'hr_name': job.get('hr_name', ''),
                        'salary': job.get('salary', ''),
                        'url': job.get('url', ''),
                        'platform': platform_name
                    })
                    storage.increment_today_apply_count()
                    logger.info(f"[{platform_display}] ✓ 投递成功: {job_name}")
                else:
                    stats['failed'] += 1
                    logger.warning(f"[{platform_display}] ✗ 投递失败: {job_name}")
            except Exception as e:
                stats['failed'] += 1
                logger.error(f"[{platform_display}] ✗ 投递异常: {job_name} - {e}")

            # 随机延迟
            if i < remaining - 1:
                delay = random.uniform(interval_min, interval_max)
                logger.debug(f"等待 {delay:.1f} 秒...")
                time.sleep(delay)

        logger.info(f"[{platform_display}] 投递完成: 成功 {stats['success']}, 失败 {stats['failed']}")

    except Exception as e:
        logger.error(f"[{platform_display}] 执行出错: {e}")
        raise
    finally:
        browser_manager.close()

    return stats


def run_apply_task(
    platforms: List[str] = None,
    headless: bool = False,
    weekend_mode: bool = False,
    weekend_limit: int = 10
) -> None:
    """
    执行投递任务（支持多平台）

    Args:
        platforms: 要运行的平台列表，None 表示运行所有启用的平台
        headless: 是否无头模式
        weekend_mode: 是否周末模式
        weekend_limit: 周末投递上限
    """
    config = Config()

    # 确定要运行的平台
    if platforms is None:
        platforms = config.enabled_platforms

    total_stats = {'success': 0, 'failed': 0, 'skipped': 0}

    for platform_name in platforms:
        if platform_name not in PLATFORM_CLASSES:
            logger.warning(f"跳过不支持的平台: {platform_name}")
            continue

        try:
            stats = run_platform_task(
                platform_name,
                config,
                headless=headless,
                weekend_mode=weekend_mode,
                weekend_limit=weekend_limit
            )

            total_stats['success'] += stats['success']
            total_stats['failed'] += stats['failed']
            total_stats['skipped'] += stats['skipped']

            # 平台之间等待
            if platform_name != platforms[-1]:
                logger.info("等待 30 秒后开始下一个平台...")
                time.sleep(30)

        except Exception as e:
            logger.error(f"平台 {platform_name} 执行失败: {e}")

    # 输出总统计
    logger.info("=" * 50)
    logger.info("所有平台投递统计:")
    logger.info(f"  总成功: {total_stats['success']}")
    logger.info(f"  总失败: {total_stats['failed']}")
    logger.info(f"  总跳过: {total_stats['skipped']}")
    logger.info("=" * 50)


def main():
    parser = argparse.ArgumentParser(description='多平台自动投递工具')
    parser.add_argument(
        '--platform', '-p',
        choices=['boss', 'liepin', 'all'],
        default='all',
        help='选择平台: boss=Boss直聘, liepin=猎聘网, all=所有启用的平台'
    )
    parser.add_argument('--schedule', '-s', action='store_true', help='启动定时任务模式')
    parser.add_argument('--headless', action='store_true', help='无头模式运行（不显示浏览器窗口）')

    args = parser.parse_args()

    logger.info("=" * 50)
    logger.info("多平台自动投递工具启动")
    logger.info("=" * 50)

    # 确定平台
    if args.platform == 'all':
        platforms = None  # 使用配置文件中启用的平台
    else:
        platforms = [args.platform]

    if args.schedule:
        # 定时任务模式
        config = Config()
        scheduler = JobScheduler(
            config,
            lambda **kwargs: run_apply_task(
                platforms=platforms,
                headless=args.headless,
                **kwargs
            )
        )
        scheduler.setup()
        scheduler.start()
    else:
        # 立即执行一次
        run_apply_task(platforms=platforms, headless=args.headless)


if __name__ == '__main__':
    main()
