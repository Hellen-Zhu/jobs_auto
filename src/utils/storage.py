import json
from pathlib import Path
from datetime import datetime, date
from typing import Dict, List, Any, Optional


class Storage:
    """数据存储管理类（带内存缓存优化）"""

    def __init__(self, data_dir: Optional[str] = None):
        self.data_dir = Path(data_dir) if data_dir else Path(__file__).parent.parent.parent / "data"
        self.data_dir.mkdir(exist_ok=True)

        self.applied_jobs_file = self.data_dir / "applied_jobs.json"
        self.blacklist_file = self.data_dir / "blacklist.json"
        self.hr_records_file = self.data_dir / "hr_records.json"
        self.daily_stats_file = self.data_dir / "daily_stats.json"

        # 内存缓存：只缓存 job_id 集合，用于快速查重
        self._applied_job_ids: Optional[set] = None
        self._blacklist_cache: Optional[Dict[str, List[str]]] = None

    def _load_json(self, file_path: Path) -> Any:
        """加载 JSON 文件"""
        if file_path.exists():
            with open(file_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        return None

    def _save_json(self, file_path: Path, data: Any) -> None:
        """保存 JSON 文件"""
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    # ==================== 已投递职位 ====================

    def _load_applied_job_ids(self) -> set:
        """加载已投递职位 ID 到内存缓存"""
        if self._applied_job_ids is None:
            applied = self._load_json(self.applied_jobs_file) or {}
            self._applied_job_ids = set(applied.keys())
        return self._applied_job_ids

    def get_applied_jobs(self) -> Dict[str, Dict[str, Any]]:
        """获取所有已投递职位详情（用于统计等场景）"""
        return self._load_json(self.applied_jobs_file) or {}

    def is_job_applied(self, job_id: str) -> bool:
        """检查职位是否已投递（使用内存缓存，O(1) 查询）"""
        return job_id in self._load_applied_job_ids()

    def add_applied_job(self, job_id: str, job_info: Dict[str, Any]) -> None:
        """添加已投递职位"""
        applied = self.get_applied_jobs()
        applied[job_id] = {
            **job_info,
            'apply_time': datetime.now().isoformat(),
            'status': 'applied'
        }
        self._save_json(self.applied_jobs_file, applied)
        # 同步更新缓存
        if self._applied_job_ids is not None:
            self._applied_job_ids.add(job_id)

    def update_job_status(self, job_id: str, status: str) -> None:
        """更新职位状态（applied/read/replied）"""
        applied = self.get_applied_jobs()
        if job_id in applied:
            applied[job_id]['status'] = status
            applied[job_id]['update_time'] = datetime.now().isoformat()
            self._save_json(self.applied_jobs_file, applied)

    # ==================== 黑名单 ====================

    def _load_blacklist_cache(self) -> Dict[str, set]:
        """加载黑名单到内存缓存"""
        if self._blacklist_cache is None:
            data = self._load_json(self.blacklist_file) or {'companies': [], 'hr_ids': []}
            self._blacklist_cache = {
                'companies': set(data.get('companies', [])),
                'hr_ids': set(data.get('hr_ids', []))
            }
        return self._blacklist_cache

    def get_blacklist(self) -> Dict[str, List[str]]:
        """获取黑名单（返回列表格式，兼容旧接口）"""
        cache = self._load_blacklist_cache()
        return {
            'companies': list(cache['companies']),
            'hr_ids': list(cache['hr_ids'])
        }

    def is_company_blacklisted(self, company: str) -> bool:
        """检查公司是否在黑名单（使用内存缓存）"""
        return company in self._load_blacklist_cache()['companies']

    def add_company_to_blacklist(self, company: str) -> None:
        """添加公司到黑名单"""
        cache = self._load_blacklist_cache()
        if company not in cache['companies']:
            cache['companies'].add(company)
            # 保存到文件
            self._save_json(self.blacklist_file, self.get_blacklist())

    def is_hr_blacklisted(self, hr_id: str) -> bool:
        """检查 HR 是否在黑名单（使用内存缓存）"""
        return hr_id in self._load_blacklist_cache()['hr_ids']

    def add_hr_to_blacklist(self, hr_id: str) -> None:
        """添加 HR 到黑名单"""
        cache = self._load_blacklist_cache()
        if hr_id not in cache['hr_ids']:
            cache['hr_ids'].add(hr_id)
            self._save_json(self.blacklist_file, self.get_blacklist())

    # ==================== HR 记录 ====================

    def get_hr_records(self) -> Dict[str, Dict[str, Any]]:
        """获取 HR 响应记录"""
        return self._load_json(self.hr_records_file) or {}

    def record_hr_contact(self, hr_id: str, hr_info: Dict[str, Any]) -> None:
        """记录 HR 联系"""
        records = self.get_hr_records()
        if hr_id not in records:
            records[hr_id] = {
                **hr_info,
                'first_contact': datetime.now().isoformat(),
                'contact_count': 0,
                'replied': False
            }
        records[hr_id]['contact_count'] += 1
        records[hr_id]['last_contact'] = datetime.now().isoformat()
        self._save_json(self.hr_records_file, records)

    def mark_hr_replied(self, hr_id: str) -> None:
        """标记 HR 已回复"""
        records = self.get_hr_records()
        if hr_id in records:
            records[hr_id]['replied'] = True
            records[hr_id]['reply_time'] = datetime.now().isoformat()
            self._save_json(self.hr_records_file, records)

    def is_hr_no_reply(self, hr_id: str, days: int = 7) -> bool:
        """检查 HR 是否已读不回（超过指定天数未回复）"""
        records = self.get_hr_records()
        if hr_id not in records:
            return False

        record = records[hr_id]
        if record.get('replied'):
            return False

        last_contact = datetime.fromisoformat(record.get('last_contact', datetime.now().isoformat()))
        return (datetime.now() - last_contact).days >= days

    # ==================== 每日统计 ====================

    def get_daily_stats(self) -> Dict[str, Dict[str, int]]:
        """获取每日统计"""
        return self._load_json(self.daily_stats_file) or {}

    def get_today_apply_count(self) -> int:
        """获取今日投递数量"""
        stats = self.get_daily_stats()
        today = date.today().isoformat()
        return stats.get(today, {}).get('apply_count', 0)

    def increment_today_apply_count(self) -> int:
        """增加今日投递计数，返回当前计数"""
        stats = self.get_daily_stats()
        today = date.today().isoformat()

        if today not in stats:
            stats[today] = {'apply_count': 0}

        stats[today]['apply_count'] += 1
        self._save_json(self.daily_stats_file, stats)

        return stats[today]['apply_count']
