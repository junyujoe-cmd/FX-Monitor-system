# 工作日志

## 2026-05-21 会话总结

### 已完成功能

#### 数据源
- **CFETS (中国外汇交易中心)**: `ak.fx_spot_quote()` — 银行间市场真实买卖报价（点差~4bp），替代了原来的 `open.er-api.com`
- **中国银行 (BOC)**: BeautifulSoup 爬取 `boc.cn` 官网牌价（每日更新，有 30 天历史数据可回溯）
- **招商银行 (CMB)**: JSON API `fx.cmbchina.com/api/v1/fx/rate`（实时牌价，无历史 API）
- **宁波银行、杭州银行**: 已移除（无公开牌价页面，尝试了所有 URL 均不可用）

#### 界面
- **报价栏**: 5 行 → 改为 3 行（CFETS + 中国银行 + 招商银行），每个卡片显示买价(绿)/卖价(红)/市场成本(灰)/银行成本(黄虚线)
- **录入表单**: 简化，移除旧的对比表格（已移至报价栏）
- **历史图表**: 4 条线 + 银行选择器 + 日期选择器 + 鼠标悬浮提示框
- **系统托盘**: 关窗口最小化到菜单栏，后台继续采集数据，首次提示

#### 打包
- `dist/实时外汇监控系统.app` — macOS 应用包，双击直接运行
- 已复制到 `/Applications/`

#### 数据持久化
- `bank_fetcher.py`: 新增 BOC 历史数据回填功能（`fetch_boc_history(days=30)`）
- `database.py`: 新增 `save_boc_history`, `has_boc_history`, `get_chart_data_by_date`
- 启动时自动回填中行 30 天历史数据，完成后触发图表刷新

### 待办
1. **Playwright 浏览器渲染爬虫** — 等网络好了装 Playwright，用于爬民生银行、光大银行等 SPA 页面的牌价
2. **历史图表数据验证** — 用户还没确认日期选择和历史曲线是否正常显示
3. **CMB 历史 API** — `fx.cmbchina.com/api/v1/fx/history-rate` 参数格式未调通

### 代码结构
```
forex-monitor/
├── main.py              # 入口
├── config.py            # 配置常量 + BANK_SPREADS
├── bank_fetcher.py      # BOC 爬虫 + CMB API + BOC 历史数据
├── fetcher.py           # CFETS 市场数据 (akshare)
├── calculator.py        # bp 计算逻辑
├── database.py          # SQLite 存储
├── ui/
│   ├── main_window.py   # 主窗口 + 系统托盘 + 后台运行
│   ├── quote_bar.py     # 报价栏 (3行: CFETS/BOC/CMB)
│   ├── compare_panel.py # 录入表单
│   └── chart_widget.py  # 历史图表 (4线 + 日期选择)
└── dist/
    └── 实时外汇监控系统.app
```
