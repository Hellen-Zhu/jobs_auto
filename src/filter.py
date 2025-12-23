from typing import List, Dict, Any
from datetime import datetime, timedelta
from .utils.config import Config
from .utils.storage import Storage
from .utils.logger import logger


class JobFilter:
    """职位过滤器"""

    def __init__(self, config: Config, storage: Storage):
        self.config = config
        self.storage = storage
        self.filter_config = config.filter

    def filter_jobs(self, jobs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        过滤职位列表

        Args:
            jobs: 原始职位列表

        Returns:
            过滤后的职位列表
        """
        original_count = len(jobs)
        filtered_jobs = []

        for job in jobs:
            if self._should_apply(job):
                filtered_jobs.append(job)

        logger.info(f"过滤完成：{original_count} -> {len(filtered_jobs)} 个职位")
        return filtered_jobs

    def _should_apply(self, job: Dict[str, Any]) -> bool:
        """
        判断是否应该投递该职位

        Args:
            job: 职位信息

        Returns:
            是否应该投递
        """
        job_id = job.get('job_id', '')
        company = job.get('company', '')
        job_name = job.get('job_name', '')
        description = job.get('description', '')

        # 1. 检查是否已投递
        if self.storage.is_job_applied(job_id):
            logger.debug(f"跳过已投递职位: {job_name} - {company}")
            return False

        # 2. 检查公司是否在黑名单
        if self.storage.is_company_blacklisted(company):
            logger.debug(f"跳过黑名单公司: {company}")
            return False

        # 3. 检查公司名是否包含黑名单关键词
        company_keywords = self.filter_config.get('company_keyword_blacklist', [])
        for keyword in company_keywords:
            if keyword in company:
                logger.debug(f"跳过公司名包含 '{keyword}': {company}")
                return False

        # 4. 检查配置中的公司黑名单
        company_blacklist = self.filter_config.get('company_blacklist', [])
        if company in company_blacklist:
            logger.debug(f"跳过配置黑名单公司: {company}")
            return False

        # 5. JD 必须包含的关键词
        must_include = self.filter_config.get('must_include', [])
        text_to_check = f"{job_name} {description}".lower()
        for keyword in must_include:
            if keyword.lower() not in text_to_check:
                logger.debug(f"跳过不包含关键词 '{keyword}': {job_name}")
                return False

        # 6. JD 必须排除的关键词
        must_exclude = self.filter_config.get('must_exclude', [])
        for keyword in must_exclude:
            if keyword.lower() in text_to_check:
                logger.debug(f"跳过包含排除词 '{keyword}': {job_name}")
                return False

        return True

    def sort_by_priority(self, jobs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        按优先级排序职位

        优先级规则：
        1. HR 未联系过的优先
        2. 新发布的职位优先

        Args:
            jobs: 职位列表

        Returns:
            排序后的职位列表
        """
        def priority_score(job: Dict[str, Any]) -> int:
            score = 0
            hr_name = job.get('hr_name', '')

            # HR 未联系过加分
            hr_records = self.storage.get_hr_records()
            if hr_name not in hr_records:
                score += 10

            # 已读不回的 HR 减分
            # 这里简化处理，实际需要 HR ID
            # if self.storage.is_hr_no_reply(hr_id):
            #     score -= 20

            return score

        return sorted(jobs, key=priority_score, reverse=True)
