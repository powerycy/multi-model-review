# multi-model-review

`multi-model-review` 是一个用于 Codex 的多模型审查 Skill。它通过“多模型独立发现问题 + 多模型投票确认”的方式，帮助你减少单一模型审查时常见的漏报、误报和低置信噪声。

如果你经常让 Codex 审查 PRD、技术方案、架构设计、代码改动或数据结论，这个 Skill 可以把审查过程拆成更可靠的两步：先让 3 个独立审查者发现候选问题，再让 3 个独立判断者逐条投票确认，最终默认只报告经过验证的 `3/3` 和 `2/3` 问题。

如果这个项目对你有帮助，欢迎给仓库点一个 Star。后续我会继续补充更多模型配置、审查模板和真实使用案例。

## 适合谁使用

这个 Skill 适合这些场景：

- 你经常用 Codex 审查 PRD、技术方案或架构文档。
- 你希望代码审查不只依赖单个模型的一次判断。
- 你想让不同审查视角分别检查事实、测试、边界条件和隐藏假设。
- 你需要把 GLM、DeepSeek 等外部模型接入 Codex 审查流程。
- 你希望最终报告更克制，只展示有足够证据支持的问题。

## 可以审查什么

- PRD、需求说明、产品方案
- 技术方案、架构文档、设计文档
- 代码仓库或局部代码改动
- 配置文件、脚本、日志
- 数据结论、分析报告、事实性判断

## 你会得到什么

默认情况下，最终报告只输出经过投票确认的问题：

- `3/3`：高置信问题，3 个 judge 都确认。
- `2/3`：有支持的问题，至少 2 个 judge 确认。

`1/3` 和 `0/3` 默认不会进入最终报告，避免把低置信猜测包装成结论。

一个简化后的报告可能长这样：

```text
3/3 高置信问题
- 严重程度：medium
- 位置：docs/architecture.md 的缓存失效策略
- 问题：文档假设缓存一定会在 5 分钟内刷新，但没有说明失败重试或手动失效机制。
- 影响：当上游数据修正后，用户可能继续看到旧结果。
- 建议：补充缓存失效失败时的降级策略，并加入对应测试。

2/3 有支持的问题
- 严重程度：low
- 位置：scripts/import.py 的输入校验
- 问题：脚本没有说明空文件输入时的预期行为。
- 影响：批量导入时可能出现不可解释的失败。
- 建议：定义空文件处理规则，并补充 dry-run 验证。
```

## 它怎么工作

整个流程分为两个阶段。

### 第一阶段：发现候选问题

3 个独立 reviewer 会从不同角度审查同一份材料：

- `correctness-review`：检查事实错误、逻辑错误、前后矛盾和错误假设。
- `testing-review`：检查测试缺口、失败路径、回归风险和验证不足。
- `adversarial-review`：用反例、异常输入、隐藏假设和跨组件交互寻找风险。

每个 reviewer 独立工作，不会看到其他 reviewer 的结论。

### 第二阶段：投票确认问题

3 个独立 judge 会使用同一套 `judge-review` prompt，对每个候选问题逐条判断：

- `confirmed`：原始材料能直接支持这个问题。
- `rejected`：候选问题误读了材料，或不构成真实问题。
- `insufficient_evidence`：问题可能存在，但当前材料不足以确认。

只有 `confirmed` 会计为支持票。票数是置信信号，不是证明；最终报告前仍然需要回到原始材料验证 `3/3` 和 `2/3` 问题。

## 安装

如果你要把它作为本地 Codex Skill 使用，可以把仓库放到 Codex skills 目录：

```bash
git clone https://github.com/powerycy/multi-model-review.git ~/.codex/skills/multi-model-review
```

如果仓库是 Private，需要先确保本机 GitHub HTTPS 或 SSH 凭据可用。

## 基本用法

在 Codex 中直接说明要使用这个 Skill，例如：

```text
用 multi-model-review builtin 审查 /path/to/target.md
```

也可以审查一个目录：

```text
用 multi-model-review builtin 审查 /path/to/project
```

如果你想混合外部模型：

```text
用 multi-model-review hybrid 审查 /path/to/target.md
```

## 审查模式

- `builtin`：默认模式，只使用 Codex 内置模型。当前配置使用 3 个独立 `gpt-5.5` reviewer，再用 3 个独立 `gpt-5.5` judge。
- `hybrid`：混合外部模型和 Codex。当前示例配置是 GLM-5.2、DeepSeek V4 Pro、GPT-5.5。
- `external`：仅使用外部模型。只有在你明确配置了至少 3 个外部 reviewer 时才建议使用。

## Prompt 在哪里改

真实会被程序读取的 prompt 文件是：

```text
references/reviewer-prompts.md
```

里面有清晰的映射关系：

- `correctness-review`
- `testing-review`
- `adversarial-review`
- `judge-review`
- 可选的 `product-review`
- 可选的 `architecture-review`

如果你想调整某个模型的审查方式，直接编辑 `references/reviewer-prompts.md` 里对应的 `## Prompt: <prompt-id>` 小节即可。

本仓库不再保留单独的 `prompt` 说明文件，避免出现“说明文件”和“真实读取文件”不一致的问题。

## 外部模型配置

外部 reviewer 示例配置在这里：

```text
references/external-reviewers.example.json
```

外部 judge 示例配置在这里：

```text
references/external-judges.example.json
```

建议复制到仓库外部再修改：

```bash
cp references/external-reviewers.example.json ~/external-reviewers.json
cp references/external-judges.example.json ~/external-judges.json
```

常用配置项包括：

- `name`：reviewer 或 judge 的名称。
- `endpoint`：OpenAI-compatible chat-completions 接口地址。
- `model`：模型名称。
- `api_key_env`：读取 API Key 的环境变量名。
- `prompt_id`：要使用的 prompt。
- `enabled`：是否启用。
- `max_tokens`：最大输出 token 数。
- `temperature`：温度参数。

运行外部模型 reviewer：

```bash
python3 scripts/external_review.py \
  --config ~/external-reviewers.json \
  --input REVIEW_PACKET_PATH \
  --output EXTERNAL_RESULTS_PATH
```

先做一次无网络 dry-run 检查：

```bash
python3 scripts/external_review.py \
  --config ~/external-reviewers.json \
  --input REVIEW_PACKET_PATH \
  --dry-run
```

## 密钥安全

不要把 API Key 写进这些地方：

- prompt
- JSON 配置
- 命令行参数
- 日志
- Git 仓库

推荐使用环境变量，例如：

```bash
export BIGMODEL_API_KEY="..."
export DEEPSEEK_API_KEY="..."
```

本地也支持 `.env.local`，但这个文件只能放在本机，并且必须被 `.gitignore` 忽略。

## 仓库结构

```text
.
├── SKILL.md
├── README.md
├── agents/
│   └── openai.yaml
├── references/
│   ├── reviewer-prompts.md
│   ├── external-reviewers.md
│   ├── external-reviewers.example.json
│   └── external-judges.example.json
└── scripts/
    └── external_review.py
```

## 设计原则

- 审查默认只读，不修改用户文件。
- 外部模型调用前必须明确获得用户授权。
- 只发送有边界的 review packet，不发送整个工作区。
- 票数只是置信信号，不等于证明。
- 最终报告前必须回到原始材料验证 `3/3` 和 `2/3` 问题。

## 反馈与支持

如果这个 Skill 帮你减少了重复审查、降低了低置信噪声，欢迎：

- 给仓库点一个 Star。
- 提 Issue 反馈你希望支持的审查场景。
- 分享你常用的外部模型配置。

联系方式：

- 微信：loonges
- 小红书：好奇的小逸
