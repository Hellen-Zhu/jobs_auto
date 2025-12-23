import time
import random
from typing import List, Dict, Any
from playwright.sync_api import Page
from .utils.config import Config
from .utils.storage import Storage
from .utils.logger import logger


class JobApplier:
    """职位投递类"""

    def __init__(self, page: Page, config: Config, storage: Storage):
        self.page = page
        self.config = config
        self.storage = storage
        self.apply_config = config.apply

    def apply_jobs(self, jobs: List[Dict[str, Any]]) -> Dict[str, int]:
        """
        批量投递职位

        Args:
            jobs: 待投递职位列表

        Returns:
            投递统计 {'success': n, 'failed': n, 'skipped': n}
        """
        stats = {'success': 0, 'failed': 0, 'skipped': 0}

        batch_limit = self.apply_config.get('batch_limit', 20)
        daily_limit = self.apply_config.get('daily_limit', 50)

        # 检查今日投递数量
        today_count = self.storage.get_today_apply_count()
        if today_count >= daily_limit:
            logger.warning(f"今日已达投递上限 ({daily_limit})，停止投递")
            return stats

        remaining_daily = daily_limit - today_count
        remaining_batch = min(batch_limit, remaining_daily)

        logger.info(f"今日已投递 {today_count} 个，本次最多投递 {remaining_batch} 个")

        for i, job in enumerate(jobs[:remaining_batch]):
            job_name = job.get('job_name', '')
            company = job.get('company', '')

            logger.info(f"[{i + 1}/{remaining_batch}] 投递: {job_name} - {company}")

            try:
                success = self._apply_single_job(job)
                if success:
                    stats['success'] += 1
                    self.storage.add_applied_job(job['job_id'], {
                        'job_name': job_name,
                        'company': company,
                        'hr_name': job.get('hr_name', ''),
                        'salary': job.get('salary', ''),
                        'url': job.get('url', '')
                    })
                    self.storage.increment_today_apply_count()
                    logger.info(f"✓ 投递成功: {job_name}")
                else:
                    stats['failed'] += 1
                    logger.warning(f"✗ 投递失败: {job_name}")
            except Exception as e:
                stats['failed'] += 1
                logger.error(f"✗ 投递异常: {job_name} - {e}")

            # 随机延迟
            self._random_delay()

        logger.info(f"投递完成: 成功 {stats['success']}, 失败 {stats['failed']}, 跳过 {stats['skipped']}")
        return stats

    def _apply_single_job(self, job: Dict[str, Any]) -> bool:
        """
        投递单个职位

        Args:
            job: 职位信息

        Returns:
            是否成功
        """
        url = job.get('url', '')
        if not url:
            return False

        # 访问职位详情页
        self.page.goto(url)
        time.sleep(2)

        # 查找"立即沟通"按钮
        chat_btn = self.page.query_selector('.btn-startchat')
        if not chat_btn:
            logger.debug("未找到'立即沟通'按钮")
            return False

        # 检查按钮状态
        btn_text = chat_btn.inner_text().strip()
        if '继续沟通' in btn_text:
            logger.debug("已经沟通过，跳过")
            return False

        # 点击"立即沟通"
        chat_btn.click()
        time.sleep(2)

        # 检查是否弹出聊天窗口或需要发送打招呼
        success = self._send_greeting(job)

        return success

    def _send_greeting(self, job: Dict[str, Any]) -> bool:
        """
        发送打招呼消息

        Args:
            job: 职位信息

        Returns:
            是否成功
        """
        # 随机选择一个打招呼模板
        greetings = self.config.greetings
        if not greetings:
            logger.warning("未配置打招呼模板")
            return True  # 没有模板也算成功（已经点击了沟通）

        greeting = random.choice(greetings)

        # 替换变量
        greeting = greeting.replace('{position}', job.get('job_name', ''))
        greeting = greeting.replace('{company}', job.get('company', ''))

        # 查找输入框
        # Boss 直聘的聊天窗口可能有多种形式
        input_selectors = [
            '.chat-input textarea',
            '.message-input textarea',
            '#chat-input',
            'textarea.input-area'
        ]

        input_box = None
        for selector in input_selectors:
            input_box = self.page.query_selector(selector)
            if input_box:
                break

        if input_box:
            input_box.fill(greeting)
            time.sleep(0.5)

            # 查找发送按钮
            send_selectors = [
                '.btn-send',
                '.send-btn',
                'button:has-text("发送")'
            ]

            for selector in send_selectors:
                send_btn = self.page.query_selector(selector)
                if send_btn:
                    send_btn.click()
                    time.sleep(1)
                    logger.debug(f"已发送打招呼: {greeting[:30]}...")
                    return True

        # 如果没有输入框，可能是直接进入了聊天页面
        # 这种情况也算成功
        return True

    def _random_delay(self) -> None:
        """随机延迟，模拟人工操作"""
        min_delay = self.apply_config.get('interval_min', 30)
        max_delay = self.apply_config.get('interval_max', 60)
        delay = random.uniform(min_delay, max_delay)
        logger.debug(f"等待 {delay:.1f} 秒...")
        time.sleep(delay)
