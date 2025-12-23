import yaml
from pathlib import Path
from typing import Dict, List, Any, Optional


class Config:
    """多平台配置管理类"""

    def __init__(self, config_path: Optional[str] = None):
        self.base_dir = Path(__file__).parent.parent.parent
        self.config_path = Path(config_path) if config_path else self.base_dir / "config.yaml"

        self._config: Dict[str, Any] = {}
        self._load()

    def _load(self) -> None:
        """加载配置文件"""
        if self.config_path.exists():
            with open(self.config_path, 'r', encoding='utf-8') as f:
                self._config = yaml.safe_load(f) or {}

    @property
    def enabled_platforms(self) -> List[str]:
        """获取启用的平台列表"""
        return self._config.get('platforms', ['boss'])

    def get_platform_config(self, platform: str) -> Dict[str, Any]:
        """获取指定平台的完整配置"""
        platform_config = self._config.get(platform, {})
        # 合并通用配置
        platform_config['greetings'] = self.greetings
        return platform_config

    def get_cookie(self, platform: str) -> str:
        """获取指定平台的 Cookie"""
        if platform == 'boss':
            cookie_file = self.base_dir / "cookie.txt"
        else:
            cookie_file = self.base_dir / f"cookie_{platform}.txt"

        if cookie_file.exists():
            with open(cookie_file, 'r', encoding='utf-8') as f:
                lines = f.readlines()
                cookie_lines = [line.strip() for line in lines
                               if line.strip() and not line.strip().startswith('#')]
                return cookie_lines[0] if cookie_lines else ""
        return ""

    @property
    def greetings(self) -> List[str]:
        """获取打招呼模板列表"""
        return self._config.get('greetings', [])

    @property
    def schedule(self) -> Dict[str, Any]:
        """获取定时任务配置"""
        return self._config.get('schedule', {})

    # 兼容旧接口
    @property
    def search(self) -> Dict[str, Any]:
        """获取 Boss 搜索配置（兼容旧代码）"""
        return self._config.get('boss', {}).get('search', {})

    @property
    def filter(self) -> Dict[str, Any]:
        """获取 Boss 过滤配置（兼容旧代码）"""
        return self._config.get('boss', {}).get('filter', {})

    @property
    def apply(self) -> Dict[str, Any]:
        """获取 Boss 投递配置（兼容旧代码）"""
        return self._config.get('boss', {}).get('apply', {})

    @property
    def cookie(self) -> str:
        """获取 Boss Cookie（兼容旧代码）"""
        return self.get_cookie('boss')

    def build_search_url(self, keyword: str) -> str:
        """构建 Boss 搜索 URL（兼容旧代码）"""
        from ..platforms.boss import BossPlatform
        base_url = "https://www.zhipin.com/web/geek/jobs"
        params = [f"query={keyword}"]

        search = self.search
        url_params = BossPlatform.URL_PARAMS

        city_code = url_params['city'].get(search.get('city', ''), '')
        if city_code:
            params.append(f"city={city_code}")

        salary_code = url_params['salary'].get(search.get('salary', ''), '')
        if salary_code:
            params.append(f"salary={salary_code}")

        exp_code = url_params['experience'].get(search.get('experience', ''), '')
        if exp_code:
            params.append(f"experience={exp_code}")

        degree_code = url_params['degree'].get(search.get('degree', ''), '')
        if degree_code:
            params.append(f"degree={degree_code}")

        return f"{base_url}?{'&'.join(params)}"
