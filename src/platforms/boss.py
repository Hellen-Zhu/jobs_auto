import time
import random
from typing import List, Dict, Any, Optional
from playwright.sync_api import Page
from .base import BasePlatform
from ..utils.logger import logger


class BossPlatform(BasePlatform):
    """Boss直聘平台实现"""

    name = "boss"
    base_url = "https://www.zhipin.com"

    # URL 参数映射（与 url_params.yaml 保持一致）
    URL_PARAMS = {
        'city': {
            '全国': '100010000',
            '北京': '101010100',
            '上海': '101020100',
            '广州': '101280100',
            '深圳': '101280600',
            '杭州': '101210100',
            '成都': '101270100',
            '南京': '101190100',
            '武汉': '101200100',
            '西安': '101110100',
            '苏州': '101190400',
        },
        'salary': {
            '20-50K': '406',
            '50K以上': '407',
        },
        'experience': {
            '不限': '101',
            '3-5年': '105',
            '5-10年': '106',
            '10年以上': '107',
        },
        'degree': {
            '本科': '203',
        }
    }

    def __init__(self, page: Page, config: Dict[str, Any]):
        super().__init__(page, config)
        self.search_config = config.get('search', {})
        self.apply_config = config.get('apply', {})
        self.greetings = config.get('greetings', [])

    def get_url_param(self, param_type: str, value: str) -> str:
        """将中文配置值转换为 URL 参数编码"""
        params = self.URL_PARAMS.get(param_type, {})
        return params.get(value, "")

    def build_search_url(self, keyword: str) -> str:
        """构建搜索 URL"""
        base_url = f"{self.base_url}/web/geek/jobs"
        params = [f"query={keyword}"]

        # 城市
        city_code = self.get_url_param('city', self.search_config.get('city', ''))
        if city_code:
            params.append(f"city={city_code}")

        # 薪资
        salary_code = self.get_url_param('salary', self.search_config.get('salary', ''))
        if salary_code:
            params.append(f"salary={salary_code}")

        # 经验
        exp_code = self.get_url_param('experience', self.search_config.get('experience', ''))
        if exp_code:
            params.append(f"experience={exp_code}")

        # 学历
        degree_code = self.get_url_param('degree', self.search_config.get('degree', ''))
        if degree_code:
            params.append(f"degree={degree_code}")

        return f"{base_url}?{'&'.join(params)}"

    def search_jobs(self, keyword: str) -> List[Dict[str, Any]]:
        """搜索职位"""
        url = self.build_search_url(keyword)
        logger.info(f"搜索关键词: {keyword}")
        logger.info(f"访问 URL: {url}")

        self.page.goto(url)
        time.sleep(2)

        if self.check_login_required():
            logger.error("登录状态已失效，请更新 cookie.txt")
            return []

        jobs = self.parse_job_list()
        logger.info(f"找到 {len(jobs)} 个职位")

        return jobs

    def check_login_required(self) -> bool:
        """检查是否需要登录"""
        if 'login' in self.page.url:
            return True
        login_btn = self.page.query_selector('.btn-sign')
        return login_btn is not None

    def parse_job_list(self) -> List[Dict[str, Any]]:
        """解析职位列表"""
        jobs = []

        try:
            self.page.wait_for_selector('.job-card-wrap', timeout=10000)
        except Exception:
            logger.warning("未找到职位列表，可能没有匹配的职位或页面结构已变化")
            return []

        job_cards = self.page.query_selector_all('.job-card-wrap')

        for card in job_cards:
            try:
                job = self.parse_job_card(card)
                if job:
                    jobs.append(job)
            except Exception as e:
                logger.debug(f"解析职位卡片失败: {e}")
                continue

        return jobs

    def parse_job_card(self, card) -> Optional[Dict[str, Any]]:
        """解析单个职位卡片"""
        try:
            job_link = card.query_selector('.job-name')
            if not job_link:
                return None

            href = job_link.get_attribute('href') or ''
            job_id = href.split('/')[-1].replace('.html', '') if href else ''

            job_name = job_link.inner_text().strip() if job_link else ''

            salary_el = card.query_selector('.job-salary')
            salary = salary_el.inner_text().strip() if salary_el else ''

            company_el = card.query_selector('.boss-name')
            company = company_el.inner_text().strip() if company_el else ''

            location_el = card.query_selector('.company-location')
            location = location_el.inner_text().strip() if location_el else ''

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
                'hr_name': '',
                'hr_title': '',
                'url': f"{self.base_url}{href}" if href else '',
                'platform': self.name
            }
        except Exception as e:
            logger.debug(f"解析职位卡片异常: {e}")
            return None

    def apply_job(self, job: Dict[str, Any]) -> bool:
        """投递职位"""
        url = job.get('url', '')
        if not url:
            return False

        self.page.goto(url)
        time.sleep(2)

        # 查找"立即沟通"按钮
        chat_btn = self.page.query_selector('.btn-startchat')
        if not chat_btn:
            logger.debug("未找到'立即沟通'按钮")
            return False

        btn_text = chat_btn.inner_text().strip()
        if '继续沟通' in btn_text:
            logger.debug("已经沟通过，跳过")
            return False

        chat_btn.click()
        time.sleep(2)

        return self.send_greeting(job)

    def send_greeting(self, job: Dict[str, Any] = None) -> bool:
        """发送打招呼消息"""
        if not self.greetings:
            logger.warning("未配置打招呼模板")
            return True

        greeting = random.choice(self.greetings)

        if job:
            greeting = greeting.replace('{position}', job.get('job_name', ''))
            greeting = greeting.replace('{company}', job.get('company', ''))

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

        return True
