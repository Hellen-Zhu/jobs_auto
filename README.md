# Boss直聘自动投递工具

基于 Python + Playwright 的 Boss直聘自动投递工具，支持定时任务、智能筛选、数据记录等功能。

## 功能特性

- **多关键词搜索**：支持配置多个搜索关键词
- **URL 参数筛选**：通过 URL 参数筛选城市、薪资、经验、学历
- **智能过滤**：黑名单公司/HR、关键词过滤、去重
- **自动投递**：自动点击沟通并发送打招呼语
- **定时任务**：支持配置多个定时执行时间点
- **数据记录**：记录已投递职位，避免重复投递

## 安装

```bash
# 创建虚拟环境
python3 -m venv venv
source venv/bin/activate

# 安装依赖
pip install -r requirements.txt

# 安装 Playwright 浏览器
playwright install chromium
```

## 配置

1. 复制并编辑配置文件 `config.yaml`
2. 将 Boss直聘 Cookie 保存到 `cookie.txt`

### 获取 Cookie

1. 登录 Boss直聘网页版
2. 打开浏览器开发者工具 (F12)
3. 在 Network 面板中找到任意请求
4. 复制 Request Headers 中的 Cookie 值
5. 保存到 `cookie.txt` 文件

## 使用

```bash
# 立即执行一次投递
python -m src.main

# 启动定时任务模式
python -m src.main --schedule

# 无头模式运行
python -m src.main --headless
```

## 配置说明

```yaml
search:
  keywords:          # 搜索关键词列表
    - QA
    - 测试开发
  city: 上海         # 城市
  salary: 20-50K     # 薪资范围
  experience: 5-10年 # 工作经验
  degree: 本科       # 学历要求

filter:
  blacklist_companies:  # 黑名单公司
    - 某某外包公司
  blacklist_keywords:   # 职位名称黑名单关键词
    - 外包

apply:
  daily_limit: 20       # 每日投递上限
  greeting: "您好..."   # 打招呼语

schedule:
  enabled: true
  times:               # 定时执行时间点
    - "09:00"
    - "14:00"
```

## 目录结构

```
├── config.yaml        # 用户配置
├── url_params.yaml    # URL 参数映射
├── cookie.txt         # Cookie 文件（不纳入版本控制）
├── data/              # 数据存储目录
├── logs/              # 日志目录
└── src/
    ├── main.py        # 主入口
    ├── browser.py     # 浏览器管理
    ├── search.py      # 职位搜索
    ├── filter.py      # 职位过滤
    ├── apply.py       # 自动投递
    ├── scheduler.py   # 定时任务
    └── utils/
        ├── config.py  # 配置加载
        ├── logger.py  # 日志工具
        └── storage.py # 数据存储
```

## 注意事项

- 请合理使用，避免频繁操作导致账号异常
- Cookie 有效期有限，失效后需重新获取
- 建议在非高峰时段运行
