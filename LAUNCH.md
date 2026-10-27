# Launch drafts

**Unpublished drafts.** Planned source destination: `https://github.com/LucasXlab/skillvet`. Confirm the repository exists, finish final QA and obtain release approval before posting. Source version 1.0.0 is not a registry release. Remote CI and star state remain pending.

## GitHub

### Description

Offline Python CLI for reviewing local agent skills, hooks and MCP configs. Inspect finite static risk signals, scan errors, coverage notes and suppression receipts. Strict mode ignores target-controlled exceptions. JSON/SARIF, zero runtime dependencies; Python 3.9+ on POSIX. A clean scan is not a safety verdict.

### Topics

```json
["python", "cli", "security", "static-analysis", "ai-agents", "agent-skills", "mcp", "sarif", "developer-tools", "offline"]
```

## Hacker News

Internal planning only; do not submit this AI-generated sample. HN requires human-written submissions and comments without AI editing. A human maker must write independently from personal work. [Guidelines](https://news.ycombinator.com/newsguidelines.html).

### Title

Show HN: Skillvet – local static review for agent skills, hooks and MCP configs

### First post

Skillvet is a small Python CLI for inspecting a local skill directory before deciding whether to enable it. It reads supported instructions, configuration grants, hooks and constant local script references as text. It does not execute them, call a model or upload the report.

The demo focuses on how to interpret a result:

- A clean fixture exits 0; malformed MCP JSON is incomplete and exits 2.
- A target can carry inline suppressions and its own ignore file. Compatibility mode records those exceptions; strict mode ignores the target's exceptions and exposes the supported findings. An explicit caller-provided ignore still applies.
- A synthetic secret is masked in the output. This is finite pattern masking, not general anonymization.
- JSON and SARIF retain rule/location and processing state. The checked-in recording labels selected-field views and includes the full raw reports alongside them.

There are 19 deterministic rules in the source. SKILL frontmatter is a deliberately small subset, and constant local references have explicit limits. Dynamic behavior, arbitrary downstream execution and unknown patterns remain outside the scan. A clean result does not establish that a skill is safe.

The runtime uses Python's standard library and POSIX descriptor-relative reading; declared minimum Python is 3.9. Independent local engineering checks passed 98 tests on 3.9, 3.11 and 3.13, plus installed-wheel tests. Python 3.11 whole-package statement coverage was 96.34%. These are local engineering results, not real-world detection accuracy or a remote CI claim.

Source and a real CLI recording on synthetic input: https://github.com/LucasXlab/skillvet

The scope is intentionally inspectable. There is no competitor benchmark or real-Skills precision/recall result yet. Feedback on useful static cases, false positives and clear coverage reporting would help determine what to evaluate next.

## Reddit draft 1 — r/Python monthly showcase comment

Use the current monthly showcase thread rather than a standalone showcase post. The [official rules](https://old.reddit.com/r/Python/about/rules/) and [October 2026 showcase](https://old.reddit.com/r/Python/comments/1wxjay5/showcase_thread/) were checked on 2026-10-24; verify the current thread and rules before posting.

### What My Project Does

This project was developed with AI assistance. The examples are synthetic and the limits below remain part of the claim.

Skillvet is an offline, standard-library Python CLI that reads supported local agent skills, hooks and MCP configuration as text. It reports finite static risk signals, selected-file processing errors, unfollowed reference notes, and visible skip/suppression receipts. JSON and SARIF output are available.

### Target Audience

Developers reviewing a downloaded skill or maintaining their own instruction/configuration bundle on POSIX with Python 3.9+. Strict mode ignores the target's own ignore rules and inline suppressions while retaining explicit caller ignores. No scanned code is executed.

### Comparison

Ordinary text search remains useful for arbitrary patterns. Skillvet groups a small set of known instruction/configuration formats with grant-specific checks, root-bounded reads, exit-code semantics and explicit exception receipts. It does not claim better detection than existing scanners; no real-world accuracy or competitor benchmark has been run.

A checked-in real CLI recording demonstrates clean/incomplete states, compatibility versus strict mode, finite secret masking and SARIF on synthetic data. The source has 98 locally passing tests on Python 3.9/3.11/3.13. A passing scan is not permission to trust or execute an unfamiliar skill.

Source: https://github.com/LucasXlab/skillvet

## Reddit draft 2 — r/SideProject technical feedback

Candidate feedback draft, not posting approval. The [official sidebar](https://old.reddit.com/r/SideProject/) uses “Project name - short description” for link titles. Recheck the current sidebar, rules and pinned threads before posting; an empty rules API response is not permission. Do not use threads that exclude AI-assisted projects.

### Title

Skillvet - Offline static review of agent skills with exception receipts

### Body

Skillvet was developed with AI assistance. It is a small Python CLI for reviewing a local directory of supported agent instructions, hooks and MCP configuration before deciding what to enable.

The synthetic demo distinguishes no gate-triggering finding from an incomplete scan: clean exits 0, a detected finding at the configured threshold exits 1, and malformed input exits 2. Compatibility mode records target-controlled skip/suppression receipts. Strict mode ignores the target's own exceptions while respecting explicit caller ignores.

The tool reads inspected text without executing it, calling a model or uploading output. JSON and SARIF reports are included. Selected-field views in the real CLI recording are labelled, and full raw reports remain available for inspection.

Python 3.9+ and POSIX secure-read APIs are required. The rule set, frontmatter subset, static-reference coverage and secret masking are finite. There is no real-Skills precision/recall result, competitor-advantage claim or safety guarantee.

Feedback on whether the exception receipts and coverage notes make a report easier to interpret would help. Reproducible synthetic cases and false positives are welcome; no human-use story or adoption figure is claimed.

Source and demo: https://github.com/LucasXlab/skillvet

## r/commandline — excluded from this launch plan

The [official rules](https://www.reddit.com/r/commandline/about/rules.json), retrieved on 2026-10-26, prohibit AI-generated titles/posts. They also impose project-age/commit-history requirements and restrictions involving generative AI, plus disclosure requirements for AI-assisted code. This AI-written draft is not eligible for posting there; the earlier “full rules unavailable” note was outdated. No publishable title or post is supplied, and rewriting or concealing AI provenance is not a workaround.

Fact brief only: Skillvet is an AI-assisted Python CLI for finite static signals in local agent assets, with visible coverage/exception information. It has no runtime third-party dependencies and includes a reproducible synthetic CLI capture. It has no real-Skills accuracy or comparative-advantage evidence. Project-age/commit eligibility has not been established. These facts are for reference, not community clearance or an AI-written submission.

## X / Twitter — five posts

1. Before enabling an agent skill, inspect what it can ask for. Skillvet reads supported local skills, hooks and MCP configs as text and reports finite static signals. No model or execution. https://github.com/LucasXlab/skillvet

2. The real CLI demo distinguishes clean from incomplete: a clean fixture exits 0; malformed config exits 2. Exit 0 does not prove safety, and coverage notes still matter. All demo inputs are synthetic.

3. Target-controlled exceptions deserve scrutiny. Compatibility mode records skip/suppression receipts. Strict mode ignores the target's ignore file and inline suppressions; explicit caller ignores still apply.

4. A synthetic token is masked in the demo's JSON and SARIF. That is limited known-pattern masking, not general anonymization. Selected-field views are labelled; the full unfiltered CLI reports are included for inspection.

5. Python 3.9+, zero runtime dependencies, POSIX secure reads. Local tests: 98 passed on 3.9/3.11/3.13. No real-world accuracy or competitor advantage is claimed. Source + real capture: https://github.com/LucasXlab/skillvet

## 掘金草稿

### 标题

启用 Agent Skill 之前，先读清扫描范围、告警和例外收据

### 正文

一个 Skill 目录不只有指令正文：还可能带工具授权、Hook、MCP 配置及脚本引用。skillvet 把支持的静态材料读成文本，输出有限、可解释的规则信号，不执行被扫描的脚本，也不调用模型或上传报告。

这次演示使用实际安装后的 CLI 与合成输入，重点是区分结果含义：正常样例退出 0，损坏的 MCP JSON 标成 incomplete 并退出 2；目标目录自带的忽略和行内抑制在兼容模式中留下收据，而 strict 模式不接受这些自抑制。显式由调用者提供的 ignore 仍然有效。

另有合成凭据脱敏、frontmatter 授权和 SARIF 输出示例。为了便于阅读，部分 JSON/SARIF 画面明确标注为包装器选择字段的视图，完整原始报告与 cast、复现脚本一起保留，没有把筛选视图冒充未经处理的输出。

项目要求 Python 3.9+ 和 POSIX 安全文件读取接口，运行时只有标准库。独立本地工程验收在 Python 3.9/3.11/3.13 各通过 98 项测试；语句覆盖率不是检测准确率。frontmatter 只是明确子集，动态脚本链和未知模式不在覆盖范围，脱敏也不等于彻底匿名化。

没有真实 Skills 语料的精确率/召回率数据，也没有相对其他扫描器的优势证据。扫描通过不能证明安全安装，更不能代替执行权限与运行环境的隔离。

源码与真实合成演示：https://github.com/LucasXlab/skillvet

希望先收集可复现的静态样例、误报和覆盖提示的展示问题，再决定下一步评测。

## V2EX 草稿

### 标题

分享 skillvet：离线检查 Agent Skill、Hook 和 MCP 配置的有限静态信号

### 正文

这是一个 Python 标准库 CLI，用于启用陌生 Skill 前的本地静态审阅。它读取支持的指令、授权字段、配置和常量脚本引用，不执行被扫文本、不下载脚本、不调用模型。

比较想解决的一个问题是：目标目录自己写的 ignore 和 suppression 是否把结果藏掉了？兼容模式保留可读收据；strict 模式忽略目标的这些例外，但仍尊重调用者显式传入的 ignore。JSON/SARIF 也保留完整性和范围信息。

真实 CLI 合成样例中，正常退出 0、损坏配置退出 2、达到门槛的告警退出 1。仓库附完整原始报告和录制，画面中选择字段的视图会明确注明。

Python 3.9+，POSIX 安全读取，零运行时第三方依赖。已有 98 项测试在 3.9/3.11/3.13 本地通过；远端 CI 尚待真实运行。规则、frontmatter 与引用范围有限，目前没有真实 Skills 精度或竞品优越性结论。扫描通过不代表安全。

项目：https://github.com/LucasXlab/skillvet

欢迎提供合成复现、误报或更清楚的报告展示建议。

## 即刻草稿

做了一个小型离线 CLI：skillvet。

启用陌生 Agent Skill 前，先查看支持的指令、授权、Hook 和 MCP 配置里有哪些有限静态信号，同时看扫描未完成的部分、覆盖提示与目标自抑制收据。

Python 3.9+、标准库运行时，不执行被扫脚本，不调用模型。仓库演示来自真实 CLI 与合成输入，附完整报告和原始录制。

没有真实语料精度或竞品优势结论；扫描通过不能证明安全安装。工具的价值需要在明确边界内评估。

源码：https://github.com/LucasXlab/skillvet

## Product Hunt

### Tagline

Review agent skills with visible static signals and exceptions

### Description

Skillvet is an offline Python CLI for reviewing supported local agent skills, hooks and MCP configuration. Inspect finite rule signals alongside processing errors, coverage notes and suppression receipts. Strict mode ignores target-controlled exceptions. JSON and SARIF support local review workflows.

It reads text without executing it, calling a model or uploading output. The source includes real CLI captures on synthetic fixtures and reproducible scripts. Python 3.9+ and POSIX secure-read APIs are required. Frontmatter, references and secret masking have explicit limits; a clean scan is not a safety verdict. No real-world accuracy or comparative advantage is claimed.

### Maker comment

The next useful step is an inspectable evaluation corpus, including false positives and uninspected cases. Feedback on the distinction between a gate, a coverage note and a target-controlled exception would be especially helpful. This release draft makes no runtime-protection or detection-accuracy promise.
