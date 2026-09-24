---
name: agent-skills
description: Use this skill to discover, install, update, and manage modular Agent Skills across AI coding agents (Antigravity, Claude Code, Cursor, Codex, Copilot, etc.) using the skills CLI.
---

# Agent Skills Management

Agent Skills are standardized, modular instruction packages (defined via `SKILL.md` with YAML frontmatter) that extend an AI agent's capabilities with specialized workflows, domain runbooks, and automation scripts.

## Core Commands

- **List installed skills:**
  ```bash
  skills list        # project scope
  skills list -g     # global scope
  ```
- **Install skills from GitHub:**
  ```bash
  skills add <owner>/<repo>
  skills add <owner>/<repo> -g    # install globally across all agents
  skills add <owner>/<repo> --all # install all skills without prompt
  ```
- **Find new skills in registry:**
  ```bash
  skills find <query>
  ```
- **Update installed skills:**
  ```bash
  skills update
  skills update -g
  ```
- **Remove skills:**
  ```bash
  skills remove <skill-name>
  ```
