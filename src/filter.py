import re
from typing import List, Dict, Any, Union, Tuple, Optional
from datetime import datetime, timedelta
from .utils.config import Config
from .utils.storage import Storage
from .utils.logger import logger


class JobFilter:
    """职位过滤器"""

    def __init__(self, config: Union[Config, Dict[str, Any]], storage: Storage):
        self.storage = storage
        # 支持传入 Config 对象或 dict
        if isinstance(config, dict):
            self.filter_config = config.get('filter', {})
        else:
            self.filter_config = config.filter

    def _parse_salary(self, salary_str: str) -> Tuple[Optional[int], Optional[int]]:
        """
        解析薪资字符串，返回 (最低薪资K, 最高薪资K)

        支持格式：
        - "20-50K"
        - "20-50k·14薪"
        - "20K-50K"
        - "15-20k·13薪"
        """
        if not salary_str:
            return None, None

        # 清理字符串，提取数字
        salary_str = salary_str.lower().replace('k', '').replace('·', '-').replace(' ', '')

        # 匹配 "数字-数字" 格式
        match = re.search(r'(\d+)-(\d+)', salary_str)
        if match:
            min_salary = int(match.group(1))
            max_salary = int(match.group(2))
            return min_salary, max_salary

        # 单个数字
        match = re.search(r'(\d+)', salary_str)
        if match:
            salary = int(match.group(1))
            return salary, salary

        return None, None

    def _check_salary_range(self, job: Dict[str, Any]) -> bool:
        """
        检查薪资是否在可接受范围内

        规则：起薪 >= 20K 且 最高薪资 >= 35K
        """
        salary_str = job.get('salary', '')
        min_salary, max_salary = self._parse_salary(salary_str)

        if min_salary is None or max_salary is None:
            # 无法解析薪资，默认通过
            return True

        # 获取配置的薪资要求
        min_start = self.filter_config.get('min_salary_start', 20)  # 起薪最低要求
        min_max = self.filter_config.get('min_salary_max', 35)      # 最高薪资最低要求

        if min_salary < min_start:
            logger.debug(f"薪资过低（起薪 {min_salary}K < {min_start}K）: {job.get('job_name', '')}")
            return False

        if max_salary < min_max:
            logger.debug(f"薪资过低（最高 {max_salary}K < {min_max}K）: {job.get('job_name', '')}")
            return False

        return True

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

        # 5. 检查薪资范围
        if not self._check_salary_range(job):
            return False

        # 6. JD 必须包含的关键词
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
