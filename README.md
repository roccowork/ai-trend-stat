# AI Trend Stat

GitHub Trending 开源项目统计分析平台，基于 statsmodels 进行统计建模，自动采集、分析并展示热门开源项目趋势。

## 在线访问

- **网站**: https://ai-trend-stat.pages.dev
- **API**: https://ai-trend-stat-api.roccowork.workers.dev

## 功能特性

### 当前已实现

- **数据采集**: 自动从 GitHub Trending 页面采集 daily/weekly/monthly 热门项目
- **API 数据增强**: 通过 GitHub API 补充项目详细信息（创建时间、提交活动等）
- **统计建模分析**: 使用 statsmodels 进行线性回归分析
- **项目评分系统**:
  - 热度分 (40%): 基于期间新增 Stars
  - 活跃分 (30%): 基于近4周提交数
  - 成长分 (20%): 当前增速 vs 历史增速
  - 成熟分 (10%): 项目年龄和总 Stars
- **可视化展示**: 语言分布、Stars 增长排行、提交趋势图表
- **自动化部署**: GitHub Actions 定时采集（每天2次），采集、分析、部署在同一个 job 里完成
- **每日推送**: ops-desk 的个人助理每天读取 `data/trending.json`，把今日最火 10 个和增长最快的 10 个 AI 项目推送到 Telegram

### 未来规划

#### 更多统计指标
- **项目健康度**: 基于 issue 响应率、PR 合并率、代码覆盖率
- **社区活跃度**: 贡献者数量增长、讨论热度、文档完整度
- **技术栈分析**: 依赖库分析、框架偏好、技术趋势
- **生命周期阶段**: 自动识别项目处于新兴/成长/成熟/衰退阶段

#### AI 项目使用建议
- **场景推荐**: 根据项目类型（LLM框架/Agent/RAG/推理优化）推荐适合场景
- **入门难度评估**: 基于文档质量、示例完整度、学习曲线分析
- **生产就绪度**: 稳定性评估、维护活跃度、企业采用情况
- **替代方案对比**: 同类项目横向比较，帮助选型决策

#### 高级功能
- **历史趋势追踪**: 累积历史数据，分析长期趋势变化
- **邮件/Webhook 订阅**: 新项目上榜通知、关注项目动态推送
- **自定义筛选**: 按语言、标签、Stars 范围等多维筛选
- **付费高级功能**: 详细报告导出、API 访问、定制分析

## 技术架构

```
├── src/
│   ├── data/
│   │   └── trending_collector.py    # GitHub Trending 数据采集
│   └── analysis/
│       └── trend_analyzer.py        # statsmodels 统计分析
├── public/
│   ├── index.html                   # 前端页面
│   ├── css/style.css                # 样式
│   ├── js/trending-app.js           # 前端应用逻辑
│   └── data/                        # 采集的 JSON 数据
├── workers/
│   └── index.js                     # Cloudflare Worker API
├── .github/workflows/
│   └── deploy.yml                   # CI/CD 自动化
└── wrangler.toml                    # Cloudflare 配置
```

## 本地开发

### 环境要求
- Python 3.11+
- Node.js 18+ (可选，用于本地预览)

### 安装依赖
```bash
pip install requests beautifulsoup4 pandas numpy statsmodels
```

### 运行数据采集
```bash
# 设置 GitHub Token 提高 API 限额（可选）
export GITHUB_TOKEN=your_token_here

# 采集数据
cd src/data
python trending_collector.py

# 运行分析
cd ../analysis
python trend_analyzer.py
```

### 本地预览
```bash
# 使用任意静态服务器
cd public
python -m http.server 8080
# 访问 http://localhost:8080
```

## 部署配置

### GitHub Secrets
| Secret | 说明 |
|--------|------|
| `CLOUDFLARE_API_TOKEN` | Cloudflare API 令牌 |
| `CLOUDFLARE_ACCOUNT_ID` | Cloudflare 账户 ID |
| `GH_PAT` | GitHub Personal Access Token |

### 定时任务
- 每天 UTC 23:00 和 11:00 自动采集（新加坡时间 07:00 和 19:00；GitHub 定时任务常推迟 1～2 小时）
- 采集完成后自动部署到 Cloudflare Pages

## 贡献

欢迎提交 Issue 和 Pull Request！

## License

MIT
