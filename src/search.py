import time
from typing import List, Dict, Any, Optional
from playwright.sync_api import Page
from .utils.config import Config
from .utils.logger import logger


class JobSearcher:
    """职位搜索类"""

    def __init__(self, page: Page, config: Config):
        self.page = page
        self.config = config

    def search_jobs(self, keyword: str) -> List[Dict[str, Any]]:
        """
        搜索职位

        Args:
            keyword: 搜索关键词

        Returns:
            职位列表
        """
        url = self.config.build_search_url(keyword)
        logger.info(f"搜索关键词: {keyword}")
        logger.info(f"访问 URL: {url}")

        self.page.goto(url)
        time.sleep(2)  # 等待页面加载

        # 检查是否需要登录
        if self._check_login_required():
            logger.error("登录状态已失效，请更新 cookie.txt")
            return []

        jobs = self._parse_job_list()
        logger.info(f"找到 {len(jobs)} 个职位")

        return jobs

    def _check_login_required(self) -> bool:
        """检查是否需要登录"""
        # 检查是否跳转到登录页面
        if 'login' in self.page.url:
            return True

        # 检查页面是否有登录提示
        login_btn = self.page.query_selector('.btn-sign')
        return login_btn is not None

    def _parse_job_list(self) -> List[Dict[str, Any]]:
        """解析职位列表"""
        jobs = []

        # 等待职位列表加载
        try:
            self.page.wait_for_selector('.job-card-wrap', timeout=10000)
        except Exception:
            logger.warning("未找到职位列表，可能没有匹配的职位或页面结构已变化")
            # 保存截图用于调试
            from pathlib import Path
            screenshot_path = Path(__file__).parent.parent / "logs" / "debug_screenshot.png"
            self.page.screenshot(path=str(screenshot_path))
            logger.info(f"已保存调试截图: {screenshot_path}")
            # 保存页面 HTML
            html_path = Path(__file__).parent.parent / "logs" / "debug_page.html"
            html_path.write_text(self.page.content(), encoding='utf-8')
            logger.info(f"已保存页面 HTML: {html_path}")
            return []

        job_cards = self.page.query_selector_all('.job-card-wrap')

        for card in job_cards:
            try:
                job = self._parse_job_card(card)
                if job:
                    jobs.append(job)
            except Exception as e:
                logger.debug(f"解析职位卡片失败: {e}")
                continue

        return jobs

    def _parse_job_card(self, card) -> Optional[Dict[str, Any]]:
        """解析单个职位卡片"""
        try:
            # 职位链接和 ID
            job_link = card.query_selector('.job-name')
            if not job_link:
                return None

            href = job_link.get_attribute('href') or ''
            # 从 href 中提取 job_id，格式如：/job_detail/xxx.html
            job_id = href.split('/')[-1].replace('.html', '') if href else ''

            # 职位名称
            job_name = job_link.inner_text().strip() if job_link else ''

            # 薪资
            salary_el = card.query_selector('.job-salary')
            salary = salary_el.inner_text().strip() if salary_el else ''

            # 公司名称
            company_el = card.query_selector('.boss-name')
            company = company_el.inner_text().strip() if company_el else ''

            # 公司位置
            location_el = card.query_selector('.company-location')
            location = location_el.inner_text().strip() if location_el else ''

            # 职位标签（经验、学历等）
            tags = []
            tag_elements = card.query_selector_all('.tag-list li')
            tags = [t.inner_text().strip() for t in tag_elements]

            return {
                'job_id': job_id,
                'job_name': job_name,
                'salary': salary,
                'company': company,
                'location': location,
                'tags': tags,
                'hr_name': '',  # 列表页没有 HR 名字
                'hr_title': '',
                'url': f"https://www.zhipin.com{href}" if href else ''
            }
        except Exception as e:
            logger.debug(f"解析职位卡片异常: {e}")
            return None

    def search_all_keywords(self) -> List[Dict[str, Any]]:
        """
        搜索所有关键词

        Returns:
            所有职位列表（已去重）
        """
        keywords = self.config.search.get('keywords', [])
        all_jobs = []
        seen_ids = set()

        for keyword in keywords:
            jobs = self.search_jobs(keyword)

            for job in jobs:
                if job['job_id'] not in seen_ids:
                    seen_ids.add(job['job_id'])
                    all_jobs.append(job)

            # 关键词之间等待，避免请求过快
            time.sleep(2)

        logger.info(f"所有关键词搜索完成，共找到 {len(all_jobs)} 个不重复职位")
        return all_jobs

    def get_next_page(self) -> bool:
        """
        翻到下一页

        Returns:
            是否成功翻页
        """
        next_btn = self.page.query_selector('.ui-icon-arrow-right')
        if next_btn and not next_btn.is_disabled():
            next_btn.click()
            time.sleep(2)
            return True
        return False
