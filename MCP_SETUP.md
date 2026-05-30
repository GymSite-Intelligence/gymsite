# MCP Server Setup for Antigravity

> **What is MCP?** Model Context Protocol — a standard way for AI agents to connect to external tools (databases, APIs, browsers).

## Available MCP Servers

This project includes a template configuration with 4 MCP servers:

| Server | Purpose | What it enables |
|---|---|---|
| **Supabase** | Database access | Query tables, inspect schema, run migrations directly from chat |
| **GitHub** | Repo management | Create PRs, review issues, check CI status |
| **Playwright** | Browser automation | Take screenshots, run E2E tests, debug UI visually |
| **Gemini API** | AI model access | Switch models, check quotas, manage API keys |

## Installation

### Step 1: Copy the template

```bash
# Create Antigravity config directory
mkdir -p ~/.gemini/antigravity

# Copy template
cp mcp-config.template.json ~/.gemini/antigravity/mcp_config.json
```

### Step 2: Add your real tokens

Edit `~/.gemini/antigravity/mcp_config.json` and replace placeholder values:

```json
{
  "mcpServers": {
    "supabase": {
      "env": {
        "SUPABASE_ACCESS_TOKEN": "sbp_your_real_token_here"
      }
    },
    "github": {
      "env": {
        "GITHUB_PERSONAL_ACCESS_TOKEN": "ghp_your_real_token_here"
      }
    },
    "gemini-api": {
      "env": {
        "GEMINI_API_KEY": "AIzaSy_your_real_key_here"
      }
    }
  }
}
```

### Step 3: Get your tokens

| Service | How to get token |
|---|---|
| **Supabase** | Dashboard → Project Settings → API → Access Tokens |
| **GitHub** | Settings → Developer settings → Personal access tokens → Tokens (classic) |
| **Gemini** | Google AI Studio → Get API key |

### Step 4: Restart Antigravity

Close and reopen Antigravity IDE. The MCP servers will be detected automatically.

## Usage in Chat

Once configured, you can ask the agent to:

```
"Query the oportunidades_prospeccao table for the last 10 records"
→ Uses Supabase MCP

"Create a PR with the title 'Fix pagination bug'"
→ Uses GitHub MCP

"Take a screenshot of /prospeccao page at mobile viewport"
→ Uses Playwright MCP

"Check my Gemini API quota"
→ Uses Gemini API MCP
```

## Troubleshooting

```bash
# Verify MCP config is valid
cat ~/.gemini/antigravity/mcp_config.json | python -m json.tool

# Check if npx is available
which npx && npx --version

# Test a specific MCP server
npx -y @supabase/mcp-server@latest --help
```

## Security Notes

- 🔒 `mcp_config.json` lives in `~/.gemini/` (home directory), NOT in the project repo
- 🔒 Never commit real tokens to git
- 🔒 The template file `mcp-config.template.json` uses fake values and is safe to commit
