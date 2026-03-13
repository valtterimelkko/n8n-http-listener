# n8n Auto-Heal HTTP Listener

HTTP listener service that receives webhook calls from n8n error workflows and automatically spawns Kimi CLI to analyze and fix the errors.

## What is this for and who is this for? Any dependencies?


This repo is for a tech stack where one hosts a self-hosted n8n instance, uses Kimi Code CLI tool. However, it could be modified with minimal effort to function using any other code agent tool, Claude Code, Codex, Gemini CLI, OpenCode, Kilo Code, an others (just the shell command and the flags used need to be changed). 

One also needs to have set up the n8n-mcp (https://github.com/czlonkowski/n8n-mcp) and the skills related to that (https://github.com/czlonkowski/n8n-skills) and make sure those are fully installed on their agent. The main repo is the HTTP listener service that receives webhook calls from n8n error workflows and automatically spawns Kimi CLI to analyze and fix the errors. 

One needs to set up a global error workflow at their n8n instance - and connect that to their workflows in production - and this becomes a self-healing system where the agent is able to autonomously try to fix the errors in the workflows. The agent, with the n8n-mcp server and the skills, is able to create the error workflow for you - but you need to set the error workflow connection manually. There's an example JSON of an error workflow that works together with the HTTP listener in this repo as well.

## Overview

This service provides two main capabilities:

### 1. Self-Healing n8n Workflows
- Listens for error notifications from n8n on port 9876
- Spawns an LLM CLI with MCP tools to analyze the error
- Attempts to automatically fix the workflow
- Notifies via email if the error cannot be auto-fixed

### 2. File Storage for n8n Workflows
- Provides HTTP endpoints for n8n workflows to save files to disk
- Bypasses n8n's task runner sandboxing restrictions
- Supports subfolders for organizing files by workflow/purpose
- API key authentication for security

## How to adopt this into your own use?

For security purposes, all the references to my own server and real examples have been removed from here - and not with a placeholder system that works like: "add your personal server details in config file X and it all works then". However you can give the repo's URL to your favourite coding agent (Claude Code, Codex, OpenCode, Kilo Code, Kimi Code, you name it) and say you want to copy the repo into a a folder, adopt it to your own n8n instance running from a Docker (insert the folder it's running from) and its public URL (give the URL) - and adopt it to the command line commands of your favourite CLI coding agent tool. Ask it to autonomously build and adopt the package, test the HTTP listener works, and then, using the n8n-mcp, first make sure you have a global error workflow in place, adopt that to use this HTTP listener to start the self-healing process - and then, using the same MCP, build a test workflow that's intentionally broken and is being triggered every 10 minutes. You can then publish that workflow manually, connect it to the global error workflow, and wait for it to be triggered (manually triggered workflows don't trigger error workflows). Then, when the workflow is being triggered, but you can ask your agent to see the logs of the HTTP listener whether it gets the calls from your n8n, see if the agent fixed the workflow using the n8n-mcp again - and ask your agent to go back&forth with you to debug if it doesn't work - until it works.

## Architecture

```
n8n Workflow Error
       ↓
Global Error Handler (HTTP Request)
       ↓
POST http://host.docker.internal:9876/fix-workflow
       ↓
HTTP Listener (Python/FastAPI)
       ↓
Spawns: kimi --quiet --yolo --mcp-config-file ... --prompt "..."
       ↓
LLM uses MCP to fix workflow OR sends email notification
```

## Prerequisites

- Python 3.8+
- n8n instance (Docker or standalone)
- Kimi CLI (or Claude Code, Aider, etc.)
- Gmail account with App Password (for notifications)
- MCP server configuration for n8n

## Installation

### 1. Clone the Repository

```bash
git clone https://github.com/yourusername/n8n-http-listener.git
cd n8n-http-listener
```

### 2. Install Dependencies

```bash
pip3 install -r requirements.txt
```

### 3. Configure Environment

Copy the example env file and fill in your values:

```bash
cp examples/.env.example .env
nano .env
```

Edit the `.env` file with your credentials:
```bash
NOTIFICATION_EMAIL=your-email@example.com
GMAIL_EMAIL=your-email@example.com
GMAIL_APP_PASSWORD=your-16-char-app-password
MCP_CONFIG=/path/to/mcp.json
SKILLS_DIR=/path/to/skills
```

### 4. Install Systemd Service

```bash
# Copy the template and edit
sudo cp examples/n8n-auto-heal.service.template /etc/systemd/system/n8n-auto-heal.service
sudo nano /etc/systemd/system/n8n-auto-heal.service  # Update paths

# Or use the production service file if you're the repo owner
sudo cp n8n-auto-heal.service /etc/systemd/system/  # (not in public repo)

sudo systemctl daemon-reload
sudo systemctl enable n8n-auto-heal.service
sudo systemctl start n8n-auto-heal.service
```

### 5. Verify Service

```bash
systemctl status n8n-auto-heal.service
curl http://localhost:9876/health
```

### 6. Configure n8n Workflow

1. Import the example workflow from `examples/workflow.json`
2. Update the email addresses in the "Prepare Error Data" node
3. Set this workflow as the Error Workflow for your main workflows

## API Endpoints

### POST /fix-workflow

Receives error data from n8n and triggers the LLM CLI.

**Request Body:**
```json
{
  "workflow_id": "abc123",
  "workflow_name": "My Workflow",
  "failed_node": "HTTP Request",
  "error_message": "404 Not Found",
  "execution_id": "12345",
  "execution_url": "https://n8n.example.com/execution/12345"
}
```

**Response:**
```json
{
  "status": "fix_attempted",
  "workflow_id": "abc123",
  "workflow_name": "My Workflow",
  "kimi_result": {
    "success": true,
    "action": "fixed",
    "details": "Fixed null reference error in Code node"
  },
  "timestamp": "2026-02-25T10:00:00Z"
}
```

### POST /save-file

Receive a file from n8n and save it to disk. Bypasses n8n's task runner sandboxing.

**Headers:**
```
X-API-Key: your-api-key-here  # Required if API_KEY is configured
Content-Type: multipart/form-data
```

**Request Body (multipart/form-data):**
- `file` (required): The binary file to save
- `subfolder` (optional): Subfolder within the storage path (e.g., "gdrive-files", "exports/2024")
- `filename` (optional): Custom filename (if not provided, uses original filename)

**Response:**
```json
{
  "success": true,
  "message": "File saved successfully",
  "saved_path": "/mnt/n8n-file-bridge/20240313_143052_document.pdf",
  "relative_path": "20240313_143052_document.pdf",
  "filename": "20240313_143052_document.pdf",
  "size_bytes": 15420,
  "timestamp": "2024-03-13T14:30:52.123456"
}
```

### POST /save-file-json

Alternative endpoint for saving base64-encoded files from JSON payload.
Useful when n8n can't easily send multipart/form-data.

**Headers:**
```
X-API-Key: your-api-key-here  # Required if API_KEY is configured
Content-Type: application/json
```

**Request Body:**
```json
{
  "filename": "document.pdf",
  "subfolder": "gdrive-files",
  "content_base64": "JVBERi0xLjQKJdPr6eEKMSAwIG9iago8PAovVHlw..."
}
```

**Response:** Same as `/save-file`

### GET /health

Health check endpoint.

**Response:**
```json
{
  "status": "healthy",
  "service": "n8n-auto-heal",
  "version": "1.1.0",
  "file_storage_path": "/mnt/n8n-file-bridge",
  "api_key_required": true
}
```

## Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `NOTIFICATION_EMAIL` | Email for failure notifications | Required |
| `GMAIL_EMAIL` | Gmail address for sending | Required |
| `GMAIL_APP_PASSWORD` | Gmail App Password | Required |
| `MCP_CONFIG` | Path to MCP config JSON | `/root/n8n-integration/.claude/mcp.json` |
| `SKILLS_DIR` | Path to skills directory | `/root/.skills-global/skills-global` |
| `KIMI_BIN` | Path to Kimi CLI binary | `/root/.local/bin/kimi` |

### Using with Different LLM CLIs

To use Claude Code, Aider, or another CLI instead of Kimi:

1. Modify `listener.py`:
   - Change the `KIMI_BIN` default or set via env var
   - Adjust the command-line arguments as needed

2. Update the MCP config path to match your CLI's requirements

## Logs

```bash
# View service logs
journalctl -u n8n-auto-heal.service -f

# View application logs
tail -f /var/log/n8n-auto-heal.log
```

## Troubleshooting

### Service won't start

1. Check logs: `journalctl -u n8n-auto-heal.service -n 50`
2. Verify Python dependencies: `pip3 list | grep -E "fastapi|uvicorn"`
3. Check port availability: `lsof -i :9876`
4. Verify `.env` file exists and is readable

### LLM CLI not found

Ensure the CLI is in PATH:
```bash
which kimi
# Should output the path set in KIMI_BIN
```

### MCP connection fails

Verify MCP config exists:
```bash
ls -la $MCP_CONFIG
```

### Workflow not being fixed

1. Check that n8n can reach the listener:
   ```bash
   # From inside n8n container
   curl http://host.docker.internal:9876/health
   ```

2. Check listener logs for Kimi CLI output

## File Storage Security

### API Key Authentication

The file storage endpoints (`/save-file`, `/save-file-json`) support API key authentication to prevent unauthorized access.

**Configuration:**
1. Set `API_KEY` in your `.env` file:
   ```bash
   API_KEY=your-secure-random-key-here
   ```
2. Include the key in requests via the `X-API-Key` header

**Security Features:**
- Filename sanitization to prevent directory traversal attacks
- Subfolder path sanitization (removes `..` and absolute paths)
- Automatic timestamp prefix to prevent file overwrites
- Files are saved to a sandboxed directory (`/mnt/n8n-file-bridge` by default)

### Why This is Needed

n8n v2.x introduced **task runner sandboxing** that prevents workflows from writing files to disk, even with correct Docker volume permissions. This HTTP listener provides a secure workaround by:
1. Running outside n8n's sandbox environment
2. Validating and sanitizing all inputs
3. Requiring API key authentication
4. Limiting writes to a specific directory

## Security Considerations

- Service typically runs as root (for CLI access)
- Port 9876 should not be exposed externally
- Gmail App Passwords should be used (not main password)
- MCP config contains API keys - restrict file permissions
- Store credentials in `.env` file (gitignored)
- **File Storage**: Set a strong `API_KEY` to prevent unauthorized file uploads

## Docker Considerations

### n8n in Docker (recommended)

Use `host.docker.internal:9876` in the HTTP Request node to reach the host.

### n8n on Host

Use `localhost:9876` in the HTTP Request node.

## Examples

See the `examples/` directory for:
- Systemd service template
- n8n workflow JSON (importable)
- Environment file template

## Contributing

Contributions welcome! Please ensure:
- No credentials in committed files
- Use `.env` for local configuration
- Update examples/ for new features

## License

MIT License - See LICENSE file

## Acknowledgments

Inspired by Nate Herk's "I Will Never Fix Another n8n Workflow" concept using AI agents for self-healing workflows.
