# multi-model-review

一个用于 Codex 的多模型审查 Skill。它会先用 3 个独立 reviewer 发现候选问题，再用 3 个独立 judge 对候选问题投票，最终默认只报告经过验证的 `3/3` 和 `2/3` 问题。

这个 Skill 适合审查：

- PRD、技术方案、架构文档
- 代码仓库或局部代码改动
- 配置文件、脚本、日志
- 数据结论、分析报告、事实性判断

## 它怎么工作

流程分两阶段：

1. **Discovery / 发现问题**
   - `correctness-review`：检查事实错误、逻辑错误、矛盾、错误假设。
   - `testing-review`：检查测试缺口、失败路径、回归风险、验证不足。
   - `adversarial-review`：用反例、异常输入、隐藏假设、跨组件交互来找问题。

2. **Judge / 投票确认**
   - 所有 judge 使用同一套 `judge-review` prompt。
   - 每个候选问题单独判断。
   - 只有 `confirmed` 计为支持票。
   - 默认最终报告只输出：
     - `3/3`：高置信问题
     - `2/3`：有支持的问题

`1/3` 和 `0/3` 默认不进入最终报告，避免把低置信噪声当成结论。

## 安装

如果你要作为本地 Codex Skill 使用，可以把仓库放到 Codex skills 目录：

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

混合外部模型时：

```text
用 multi-model-review hybrid 审查 /path/to/target.md
```

常用模式：

- `builtin`：默认模式，只使用 Codex 内置模型。当前配置使用 3 个独立 `gpt-5.5` reviewer，再用 3 个独立 `gpt-5.5` judge。
- `hybrid`：混合外部模型和 Codex。当前示例配置是 GLM-5.2、DeepSeek V4 Pro、GPT-5.5。
- `external`：仅外部模型。只有在你明确配置了至少 3 个外部 reviewer 时才建议使用。

## Prompt 在哪里改

真实会被程序读取的 prompt 文件是：

```text
references/reviewer-prompts.md
```

里面有清晰的映射表：

- `correctness-review`
- `testing-review`
- `adversarial-review`
- `judge-review`
- 可选的 `product-review`
- 可选的 `architecture-review`

如果你想改某个模型的审查方式，直接编辑 `references/reviewer-prompts.md` 里对应的 `## Prompt: <prompt-id>` 小节即可。

注意：本仓库不再保留单独的 `prompt` 说明文件，避免出现“说明文件”和“真实读取文件”不一致的问题。

## 外部模型配置

外部 reviewer 示例配置：

```text
references/external-reviewers.example.json
```

外部 judge 示例配置：

```text
references/external-judges.example.json
```

建议复制到仓库外部再改：

```bash
cp references/external-reviewers.example.json ~/external-reviewers.json
cp references/external-judges.example.json ~/external-judges.json
```

然后在配置里调整：

- `name`
- `endpoint`
- `model`
- `api_key_env`
- `prompt_id`
- `enabled`
- `max_tokens`
- `temperature`

外部模型 runner：

```bash
python3 scripts/external_review.py \
  --config ~/external-reviewers.json \
  --input REVIEW_PACKET_PATH \
  --output EXTERNAL_RESULTS_PATH
```

先做无网络 dry-run 检查：

```bash
python3 scripts/external_review.py \
  --config ~/external-reviewers.json \
  --input REVIEW_PACKET_PATH \
  --dry-run
```

## 密钥安全

不要把 API Key 写进：

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

本地也支持 `.env.local`，但这个文件必须只放在本机，并且已经被 `.gitignore` 忽略。

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
- 外部模型调用前必须明确用户授权。
- 只发送有边界的 review packet，不发送整个工作区。
- 票数是置信信号，不是证明。
- 最终报告前必须回到原始材料验证 `3/3` 和 `2/3` 问题。
