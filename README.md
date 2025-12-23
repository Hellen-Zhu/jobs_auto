# 多平台自动投递工具

基于 Python + Playwright 的多平台自动投递工具，支持 Boss直聘 和 猎聘网，具备定时任务、智能筛选、数据记录等功能。

## 支持平台

- **Boss直聘** (zhipin.com)
- **猎聘网** (liepin.com)

## 功能特性

- **多平台支持**：一个工具同时管理多个招聘平台
- **多关键词搜索**：支持配置多个搜索关键词
- **URL 参数筛选**：通过 URL 参数筛选城市、薪资、经验、学历
- **智能过滤**：黑名单公司/HR、关键词过滤、去重
- **自动投递**：自动点击沟通并发送打招呼语
- **定时任务**：支持配置多个定时执行时间点
- **数据记录**：记录已投递职位，避免重复投递（按平台分离存储）

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

### 1. 编辑配置文件

编辑 `config.yaml`，配置启用的平台和各平台的搜索条件：

```yaml
# 启用的平台
platforms:
  - boss
  - liepin

# Boss直聘配置
boss:
  search:
    keywords: ["QA", "测试开发"]
    city: "上海"
    salary: "20-50K"
    # ...

# 猎聘网配置
liepin:
  search:
    keywords: ["QA", "测试开发"]
    city: "上海"
    salary: "30-50K"
    # ...
```

### 2. 配置 Cookie

#### Boss直聘
1. 登录 Boss直聘网页版
2. 打开浏览器开发者工具 (F12)
3. 复制 Cookie 值到 `cookie.txt`

#### 猎聘网
1. 登录猎聘网网页版
2. 打开浏览器开发者工具 (F12)
3. 复制 Cookie 值到 `cookie_liepin.txt`

## 使用

```bash
# 运行所有启用的平台
python -m src.main

# 只运行 Boss直聘
python -m src.main --platform boss

# 只运行猎聘网
python -m src.main --platform liepin

# 启动定时任务模式
python -m src.main --schedule

# 无头模式运行（不显示浏览器）
python -m src.main --headless

# 组合使用
python -m src.main --platform boss --headless --schedule
```

## 目录结构

```
├── config.yaml           # 多平台配置文件
├── cookie.txt            # Boss直聘 Cookie
├── cookie_liepin.txt     # 猎聘网 Cookie
├── data/                 # 数据存储目录
│   ├── applied_jobs.json       # Boss 已投递记录
│   ├── liepin_applied_jobs.json # 猎聘 已投递记录
│   └── ...
├── logs/                 # 日志目录
└── src/
    ├── main.py           # 主入口
    ├── browser.py        # 浏览器管理
    ├── filter.py         # 职位过滤
    ├── scheduler.py      # 定时任务
    ├── platforms/        # 平台实现
    │   ├── base.py       # 抽象基类
    │   ├── boss.py       # Boss直聘
    │   └── liepin.py     # 猎聘网
    └── utils/
        ├── config.py     # 配置加载
        ├── logger.py     # 日志工具
        └── storage.py    # 数据存储
```

## 配置说明

```yaml
# 启用的平台列表
platforms:
  - boss      # Boss直聘
  - liepin    # 猎聘网

# 各平台独立配置
boss/liepin:
  search:
    keywords:          # 搜索关键词列表
    city: 上海         # 城市
    salary: 20-50K     # 薪资范围
    experience: 5-10年 # 工作经验
    degree: 本科       # 学历要求

  filter:
    must_include: []        # JD 必须包含的关键词
    must_exclude: []        # JD 必须排除的关键词
    company_blacklist: []   # 黑名单公司
    company_keyword_blacklist: []  # 公司名黑名单关键词

  apply:
    daily_limit: 50    # 每日投递上限
    batch_limit: 20    # 单次投递上限
    interval_min: 30   # 投递间隔最小秒数
    interval_max: 60   # 投递间隔最大秒数

# 通用配置
greetings:             # 打招呼模板（所有平台共用）
  - "您好，..."

schedule:              # 定时任务配置
  enabled: true
  times:
    - "09:00"
    - "14:00"
```

## 注意事项

- 请合理使用，避免频繁操作导致账号异常
- Cookie 有效期有限，失效后需重新获取
- 建议在非高峰时段运行
- 猎聘网的页面结构可能需要根据实际情况调整选择器
