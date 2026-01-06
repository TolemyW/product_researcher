# product_researcher
自动化收集产品信息，并分析总结相关信息

> 开发阶段与进度记录：参见 [docs/DEVELOPMENT_PROGRESS.md](docs/DEVELOPMENT_PROGRESS.md)

## 开发阶段规划

### 阶段 1：MVP —— 单渠道采集与基础摘要（含 Source Discovery）
- 在 `src/` 搭建项目骨架（如 `collect/`, `summarize/`, `cli.py`），配置依赖与基础日志。
- 支持单一主要渠道（例如网页 URL 列表）的抓取：实现请求、解析和去重（`collect/web_scraper.py`），允许命令行传入目标 URL。
- 设计数据模型和存储方式（本地 JSON/SQLite），定义统一的原始数据格式。
- 实现最小摘要能力：对抓取结果生成要点（可先用模板或轻量 LLM API 封装 `summarize/basic.py`）。
- **Source Discovery：** 在给定关键词或产品名称时，自动发现潜在数据来源（搜索引擎结果解析、热点榜单/目录抓取），并将发现的链接加入待采集队列，可在 `collect/source_discovery.py` 中实现。
- 在 README 增加使用示例与运行指令；提供一条端到端示例命令（从抓取到输出摘要）。

### 快速上手（MVP）
1. 安装依赖（目前仅使用标准库，无额外安装）。
2. 可选：如需启用 LLM 生成关键词/摘要，请在环境中设置 `OPENAI_API_KEY`（支持 `OPENAI_BASE_URL` 自定义兼容端点），并通过 `--use-llm` 或 `--keyword-brief` 触发。
3. 运行发现 + 抓取 + 摘要的端到端流程（会在本地 `data/` 下写入 JSONL 文件）：
   ```bash
   python -m src.cli pipeline --keywords "新款耳机" --urls https://example.com
   ```
4. 如果已知 URL，可直接抓取后再摘要（可按需调整抓取策略）：
```bash
 python -m src.cli fetch https://example.com/product --timeout 12 --max-retries 2 --delay 0.5
 python -m src.cli summarize
 ```
5. 仅做来源发现：
   ```bash
   # 按产品类型（如 consumer、software、b2b）自动挑选搜索渠道，可通过简述让 LLM 生成关键词
   python -m src.cli discover --keyword-brief "旗舰手机，主打影像与快充" --product-type consumer --llm-model gpt-4o-mini
   ```

5. **阶段 2 新增：清洗与规范化**
   - 将已抓取的原始数据进行语言检测、去重、压缩空白：
     ```bash
     python -m src.cli normalize --data-dir data
     ```
   - 端到端流程会自动在抓取后执行清洗，再做摘要：
    ```bash
    python -m src.cli pipeline --keywords "企业级 CRM" --product-type b2b
    ```

6. **阶段 3 预览：报告导出**
   - 基于已清洗/摘要的数据生成 Markdown 报告（默认中文模板）：
     ```bash
     python -m src.cli report --data-dir data --output data/report.md --title "企业级产品研究报告"
     ```
   - 报告中包含渠道与语言分布、摘要要点、优劣势提炼（基于要点关键词的规则分类）、对比速览以及来源列表，便于在中文语境下快速浏览采集结果。

也可以在端到端流程中指定产品类型，让发现阶段优先使用匹配的渠道：

```bash
python -m src.cli pipeline --keywords "企业级 CRM" --product-type b2b
```

如需在 pipeline 中直接启用 LLM 摘要与关键词扩展，可增加：

```bash
OPENAI_API_KEY=sk-*** python -m src.cli pipeline \
  --keyword-brief "企业级 CRM，关注中大型客户的部署与集成" \
  --product-type b2b --use-llm --llm-model gpt-4o-mini
```

输出文件位于 `data/` 目录：
- `raw.jsonl`：原始抓取结果（URL、标题、正文、抓取时间）。
- `normalized.jsonl`：清洗/标准化后的文档（去重、语言标签等）。
- `summary.jsonl`：要点摘要（对应 URL 的条目、摘要要点、生成时间）。

### 自动化调度与部署（阶段 4）
1. 复制调度示例配置并按需调整：
   ```bash
   cp config/schedule.example.json config/schedule.json
   ```
   - 可在 `env_file` 中指定 `.env`，格式为 `KEY=VALUE`，用于注入 `OPENAI_API_KEY` 等敏感信息。
   - 在 `default_*` 字段设置数据目录、默认产品类型/LLM，`tasks` 内可分别配置关键词、URL、报告导出路径与执行间隔。

2. 一次性或循环调度运行（默认将日志写入 `logs/pipeline.log`）：
   ```bash
   python -m src.cli schedule --config config/schedule.json --run-once
   # 循环 5 轮、每轮间隔 30 秒
   python -m src.cli schedule --config config/schedule.json --max-cycles 5 --sleep-seconds 30
   ```

3. Docker/Compose 方式启动（挂载数据、日志与配置目录）：
   ```bash
   docker compose up --build
   # 自定义配置文件
   docker compose run researcher python -m src.cli schedule --config config/schedule.json --run-once
   ```

4. 监控与后续告警：
   - 每次任务结束会在 `logs/pipeline.log` 记录 JSON 行，包含任务名、状态、耗时、报错与生成的报告路径。
   - 可将日志文件挂载到日志聚合/告警系统，实现失败通知或按耗时监控。

#### 抓取策略与渠道选择
- **按产品类型自动挑选渠道与抓取策略：**
  - `consumer`/`hardware`：偏重电商与测评站点，超时 8s，最多 2 次重试。
  - `software`/`saas`：偏重官方文档/社区，超时 12s，最多 2 次重试。
  - `b2b`/`enterprise`：偏重行业报告、案例、G2/Gartner 等，超时 15s，最多 3 次重试，每次重试前等待 1s。
- **可自定义抓取策略参数：**
  ```bash
  # B2B 产品，定制 UA、超时、重试与节流
  python -m src.cli pipeline \
    --keywords "企业级 CRM" --product-type b2b \
    --user-agent "product-researcher-demo/0.2" \
    --timeout 20 --max-retries 3 --delay 1.5
  ```

- **多渠道抓取路由（阶段 2 新增）：**
  - 按 URL 自动分配到不同抓取器并标记 `channel`，便于后续分析与质量监控。
  - 消费类：`ecommerce`（京东/淘宝/亚马逊）、`reviews`（知乎/视频平台）
  - 软件类：`docs`（官方文档站）、`github`（仓库）
  - B2B：`analyst_reports`（Gartner/Forrester/G2）、`case_studies`（官网案例/白皮书）
  - 其他未命中域名的链接会落到 `general` 通道。
  - CLI 会在抓取结果中返回使用到的渠道列表：
    ```bash
    python -m src.cli fetch https://item.jd.com/123.html https://example.com/blog --product-type consumer
    # 输出示例：{"fetched":2,"added":2,"file":"data/raw.jsonl","channels":["ecommerce","general"]}
    ```
  - **并发抓取（阶段 2 新增）：** 可通过 `--concurrency` 控制并行 worker 数，批量 URL 时提升吞吐且保留每个通道的策略。
    ```bash
    python -m src.cli fetch \
      https://item.jd.com/123.html https://www.bilibili.com/video/abc \
      --product-type consumer --concurrency 4
    ```
    端到端流程同样支持并发：
    ```bash
    python -m src.cli pipeline --keywords "企业级 CRM" --product-type b2b --concurrency 3
    ```

### 阶段 2：多源采集与数据清洗
- 新增电商/社媒/垂直媒体等渠道采集器（如 `collect/amazon.py`, `collect/twitter.py`），抽象统一接口，支持并发/队列，并根据产品类型自动挑选适配的渠道（如消费电子优先电商和测评，软件产品优先官方文档与 GitHub）。
- 考虑 B2B 产品的情境：接入行业报告/案例/第三方评测等信息源（如 `analyst_reports/`, `case_studies/` 抓取器），并支持以关键词自动搜索企业官网、招投标/RFP、G2/Gartner 等评论索引。
- 引入结构化清洗/规范化流程（`pipeline/normalize.py`）：字段映射、去噪、语言检测、重复检测。
- 为不同渠道设计可配置的抓取策略（headers、重试、节流），并允许渠道动态增减或开关。
- 增加采集与清洗的单元测试与集成测试样例；在 README 记录新增渠道的配置方法。

### 阶段 3：分析与报告生成
- 在 `analysis/` 目录实现要点提炼、优劣势总结、价格/规格对比等模块。
- 支持多产品对比的报告模板（Markdown/HTML），并提供导出命令（`cli.py report`）。
- 为分析结果添加可配置的提示词/模板，支持多语言输出。
- 增加示例数据与快照测试，确保报告格式稳定；更新 README 展示示例报告片段。

### 阶段 4：自动化运行与部署（已落地）
- 通过 `config/schedule.example.json` 管理任务队列、默认数据目录与 LLM 设置，可搭配 `.env` 注入敏感信息。
- CLI 新增 `schedule` 命令，支持一次性执行（`--run-once`）或按间隔轮询（`--max-cycles` + `--sleep-seconds`），并将运行结果写入 `logs/pipeline.log`。
- Dockerfile 与 `docker-compose.yml` 支持一键启动调度流程，默认挂载 `data/`、`logs/`、`config/` 目录。
- 监控与告警基础：每次任务写入结构化日志（状态、耗时、报错），便于日志聚合或后续接入通知渠道。

### 阶段 5：性能与质量优化
- 优化并发抓取与缓存策略，降低重复请求；为关键路径增加性能基准。
- 完善错误处理与回退策略，覆盖异常场景的测试。
- 引入基本可观测性（追踪采集/分析耗时），并记录优化前后指标。
- 更新文档，给出性能与稳定性指标基线。

### 阶段 6：可视化与交互
- 构建轻量 Web UI（如 `app/`），展示抓取列表、摘要、对比报告，并支持导出。
- 实现前端过滤/搜索，后端提供对应 API（`api/`）。
- 增加演示数据与截图/录屏，补充用户操作手册。
