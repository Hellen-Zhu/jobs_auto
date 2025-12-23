from playwright.sync_api import sync_playwright, Browser, BrowserContext, Page
from typing import Optional
from .utils.config import Config
from .utils.logger import logger


class BrowserManager:
    """浏览器管理类"""

    def __init__(self, config: Config):
        self.config = config
        self.playwright = None
        self.browser: Optional[Browser] = None
        self.context: Optional[BrowserContext] = None
        self.page: Optional[Page] = None

    def start(self, headless: bool = False) -> Page:
        """
        启动浏览器

        Args:
            headless: 是否无头模式

        Returns:
            Page 对象
        """
        logger.info("启动浏览器...")

        self.playwright = sync_playwright().start()
        self.browser = self.playwright.chromium.launch(
            headless=headless,
            args=['--disable-blink-features=AutomationControlled']
        )

        # 创建上下文并设置 Cookie
        self.context = self.browser.new_context(
            viewport={'width': 1920, 'height': 1080},
            user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        )

        # 设置 Cookie
        self._set_cookies()

        self.page = self.context.new_page()

        # 设置默认超时
        self.page.set_default_timeout(30000)

        logger.info("浏览器启动成功")
        return self.page

    def _set_cookies(self) -> None:
        """设置 Cookie"""
        cookie_str = self.config.cookie
        if not cookie_str:
            logger.warning("未找到 Cookie，请确保 cookie.txt 文件中有有效的 Cookie")
            return

        cookies = []
        for item in cookie_str.split(';'):
            item = item.strip()
            if '=' in item:
                name, value = item.split('=', 1)
                cookies.append({
                    'name': name.strip(),
                    'value': value.strip(),
                    'domain': '.zhipin.com',
                    'path': '/'
                })

        if cookies:
            self.context.add_cookies(cookies)
            logger.info(f"已设置 {len(cookies)} 个 Cookie")

    def close(self) -> None:
        """关闭浏览器"""
        if self.page:
            self.page.close()
        if self.context:
            self.context.close()
        if self.browser:
            self.browser.close()
        if self.playwright:
            self.playwright.stop()

        logger.info("浏览器已关闭")

    def __enter__(self):
        self.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
