# Example Configuration Files

This folder contains template files for setting up the n8n Auto-Heal service.

## Files

### `n8n-auto-heal.service.template`
Systemd service template. Copy to `/etc/systemd/system/` and update the environment variables.

### `workflow.json`
Example n8n workflow that can be imported. Update the email addresses before use.

### `.env.example`
Example environment variables file.

## Quick Setup

1. Copy the systemd template:
   ```bash
   sudo cp examples/n8n-auto-heal.service.template /etc/systemd/system/n8n-auto-heal.service
   sudo nano /etc/systemd/system/n8n-auto-heal.service  # Edit variables
   ```

2. Import the workflow:
   - Open n8n
   - Settings → Import/Export
   - Import `workflow.json`
   - Update the email addresses in the Code node

3. Set up the error workflow:
   - Open your main workflows
   - Settings → Error Workflow
   - Select the imported "Global Error Handler"

4. Enable and start the service:
   ```bash
   sudo systemctl daemon-reload
   sudo systemctl enable n8n-auto-heal.service
   sudo systemctl start n8n-auto-heal.service
   ```

## Docker Networking

### Linux Docker (Production Servers)

`host.docker.internal` doesn't work on Linux Docker by default. Use the Docker network gateway IP:

```bash
# Find your n8n container's network gateway
docker network inspect n8n-docker-caddy_default | grep Gateway
# Example: "Gateway": "172.18.0.1"
```

Update the HTTP Request node URL to:
- `http://172.18.0.1:9876/fix-workflow`

**Firewall:** Ensure port 9876 is open from Docker networks:
```bash
sudo ufw allow from 172.18.0.0/16 to any port 9876 comment "n8n Auto-Heal"
```

### Docker Desktop (Mac/Windows)

Use `host.docker.internal:9876` - it works automatically.

### Non-Docker n8n

If n8n runs directly on the host, use:
- `http://localhost:9876/fix-workflow`

## Customization

### Changing the Port

Edit `listener.py` and change the `PORT` variable (default: 9876).

### Different LLM CLI

To use a different CLI tool instead of Kimi:
1. Modify `listener.py` to call your preferred CLI
2. Update the MCP config path accordingly
