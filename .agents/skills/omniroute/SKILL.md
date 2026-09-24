---
name: omniroute
description: Use this skill to start, configure, manage, and route LLM requests through OmniRoute (the local AI gateway/proxy on port 20128). Use when running multi-provider AI models, configuring fallback routes, managing API keys, token compression, or connecting agents.
---

# OmniRoute AI Gateway

OmniRoute is a self-hosted AI gateway that aggregates access to 350+ AI providers and 1200+ models under a single OpenAI-compatible endpoint.

## Quick Start

1. **Start OmniRoute Server:**
   ```bash
   omniroute
   ```
2. **Web Dashboard & Admin UI:**
   - URL: `http://localhost:20128`
   - Set up API keys and configure upstream providers (Anthropic, Gemini, OpenAI, Groq, DeepSeek, local Ollama, etc.).
3. **OpenAI-Compatible Proxy Endpoint:**
   - Base URL: `http://localhost:20128/v1`
   - Use in any coding agent (Antigravity, Cursor, Claude Code, Cline, etc.) by setting the base URL to `http://localhost:20128/v1`.

## Key Capabilities

- **Automatic Failover & Load Balancing:** Automatically routes requests to next available models when rate limits or quotas are reached.
- **Token Compression:** Built-in RTK and Caveman compression reduces token usage by 15% to 90%.
- **CLI Management:**
  - `omniroute` — Start daemon/server
  - `omniroute providers list` — View active providers
  - `omniroute models list` — List all model aliases
  - `omniroute combos list` — Inspect routing strategies and fallback chains
