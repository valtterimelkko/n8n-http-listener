# n8n Auto-Heal HTTP Listener

HTTP listener service that receives webhook calls from n8n error workflows and automatically spawns Kimi CLI to analyze and fix the errors.

## Overview

This service enables **self-healing n8n workflows** by:
1. Listening for error notifications from n8n on port 9876
2. Spawning Kimi CLI with n8n-mcp tools to analyze the error
3. Attempting to automatically fix the workflow
4. Notifying via email if the error cannot be auto-fixed

## Architecture

```
n8n Workflow Error
       ↓
Global Error Handler (HTTP Request)
       ↓
POST http://host.docker.internal:9876/fix-workflow
       ↓
This HTTP Listener (Python/FastAPI)
       ↓
Spawns: kimi --quiet --yolo --mcp-config-file ... --prompt "..."
       ↓
Kimi uses n8n-mcp to fix workflow OR sends email notification
```

## Installation

### 1. Clone and Setup

```bash
cd /root/n8n-http-listener
pip3 install fastapi uvicorn pydantic
```

### 2. Install Systemd Service

```bash
cp n8n-auto-heal.service /etc/systemd/system/
systemctl daemon-reload
systemctl enable n8n-auto-heal.service
systemctl start n8n-auto-heal.service
```

### 3. Verify Service

```bash
systemctl status n8n-auto-heal.service
curl http://localhost:9876/health
```

## API Endpoints

### POST /fix-workflow

Receives error data from n8n and triggers Kimi CLI.

**Request Body:**
```json
{
  "workflow_id": "dNn3roEoih6qcpaF",
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
  "workflow_id": "dNn3roEoih6qcpaF",
  "workflow_name": "My Workflow",
  "kimi_result": {
    "success": true,
    "action": "fixed",
    "details": "Fixed null reference error in Code node"
  },
  "timestamp": "2026-02-25T10:00:00Z"
}
```

### GET /health

Health check endpoint.

**Response:**
```json
{
  "status": "healthy",
  "service": "n8n-auto-heal"
}
```

## Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `GMAIL_EMAIL` | Gmail address for notifications | From .bashrc |
| `GMAIL_APP_PASSWORD` | Gmail App Password | From .bashrc |
| `PATH` | Must include kimi CLI path | `/root/.local/bin:/usr/bin:/bin` |

### Files

| File | Purpose |
|------|---------|
| `listener.py` | Main FastAPI application |
| `n8n-auto-heal.service` | Systemd service definition |
| `/var/log/n8n-auto-heal.log` | Application logs |

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

### Kimi CLI not found

Ensure kimi is in PATH:
```bash
which kimi
# Should output: /root/.local/bin/kimi
```

### MCP connection fails

Verify MCP config exists:
```bash
ls -la /root/n8n-integration/.claude/mcp.json
```

## Security Considerations

- Service runs as root (required for kimi CLI access)
- Port 9876 is bound to 0.0.0.0 but only accessible from localhost/Docker
- No authentication on endpoints (assumes localhost-only access)
- Gmail credentials passed via environment variables
- MCP config contains API keys - ensure proper file permissions

## License

Private - For internal use only
