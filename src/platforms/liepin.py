import time
import random
from typing import List, Dict, Any, Optional
from playwright.sync_api import Page
from .base import BasePlatform
from ..utils.logger import logger


class LiepinPlatform(BasePlatform):
    """猎聘网平台实现"""

    name = "liepin"
    base_url = "https://www.liepin.com"

    # URL 参数映射（猎聘城市代码）
    URL_PARAMS = {
        'city': {
            '上海': '020',
            '北京': '010',
            '深圳': '050090',
            '广州': '050020',
            '杭州': '070020',
            '成都': '280020',
            '南京': '060020',
            '武汉': '170020',
            '西安': '200020',
            '苏州': '060080',
        },
        # 猎聘薪资是年薪（万），使用 salaryCode 参数
        # 1=10万以下, 2=10-20万, 3=20-30万, 4=21-30万, 5=31-50万, 6=51-70万, 7=71-100万, 8=100万以上
        'salary': {
            '10万以下': '1',
            '10-20万': '2',
            '20-30万': '3',
            '21-30万': '4',
            '31-50万': '5',
            '51-70万': '6',
            '71-100万': '7',
            '100万以上': '8',
        },
        'experience': {
            '不限': '',
            '1年以内': '0$1',
            '1-3年': '1$3',
            '3-5年': '3$5',
            '5-10年': '5$10',
            '10年以上': '10$',
        },
        'degree': {
            '不限': '',
            '大专': '30',
            '本科': '40',
            '硕士': '50',
            '博士': '60',
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
        import urllib.parse
        base_url = f"{self.base_url}/zhaopin/"
        params = [f"key={urllib.parse.quote(keyword)}"]

        # 城市
        city_code = self.get_url_param('city', self.search_config.get('city', ''))
        if city_code:
            params.append(f"dqs={city_code}")

        # 薪资（猎聘使用 salaryCode，年薪）
        salary_code = self.get_url_param('salary', self.search_config.get('salary', ''))
        if salary_code:
            params.append(f"salaryCode={salary_code}")

        # 经验
        exp_code = self.get_url_param('experience', self.search_config.get('experience', ''))
        if exp_code:
            params.append(f"workYearCode={exp_code}")

        # 学历
        degree_code = self.get_url_param('degree', self.search_config.get('degree', ''))
        if degree_code:
            params.append(f"eduLevel={degree_code}")

        return f"{base_url}?{'&'.join(params)}"

    def search_jobs(self, keyword: str) -> List[Dict[str, Any]]:
        """搜索职位"""
        url = self.build_search_url(keyword)
        logger.info(f"[猎聘] 搜索关键词: {keyword}")
        logger.info(f"[猎聘] 访问 URL: {url}")

        try:
            # 使用 domcontentloaded 而不是 load，避免等待所有资源
            self.page.goto(url, wait_until='domcontentloaded', timeout=30000)
        except Exception as e:
            logger.warning(f"[猎聘] 页面加载异常: {e}")
            # 等待一下再检查页面状态
            time.sleep(2)

        time.sleep(3)  # 猎聘页面加载较慢

        # 检查当前 URL
        current_url = self.page.url
        logger.debug(f"[猎聘] 当前 URL: {current_url}")

        if self.check_login_required():
            logger.error("[猎聘] 登录状态已失效，请更新 cookie_liepin.txt")
            return []

        jobs = self.parse_job_list()
        logger.info(f"[猎聘] 找到 {len(jobs)} 个职位")

        return jobs

    def check_login_required(self) -> bool:
        """检查是否需要登录"""
        if 'login' in self.page.url or 'passport' in self.page.url:
            return True
        # 检查是否有登录按钮
        login_btn = self.page.query_selector('.login-btn, .btn-login, [data-nick="登录"]')
        return login_btn is not None

    def parse_job_list(self) -> List[Dict[str, Any]]:
        """解析职位列表"""
        jobs = []

        # 猎聘的职位卡片选择器（2024年新版页面结构）
        job_card_selectors = [
            '.job-card-pc-container',
            '.job-list-box .job-card',
            '[class*="job-card"]',
            '.job-detail-box',
            'div[style*="job"]',
        ]

        job_cards = []
        for selector in job_card_selectors:
            try:
                self.page.wait_for_selector(selector, timeout=10000)
                job_cards = self.page.query_selector_all(selector)
                if job_cards:
                    logger.info(f"[猎聘] 使用选择器: {selector}, 找到 {len(job_cards)} 个卡片")
                    break
            except Exception:
                continue

        if not job_cards:
            logger.warning("[猎聘] 未找到职位列表，尝试直接解析页面链接...")
            # 保存截图和HTML用于调试
            from pathlib import Path
            screenshot_path = Path(__file__).parent.parent.parent / "logs" / "liepin_debug.png"
            html_path = Path(__file__).parent.parent.parent / "logs" / "liepin_debug.html"
            self.page.screenshot(path=str(screenshot_path))
            html_path.write_text(self.page.content(), encoding='utf-8')
            logger.info(f"[猎聘] 已保存调试截图: {screenshot_path}")
            logger.info(f"[猎聘] 已保存页面HTML: {html_path}")

            # 尝试直接找所有职位链接
            jobs = self._parse_job_links()
            return jobs

        for card in job_cards:
            try:
                job = self.parse_job_card(card)
                if job:
                    jobs.append(job)
            except Exception as e:
                logger.debug(f"[猎聘] 解析职位卡片失败: {e}")
                continue

        return jobs

    def _parse_job_links(self) -> List[Dict[str, Any]]:
        """备用方法：直接解析页面中的职位链接"""
        jobs = []

        # 查找所有包含 /job/ 的链接
        links = self.page.query_selector_all('a[href*="/job/"]')
        seen_ids = set()

        for link in links:
            try:
                href = link.get_attribute('href') or ''
                if not href or '/job/' not in href:
                    continue

                # 提取 job_id
                job_id = href.split('/job/')[-1].split('.')[0].split('?')[0]
                if not job_id or job_id in seen_ids:
                    continue
                seen_ids.add(job_id)

                job_name = link.inner_text().strip()
                if not job_name or len(job_name) < 2:
                    continue

                # 确保 URL 完整
                if not href.startswith('http'):
                    href = f"{self.base_url}{href}"

                jobs.append({
                    'job_id': job_id,
                    'job_name': job_name,
                    'salary': '',
                    'company': '',
                    'location': '',
                    'tags': [],
                    'hr_name': '',
                    'hr_title': '',
                    'url': href,
                    'platform': self.name
                })
            except Exception as e:
                logger.debug(f"[猎聘] 解析链接失败: {e}")
                continue

        logger.info(f"[猎聘] 通过链接解析找到 {len(jobs)} 个职位")
        return jobs

    def parse_job_card(self, card) -> Optional[Dict[str, Any]]:
        """解析单个职位卡片"""
        try:
            # 职位链接 - 猎聘新版页面结构
            job_link = (
                card.query_selector('a.ellipsis-1') or
                card.query_selector('.job-title-box a') or
                card.query_selector('a[href*="/job/"]')
            )

            if not job_link:
                return None

            href = job_link.get_attribute('href') or ''
            # 从 href 中提取 job_id
            job_id = ''
            if '/job/' in href:
                job_id = href.split('/job/')[-1].split('.')[0].split('?')[0]

            # 只获取职位标题文本
            job_name = job_link.get_attribute('title') or job_link.inner_text().strip()
            # 清理换行和多余空格
            job_name = ' '.join(job_name.split())

            if not job_id or not job_name:
                return None

            # 薪资 - 猎聘通常用橙色显示
            salary_el = card.query_selector('.job-salary, .salary, span[class*="salary"]')
            salary = salary_el.inner_text().strip() if salary_el else ''

            # 公司名称
            company_el = card.query_selector('.company-name a, .company-name, a[href*="/company/"]')
            company = company_el.inner_text().strip() if company_el else ''
            company = ' '.join(company.split())  # 清理换行

            # 公司位置
            location_el = card.query_selector('.job-dq, .area, [class*="city"]')
            location = location_el.inner_text().strip() if location_el else ''

            # 确保 URL 完整
            if href and not href.startswith('http'):
                href = f"{self.base_url}{href}"

            return {
                'job_id': job_id,
                'job_name': job_name,
                'salary': salary,
                'company': company,
                'location': location,
                'tags': [],
                'hr_name': '',
                'hr_title': '',
                'url': href,
                'platform': self.name
            }
        except Exception as e:
            logger.debug(f"[猎聘] 解析职位卡片异常: {e}")
            return None

    def apply_job(self, job: Dict[str, Any]) -> bool:
        """投递职位"""
        url = job.get('url', '')
        if not url:
            return False

        try:
            self.page.goto(url, wait_until='domcontentloaded', timeout=30000)
        except Exception as e:
            logger.warning(f"[猎聘] 页面加载异常: {e}")

        time.sleep(3)

        from pathlib import Path

        # 猎聘职位详情页的"聊一聊"按钮选择器
        # 优先找大的橙色按钮，在页面右上角
        apply_btn_selectors = [
            'button:has-text("聊一聊")',
            'a:has-text("聊一聊")',
            '.job-apply-btn',
            '.btn-chat',
            'button:has-text("立即沟通")',
            'button:has-text("投递简历")',
        ]

        apply_btn = None
        for selector in apply_btn_selectors:
            try:
                btns = self.page.query_selector_all(selector)
                for btn in btns:
                    if btn.is_visible():
                        btn_text = btn.inner_text().strip()
                        # 确保是真正的按钮，不是包含太多文字的容器
                        if len(btn_text) < 20 and ('聊' in btn_text or '沟通' in btn_text or '投递' in btn_text):
                            apply_btn = btn
                            logger.info(f"[猎聘] 找到按钮: '{btn_text}'")
                            break
                if apply_btn:
                    break
            except Exception:
                continue

        if not apply_btn:
            # 保存截图调试
            screenshot_path = Path(__file__).parent.parent.parent / "logs" / "liepin_apply_debug.png"
            self.page.screenshot(path=str(screenshot_path))
            logger.warning(f"[猎聘] 未找到投递按钮，已保存截图: {screenshot_path}")
            return False

        try:
            btn_text = apply_btn.inner_text().strip()

            if '已投递' in btn_text or '已沟通' in btn_text or '已申请' in btn_text:
                logger.debug("[猎聘] 已投递过，跳过")
                return False

            # 保存点击前截图
            screenshot_path = Path(__file__).parent.parent.parent / "logs" / "liepin_before_click.png"
            self.page.screenshot(path=str(screenshot_path))

            apply_btn.click()
            time.sleep(3)

            # 保存点击后截图
            screenshot_path = Path(__file__).parent.parent.parent / "logs" / "liepin_after_click.png"
            self.page.screenshot(path=str(screenshot_path))
            logger.info(f"[猎聘] 已保存点击后截图")

            # 检查是否进入聊天页面或有弹窗
            # 猎聘点击聊一聊后可能直接进入聊天界面
            current_url = self.page.url
            if 'im.' in current_url or 'chat' in current_url:
                logger.info("[猎聘] 已进入聊天页面")
                # 发送打招呼消息
                return self.send_greeting(job)

            # 检查是否有确认弹窗
            confirm_btn = self.page.query_selector('button:has-text("确认"), button:has-text("确定")')
            if confirm_btn and confirm_btn.is_visible():
                logger.info("[猎聘] 找到确认按钮，点击...")
                confirm_btn.click()
                time.sleep(2)

            return True
        except Exception as e:
            logger.error(f"[猎聘] 点击投递按钮失败: {e}")
            return False

    def send_greeting(self, job: Dict[str, Any] = None) -> bool:
        """发送打招呼消息"""
        if not self.greetings:
            logger.warning("[猎聘] 未配置打招呼模板")
            return True

        greeting = random.choice(self.greetings)

        if job:
            greeting = greeting.replace('{position}', job.get('job_name', ''))
            greeting = greeting.replace('{company}', job.get('company', ''))

        # 猎聘的聊天输入框选择器
        input_selectors = [
            '.chat-input textarea',
            '.message-input textarea',
            '.im-input textarea',
            'textarea[placeholder*="输入"]'
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
                '.send-btn',
                '.btn-send',
                'button:has-text("发送")'
            ]

            for selector in send_selectors:
                send_btn = self.page.query_selector(selector)
                if send_btn:
                    send_btn.click()
                    time.sleep(1)
                    logger.debug(f"[猎聘] 已发送打招呼: {greeting[:30]}...")
                    return True

        return True
