# External Reviewers

Use external APIs only when the user requests cross-provider or external-model review.

## Configuration

Copy `external-reviewers.example.json` to a user-controlled path outside the Skill if customization is needed. Do not place credentials in that JSON file.

The runner loads credentials from process environment variables first, then from the Skill-local `.env.local` without overriding existing variables. Restrict `.env.local` to the current user and never share or commit it.

Each reviewer supports:

- `name`: stable reviewer identifier.
- `endpoint`: full OpenAI-compatible chat-completions URL.
- `model`: provider model identifier.
- `api_key_env`: environment variable containing the API key.
- `prompt_id`: A `## Prompt: <prompt-id>` entry in `reviewer-prompts.md`, such as `correctness-review`, `testing-review`, or `adversarial-review`.
- `enabled`: whether to run this reviewer.
- `thinking`, `reasoning_effort`, `max_tokens`, and `temperature`: optional provider request fields.
- `timeout_seconds`: optional HTTP timeout.

The runner accepts multiple reviewers and executes them concurrently.

The bundled example currently configures:

- Zhipu GLM-5.2 for correctness review.
- DeepSeek V4 Pro for testing review.

Combine these two external reviewers with one Codex reviewer in `hybrid` mode.

For the second-stage vote, use `external-judges.example.json`. Both external models use `prompt_id: judge-review`; combine them with one independent Codex judge using the same prompt.

Run one normalized candidate per judge packet. Include the original bounded material and exactly one candidate. Do not include discovery support counts or other judge results.

## Security

- Revoke any credential pasted into a chat, issue, log, or committed file.
- Prefer environment variables or an OS secret manager. A Skill-local `.env.local` is supported for a private local installation but must use restrictive file permissions.
- Send only the bounded review packet, not the entire workspace.
- Remove credentials, personal data, customer data, private keys, tokens, and unrelated source files.
- Obtain authorization before sending private material to an external provider.
- Review the provider's retention and data-processing terms for sensitive work.

## Hybrid Review

When only one external reviewer is configured, combine it with two different Codex models. When two external reviewers are configured, combine them with one Codex reviewer. Keep all reviewer prompts independent and disclose the actual composition.

## Adding Providers

The bundled runner supports OpenAI-compatible chat-completions APIs. Add another compatible provider by adding a reviewer object with its endpoint, model, and key environment variable.

Providers requiring a different request or response schema need a dedicated adapter in `scripts/external_review.py`; do not pretend an incompatible API is supported.
