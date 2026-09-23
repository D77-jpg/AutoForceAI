# Contributing to GlobalPilot AI

Thank you for your interest in contributing!

> [!IMPORTANT]
> **多 Agent 协作与分支规范见 [AGENTS.md](./AGENTS.md)**（含工作目录分工、分支命名、PR 流程与禁止事项）。
> 本仓库同时有多个 AI agent 在改动代码，**开工前务必先读 AGENTS.md**。
> 铁律：任何改动都从 `main` 开**短命分支** → 开 **PR** → 合入 `main` → **立刻删分支**；不要直接 push `main`。

## Code of Conduct

Please help us keep this project open and inclusive. Be kind and respectful to others.

## How to Contribute

1.  **Fork the repository** on GitHub.
2.  **Clone** your fork locally.
3.  **Create a branch** for your feature or bugfix (`git switch -c feature/amazing-feature`).
    Branch names follow `<agent-or-scope>/<topic>`: `codex/<topic>` (backend), `ui/<topic>` (frontend), `docs/<topic>`.
    Branch from the latest `main` and delete it right after the PR is merged (see [AGENTS.md](./AGENTS.md)).
4.  **Make changes** and commit (`git commit -m 'Add amazing feature'`).
5.  **Push** to your branch (`git push origin feature/amazing-feature`).
6.  **Create a Pull Request**.

## Style Guide

- **Python**: Follow PEP 8. Use typing hints where possible.
- **JavaScript/TypeScript**: Use provided ESLint configurations.
- **Commit Messages**: Use semantic commit messages (e.g., `feat:`, `fix:`, `docs:`).

## Reporting Issues

If you find a bug, please open an issue with:
- Steps to reproduce
- Expected behavior
- Actual behavior
- Screenshots (if applicable)
