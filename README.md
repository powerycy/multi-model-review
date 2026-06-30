# multi-model-review

[English](README.md) | [中文](README.zh-CN.md)

`multi-model-review` is a Codex Skill for evidence-based reviews across three independent model channels.

It helps Codex review PRDs, technical proposals, architecture documents, code changes, configuration files, logs, and data claims with a more disciplined workflow: first discover candidate issues from different review lenses, then validate those candidates through independent judging before reporting only higher-confidence findings.

By default, the Skill tries to use **GLM + DeepSeek + Codex** when external API keys are configured. If external keys are missing, invalid, unavailable, or the user requests local-only review, it falls back to Codex-only review.

If you often ask Codex to review important documents or project artifacts, this Skill is designed to reduce three common problems:

- Missing issues because one model looked from only one angle.
- Reporting weak or speculative findings as if they were confirmed.
- Mixing discovery, judgment, and final recommendations into one noisy pass.

## Why This Skill Exists

Single-pass AI reviews are fast, but they can be inconsistent. A model may notice a useful issue, miss a critical edge case, or overstate a weak concern.

`multi-model-review` separates the review into two stages:

1. **Discovery**: three independent channels inspect the same bounded review packet from complementary perspectives.
2. **Judging**: three independent judge lanes evaluate candidate issues against the original material and vote on whether each issue is supported.

The final report focuses on verified `3/3` and `2/3` findings, while lower-confidence candidates stay out of the default report.

## Best For

- Product requirement documents and PRDs.
- Technical design documents and architecture proposals.
- Code repositories or focused code changes.
- Test plans, validation logic, and regression risk reviews.
- Configuration files, scripts, and operational runbooks.
- Analytical reports, data claims, and factual conclusions.

## Review Lenses

The built-in review flow uses three complementary lenses:

- **Correctness review**: checks factual errors, invalid assumptions, contradictions, logic defects, and unsupported conclusions.
- **Testing review**: checks missing test coverage, weak assertions, untested failure paths, flaky assumptions, and regression risk.
- **Adversarial review**: looks for hidden assumptions, concrete counterexamples, abnormal inputs, trust-boundary failures, concurrency issues, and unsafe cross-component interactions.

Each reviewer works independently and does not see the other reviewers' findings.

## Voting Model

After discovery, the Skill normalizes and merges candidate findings. Then three judges evaluate each candidate against the original material.

Each judge returns one of:

- `confirmed`: the original material directly supports the candidate as a real, actionable issue.
- `rejected`: the candidate misreads the material, relies on a false premise, is out of scope, or is not actionable.
- `insufficient_evidence`: the candidate may be valid, but the supplied material is not enough to establish it.

Only `confirmed` counts as a supporting vote.

To control cost, the judge stage uses exactly three judge lanes for the whole review run instead of launching a new set of three judge sub-agents for every candidate.

The intended flow is:

1. Start or configure `judge-1`, `judge-2`, and `judge-3`.
2. Send `CAND-001` to the three judge lanes for independent votes.
3. Record the verdicts, then clear or discard that candidate-specific context.
4. Reuse the same three judge lanes for `CAND-002` and the remaining candidates.

In other words, independence comes from the three judge lanes not seeing each other's results. It does not require creating a fresh group of three judges for every candidate.

Final classifications:

- `3/3`: high-confidence finding.
- `2/3`: supported finding.
- `1/3` or `0/3`: hidden from the default report unless the user asks for the full audit trail.

Votes are confidence signals, not proof. The main Codex agent must still re-check the original artifacts before reporting or fixing a finding.

## Modes

### `auto`

Default mode. Uses GLM + DeepSeek + Codex when the external keys are configured, and falls back to Codex-only review when they are not.

Use this for normal reviews.

### `builtin`

Codex-only fallback mode. Uses three independent Codex discovery reviewers, then a fixed pool of three Codex judge lanes for candidate voting.

Use this when external API keys are not configured, external calls are unavailable, or you want a local Codex-native workflow without sending material to external model providers.

### `hybrid`

Default path when external keys are configured. Combines external OpenAI-compatible model APIs with Codex sub-agents.

The bundled example is designed around:

- GLM-5.2 for correctness review.
- DeepSeek V4 Pro for testing review.
- GPT-5.5 Codex sub-agents for the remaining built-in review and judge roles.

Use this when you want the main three-model value proposition: GLM + DeepSeek + Codex.

### `external`

Uses external reviewers only.

Use this only when you have configured at least three external reviewers and you are comfortable sending the bounded review packet to those providers.

## Installation

Clone this repository into your local Codex skills directory:

```bash
git clone https://github.com/powerycy/multi-model-review.git ~/.codex/skills/multi-model-review
```

If the repository is private, make sure your local GitHub HTTPS or SSH credentials are configured first.

## Basic Usage

Ask Codex to use this Skill on a file:

```text
Use multi-model-review to review /path/to/target.md
```

Or on a project directory:

```text
Use multi-model-review to review /path/to/project
```

To force cross-provider review:

```text
Use multi-model-review hybrid to review /path/to/target.md
```

To force local Codex-only review:

```text
Use multi-model-review builtin to review /path/to/target.md
```

For Chinese prompts:

```text
用 multi-model-review 审查 /path/to/target.md
```

## Prompt Customization

The canonical prompt file is:

```text
references/reviewer-prompts.md
```

Prompt IDs include:

- `correctness-review`
- `testing-review`
- `adversarial-review`
- `judge-review`
- `product-review`
- `architecture-review`

Edit the matching `## Prompt: <prompt-id>` section to tune a reviewer or judge. This avoids drift between documentation and the prompts actually used by the Skill.

## External Model Configuration

Example external reviewer configuration:

```text
references/external-reviewers.example.json
```

Example external judge configuration:

```text
references/external-judges.example.json
```

Recommended workflow:

```bash
cp references/external-reviewers.example.json ~/external-reviewers.json
cp references/external-judges.example.json ~/external-judges.json
```

The default bundled configuration expects:

- `BIGMODEL_API_KEY` for GLM.
- `DEEPSEEK_API_KEY` for DeepSeek.

When both keys are configured, the default review path is GLM + DeepSeek + Codex. When the keys are not configured, the Skill falls back to Codex-only review.

Validate configuration without network access:

```bash
python3 scripts/external_review.py \
  --config ~/external-reviewers.json \
  --input REVIEW_PACKET_PATH \
  --dry-run
```

Run external reviewers:

```bash
python3 scripts/external_review.py \
  --config ~/external-reviewers.json \
  --input REVIEW_PACKET_PATH \
  --output EXTERNAL_RESULTS_PATH
```

## Security Notes

External model calls can send project material outside your machine. Do not use external reviewers unless the user has authorized that transfer.

Never place API keys in:

- Prompts.
- JSON config files.
- Command-line arguments.
- Logs.
- Git commits.

Use environment variables instead:

```bash
export BIGMODEL_API_KEY="..."
export DEEPSEEK_API_KEY="..."
```

The Skill also supports a local `.env.local` file, but it must remain private and ignored by Git.

## Cost And Token Notes

Multi-stage review is more reliable than a single-pass review, but it costs more tokens. Large review packets and many candidate findings can increase both runtime and model usage.

For best results:

- Review the smallest useful artifact scope.
- Exclude generated files, secrets, private data, and unrelated project content.
- Ask for the full audit trail only when you need it.
- Use the default `auto` mode for three-model review. Use `builtin` only when you need local-only review or lower external API cost.

## Repository Structure

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

## Design Principles

- Review is read-only by default.
- External model transmission must be explicit and authorized.
- Review packets should be bounded and relevant.
- Discovery support count is not treated as a vote.
- Judge votes are confidence signals, not final proof.
- Reported findings must be re-verified against the original artifacts.

## Support And Contact

If this Skill helps your review workflow, you are welcome to star the repository, open an issue, or share your use case.

- Email: 247133278@qq.com
- WeChat: loonges
- QQ: 247133278
- Xiaohongshu / Bilibili: 好奇的小逸
