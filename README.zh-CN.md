# multi-model-review 中文说明

[English](README.md) | [中文](README.zh-CN.md)

`multi-model-review` 是一个用于 Codex 的多模型审查 Skill。它通过“多模型独立发现问题 + 多模型独立投票确认”的方式，帮助你更稳地审查 PRD、技术方案、架构文档、代码改动、配置文件、日志和数据结论。

如果你经常让 Codex 审查重要文档或项目材料，这个 Skill 主要解决三个问题：

- 单个模型只从一个角度看，容易漏掉问题。
- 弱证据或猜测性问题容易被包装成确定结论。
- 发现问题、判断问题、给出建议混在一次输出里，报告容易变得很吵。

## 它为什么有用

普通的一次性 AI 审查速度很快，但稳定性有限。模型可能发现一个有价值的问题，也可能漏掉关键边界条件，或者把证据不足的风险说得太确定。

`multi-model-review` 把审查拆成两个阶段：

1. **发现阶段**：3 个独立 reviewer 从不同角度审查同一份有边界的材料。
2. **判断阶段**：3 个独立 judge 针对候选问题回到原始材料投票确认。

最终报告默认只展示经过验证的 `3/3` 和 `2/3` 问题，低置信候选问题不会进入默认报告。

## 适合审查什么

- PRD、需求说明、产品方案。
- 技术方案、架构文档、设计文档。
- 代码仓库或局部代码改动。
- 测试计划、验证逻辑、回归风险。
- 配置文件、脚本、运维文档。
- 数据结论、分析报告、事实性判断。

## 审查视角

内置流程默认包含三个互补视角：

- **Correctness review**：检查事实错误、错误假设、前后矛盾、逻辑缺陷和证据不足的结论。
- **Testing review**：检查测试缺口、无效断言、缺失失败路径、脆弱假设和未覆盖的回归风险。
- **Adversarial review**：通过隐藏假设、具体反例、异常输入、信任边界、并发问题和跨组件交互寻找风险。

每个 reviewer 独立工作，不会看到其他 reviewer 的结论。

## 投票机制

发现阶段结束后，Skill 会对候选问题进行规范化、去重和合并。然后 3 个 judge 会回到原始材料，对每个候选问题进行判断。

每个 judge 会返回：

- `confirmed`：原始材料能直接支持这是一个真实、可行动的问题。
- `rejected`：候选问题误读材料、前提错误、超出范围，或不构成可行动问题。
- `insufficient_evidence`：问题可能存在，但当前材料不足以确认。

只有 `confirmed` 会计为支持票。

为了控制成本，judge 阶段使用固定的 3 条 judge lane，而不是为每个候选问题都重新启动一组 3 个 judge sub-agent。

推荐流程是：

1. 启动或配置 `judge-1`、`judge-2`、`judge-3`。
2. 把 `CAND-001` 分别交给 3 个 judge lane 独立投票。
3. 记录投票结果后，清理或丢弃这一轮 candidate 的上下文。
4. 再用同一组 judge lane 判断 `CAND-002`，依次处理后续候选问题。

也就是说，judge 的独立性来自“三个 judge lane 互相看不到对方结果”，不是来自“每个候选问题都新建一批 judge”。

最终分类：

- `3/3`：高置信问题。
- `2/3`：有支持的问题。
- `1/3` 或 `0/3`：默认不展示，除非用户要求完整审计轨迹。

票数只是置信信号，不是证明。最终报告前，主 Codex agent 仍然需要回到原始材料验证问题是否成立。

## 审查模式

### `builtin`

默认模式，使用 3 个独立 Codex discovery reviewer，然后用固定的 3 条 Codex judge lane 对候选问题投票。

适合不希望把材料发送给外部模型服务的本地 Codex 审查流程。

### `hybrid`

混合外部 OpenAI-compatible 模型 API 和 Codex 子智能体。

当前示例配置面向：

- GLM-5.2：correctness review。
- DeepSeek V4 Pro：testing review。
- GPT-5.5 Codex 子智能体：其他内置审查和 judge 角色。

适合明确需要跨模型、跨供应商审查的场景。

### `external`

仅使用外部模型。

只有在你已经配置至少 3 个外部 reviewer，并且确认可以把有边界的审查材料发送给这些供应商时才建议使用。

## 安装

把仓库克隆到本地 Codex skills 目录：

```bash
git clone https://github.com/powerycy/multi-model-review.git ~/.codex/skills/multi-model-review
```

如果仓库是 Private，需要先确保本机 GitHub HTTPS 或 SSH 凭据可用。

## 基本用法

审查单个文件：

```text
用 multi-model-review builtin 审查 /path/to/target.md
```

审查项目目录：

```text
用 multi-model-review builtin 审查 /path/to/project
```

使用混合外部模型审查：

```text
用 multi-model-review hybrid 审查 /path/to/target.md
```

英文也可以：

```text
Use multi-model-review builtin to review /path/to/target.md
```

## Prompt 在哪里改

真实会被读取的 prompt 文件是：

```text
references/reviewer-prompts.md
```

主要 Prompt ID：

- `correctness-review`
- `testing-review`
- `adversarial-review`
- `judge-review`
- `product-review`
- `architecture-review`

如果要调整某个审查视角，直接编辑对应的 `## Prompt: <prompt-id>` 小节即可。这样可以避免“说明文档”和“真实执行 prompt”不一致。

## 外部模型配置

外部 reviewer 示例配置：

```text
references/external-reviewers.example.json
```

外部 judge 示例配置：

```text
references/external-judges.example.json
```

建议复制到仓库外部再修改：

```bash
cp references/external-reviewers.example.json ~/external-reviewers.json
cp references/external-judges.example.json ~/external-judges.json
```

先做一次无网络 dry-run 检查：

```bash
python3 scripts/external_review.py \
  --config ~/external-reviewers.json \
  --input REVIEW_PACKET_PATH \
  --dry-run
```

运行外部 reviewer：

```bash
python3 scripts/external_review.py \
  --config ~/external-reviewers.json \
  --input REVIEW_PACKET_PATH \
  --output EXTERNAL_RESULTS_PATH
```

## 密钥安全

外部模型调用可能会把项目材料发送到本机之外。除非用户明确授权，否则不要使用外部 reviewer。

不要把 API Key 写进这些地方：

- Prompt。
- JSON 配置。
- 命令行参数。
- 日志。
- Git 提交。

推荐使用环境变量：

```bash
export BIGMODEL_API_KEY="..."
export DEEPSEEK_API_KEY="..."
```

本地也支持 `.env.local`，但这个文件必须保留在本机，并且被 Git 忽略。

## Token 与成本提示

多阶段审查比单次审查更稳，但也会消耗更多 token。审查材料越大、候选问题越多，运行时间和模型成本就越高。

建议：

- 只审查当前任务所需的最小范围。
- 排除生成文件、密钥、个人数据和无关项目内容。
- 只有确实需要时再要求完整审计轨迹。
- 除非需要跨供应商验证，否则优先使用 `builtin` 模式。

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
- 外部模型传输必须明确告知并获得授权。
- 审查材料应该有边界，只包含相关内容。
- 发现阶段的支持数量不等于投票。
- judge 投票只是置信信号，不是最终证明。
- 最终报告的问题必须回到原始材料验证。

## 反馈与联系

如果这个 Skill 帮你减少了重复审查、降低了低置信噪声，欢迎给仓库 Star、提 Issue，或分享你的使用场景。

- 邮箱：247133278@qq.com
- 微信：loonges
- QQ：247133278
- 小红书 / B站：好奇的小逸
