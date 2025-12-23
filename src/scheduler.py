from datetime import datetime
from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.cron import CronTrigger
from .utils.config import Config
from .utils.logger import logger


class JobScheduler:
    """定时任务调度器"""

    def __init__(self, config: Config, job_func):
        """
        初始化调度器

        Args:
            config: 配置对象
            job_func: 要执行的任务函数
        """
        self.config = config
        self.job_func = job_func
        self.scheduler = BlockingScheduler()
        self.schedule_config = config.schedule

    def setup(self) -> None:
        """设置定时任务"""
        if not self.schedule_config.get('enabled', False):
            logger.info("定时任务未启用")
            return

        times = self.schedule_config.get('times', [])
        workdays_only = self.schedule_config.get('workdays_only', False)

        for time_str in times:
            try:
                hour, minute = time_str.split(':')

                if workdays_only:
                    # 仅工作日执行
                    trigger = CronTrigger(
                        hour=int(hour),
                        minute=int(minute),
                        day_of_week='mon-fri'
                    )
                else:
                    # 每天执行
                    trigger = CronTrigger(
                        hour=int(hour),
                        minute=int(minute)
                    )

                self.scheduler.add_job(
                    self._wrapped_job,
                    trigger=trigger,
                    id=f"apply_job_{time_str.replace(':', '')}",
                    name=f"自动投递任务 {time_str}"
                )
                logger.info(f"已添加定时任务: {time_str}" + (" (仅工作日)" if workdays_only else ""))

            except ValueError as e:
                logger.error(f"无效的时间格式 '{time_str}': {e}")

    def _wrapped_job(self) -> None:
        """包装的任务函数，添加日志和异常处理"""
        logger.info("=" * 50)
        logger.info(f"定时任务开始执行 - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        logger.info("=" * 50)

        try:
            # 检查是否是周末，如果是则应用周末限制
            if datetime.now().weekday() >= 5:  # 周六=5, 周日=6
                weekend_limit = self.schedule_config.get('weekend_limit', 10)
                logger.info(f"周末模式，投递上限: {weekend_limit}")
                # 可以在这里修改投递限制
                self.job_func(weekend_mode=True, weekend_limit=weekend_limit)
            else:
                self.job_func()
        except Exception as e:
            logger.error(f"定时任务执行失败: {e}")

        logger.info("定时任务执行完成")
        logger.info("=" * 50)

    def start(self) -> None:
        """启动调度器"""
        if not self.scheduler.get_jobs():
            logger.warning("没有配置任何定时任务")
            return

        logger.info("定时调度器启动，等待执行...")
        logger.info("按 Ctrl+C 停止")

        try:
            self.scheduler.start()
        except (KeyboardInterrupt, SystemExit):
            logger.info("调度器已停止")

    def run_once(self) -> None:
        """立即执行一次（用于测试）"""
        logger.info("手动触发执行...")
        self._wrapped_job()
