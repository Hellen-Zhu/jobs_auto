import yaml
from pathlib import Path
from typing import Dict, List, Any, Optional


class Config:
    """配置管理类"""

    def __init__(self, config_path: Optional[str] = None):
        self.base_dir = Path(__file__).parent.parent.parent
        self.config_path = Path(config_path) if config_path else self.base_dir / "config.yaml"
        self.url_params_path = self.base_dir / "url_params.yaml"
        self.cookie_path = self.base_dir / "cookie.txt"

        self._config: Dict[str, Any] = {}
        self._url_params: Dict[str, Dict[str, str]] = {}
        self._cookie: str = ""

        self._load()

    def _load(self) -> None:
        """加载所有配置"""
        # 加载主配置
        if self.config_path.exists():
            with open(self.config_path, 'r', encoding='utf-8') as f:
                self._config = yaml.safe_load(f) or {}

        # 加载 URL 参数映射
        if self.url_params_path.exists():
            with open(self.url_params_path, 'r', encoding='utf-8') as f:
                self._url_params = yaml.safe_load(f) or {}

        # 加载 Cookie
        if self.cookie_path.exists():
            with open(self.cookie_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
                # 跳过注释行
                cookie_lines = [line.strip() for line in lines if line.strip() and not line.strip().startswith('#')]
                self._cookie = cookie_lines[0] if cookie_lines else ""

    @property
    def cookie(self) -> str:
        """获取 Cookie"""
        return self._cookie

    @property
    def search(self) -> Dict[str, Any]:
        """获取搜索配置"""
        return self._config.get('search', {})

    @property
    def filter(self) -> Dict[str, Any]:
        """获取过滤配置"""
        return self._config.get('filter', {})

    @property
    def apply(self) -> Dict[str, Any]:
        """获取投递配置"""
        return self._config.get('apply', {})

    @property
    def greetings(self) -> List[str]:
        """获取打招呼模板列表"""
        return self._config.get('greetings', [])

    @property
    def schedule(self) -> Dict[str, Any]:
        """获取定时任务配置"""
        return self._config.get('schedule', {})

    def get_url_param(self, param_type: str, value: str) -> str:
        """
        将中文配置值转换为 URL 参数编码

        Args:
            param_type: 参数类型（city, salary, experience, degree）
            value: 中文配置值

        Returns:
            URL 参数编码，如果找不到则返回空字符串
        """
        params = self._url_params.get(param_type, {})
        return params.get(value, "")

    def build_search_url(self, keyword: str) -> str:
        """
        根据配置构建搜索 URL

        Args:
            keyword: 搜索关键词

        Returns:
            完整的搜索 URL
        """
        base_url = "https://www.zhipin.com/web/geek/jobs"
        params = [f"query={keyword}"]

        search = self.search

        # 城市
        city_code = self.get_url_param('city', search.get('city', ''))
        if city_code:
            params.append(f"city={city_code}")

        # 薪资
        salary_code = self.get_url_param('salary', search.get('salary', ''))
        if salary_code:
            params.append(f"salary={salary_code}")

        # 经验
        exp_code = self.get_url_param('experience', search.get('experience', ''))
        if exp_code:
            params.append(f"experience={exp_code}")

        # 学历
        degree_code = self.get_url_param('degree', search.get('degree', ''))
        if degree_code:
            params.append(f"degree={degree_code}")

        return f"{base_url}?{'&'.join(params)}"
