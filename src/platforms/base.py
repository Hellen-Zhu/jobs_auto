from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from playwright.sync_api import Page, BrowserContext
from ..utils.logger import logger


class BasePlatform(ABC):
    """招聘平台抽象基类"""

    name: str = "base"  # 平台名称
    base_url: str = ""  # 平台基础 URL

    def __init__(self, page: Page, config: Dict[str, Any]):
        self.page = page
        self.config = config

    @abstractmethod
    def build_search_url(self, keyword: str) -> str:
        """构建搜索 URL"""
        pass

    @abstractmethod
    def search_jobs(self, keyword: str) -> List[Dict[str, Any]]:
        """搜索职位"""
        pass

    @abstractmethod
    def parse_job_list(self) -> List[Dict[str, Any]]:
        """解析职位列表"""
        pass

    @abstractmethod
    def parse_job_card(self, card) -> Optional[Dict[str, Any]]:
        """解析单个职位卡片"""
        pass

    @abstractmethod
    def apply_job(self, job: Dict[str, Any]) -> bool:
        """投递职位"""
        pass

    @abstractmethod
    def send_greeting(self, greeting: str) -> bool:
        """发送打招呼消息"""
        pass

    def check_login_required(self) -> bool:
        """检查是否需要登录（子类可覆盖）"""
        if 'login' in self.page.url.lower():
            return True
        return False

    def search_all_keywords(self, keywords: List[str]) -> List[Dict[str, Any]]:
        """搜索所有关键词（通用实现）"""
        import time
        all_jobs = []
        seen_ids = set()

        for keyword in keywords:
            jobs = self.search_jobs(keyword)

            for job in jobs:
                if job['job_id'] not in seen_ids:
                    seen_ids.add(job['job_id'])
                    all_jobs.append(job)

            time.sleep(2)

        logger.info(f"[{self.name}] 所有关键词搜索完成，共找到 {len(all_jobs)} 个不重复职位")
        return all_jobs

    def get_platform_storage_prefix(self) -> str:
        """获取平台存储前缀"""
        return self.name
