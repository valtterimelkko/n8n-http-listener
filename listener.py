#!/usr/bin/env python3
"""
n8n Auto-Heal HTTP Listener
Receives webhook calls from n8n error workflows and spawns Kimi CLI to fix them.
"""

import json
import logging
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel

# Configuration
PORT = 9876
HOST = "0.0.0.0"
LOG_FILE = "/var/log/n8n-auto-heal.log"
KIMI_TIMEOUT_SECONDS = 600  # 10 minutes max for Kimi to fix

# Paths (configurable via env vars)
MCP_CONFIG = os.environ.get("MCP_CONFIG", "/root/n8n-integration/.claude/mcp.json")
SKILLS_DIR = os.environ.get("SKILLS_DIR", "/root/.skills-global/skills-global")
KIMI_BIN = os.environ.get("KIMI_BIN", "/root/.local/bin/kimi")
NOTIFICATION_EMAIL = os.environ.get("NOTIFICATION_EMAIL", "your-email@example.com")

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE),
        logging.StreamHandler(sys.stdout),
    ],
)
logger = logging.getLogger("n8n-auto-heal")

app = FastAPI(title="n8n Auto-Heal Listener", version="1.0.0")


class WorkflowError(BaseModel):
    """Error data from n8n"""
    workflow_id: str
    workflow_name: str
    failed_node: str
    error_message: str
    execution_id: str
    execution_url: str = ""


def build_kimi_prompt(error_data: WorkflowError) -> str:
    """Build the prompt for Kimi CLI"""
    return f"""You are an n8n workflow repair agent. A workflow has failed with an error.

ERROR DETAILS:
- Workflow ID: {error_data.workflow_id}
- Workflow Name: {error_data.workflow_name}
- Failed Node: {error_data.failed_node}
- Error Message: {error_data.error_message}
- Execution ID: {error_data.execution_id}
- Execution URL: {error_data.execution_url}

YOUR TASK:
1. Use your n8n skills available to you to examine the workflow - make sure you connect to the n8n-mcp directly, do not use docker commands or similar
2. Analyze the error and determine if it's fixable (code errors, logic issues, etc.)
   vs. unfixable (expired credentials, rate limits, third-party outages)
3. If FIXABLE:
   - Use n8n-mcp tools (n8n_get_workflow, n8n_update_partial_workflow, etc.) to fix it
   - Do NOT use docker commands - connect directly via MCP
   - Use your n8n skills to guide your work
4. If NOT FIXABLE:
   - Use your gmail-send skill to notify {NOTIFICATION_EMAIL}
   - Subject: "n8n Workflow Error - Manual Fix Required: {error_data.workflow_name}"
   - Include the error details and why it couldn't be auto-fixed

REQUIREMENTS:
- Connect to n8n via the configured n8n-mcp server (direct connection)
- Do NOT run docker exec commands or similar
- Return a JSON summary of what you did

OUTPUT FORMAT:
Return ONLY a JSON object like:
{{"success": true/false, "action": "fixed|notified_unfixable|failed", "details": "..."}}
"""


def spawn_kimi(prompt: str) -> dict:
    """Spawn Kimi CLI process and return result"""
    cmd = [
        KIMI_BIN,
        "--quiet",  # Non-interactive mode
        "--yolo",   # Auto-approve all tool calls
        "--mcp-config-file", MCP_CONFIG,
        "--skills-dir", SKILLS_DIR,
        "--prompt", prompt,
    ]
    
    logger.info(f"Spawning Kimi CLI with MCP and skills directory...")
    
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=KIMI_TIMEOUT_SECONDS,
            env={**dict(subprocess.os.environ), "PATH": "/root/.local/bin:/usr/bin:/bin"},
        )
        
        logger.info(f"Kimi exited with code: {result.returncode}")
        
        if result.returncode != 0:
            logger.error(f"Kimi stderr: {result.stderr}")
            return {
                "success": False,
                "action": "failed",
                "details": f"Kimi process failed: {result.stderr}",
            }
        
        # Try to parse JSON from output
        output = result.stdout.strip()
        logger.info(f"Kimi output preview: {output[:500]}...")
        
        # Look for JSON in the output
        try:
            # Try to find JSON object in the output
            start_idx = output.find("{")
            end_idx = output.rfind("}")
            if start_idx != -1 and end_idx != -1:
                json_str = output[start_idx:end_idx+1]
                parsed = json.loads(json_str)
                return parsed
        except json.JSONDecodeError:
            pass
        
        # If no JSON found, return the raw output
        return {
            "success": True,
            "action": "unknown",
            "details": output,
        }
        
    except subprocess.TimeoutExpired:
        logger.error("Kimi process timed out")
        return {
            "success": False,
            "action": "failed",
            "details": f"Kimi process timed out after {KIMI_TIMEOUT_SECONDS} seconds",
        }
    except Exception as e:
        logger.error(f"Error spawning Kimi: {str(e)}")
        return {
            "success": False,
            "action": "failed",
            "details": f"Exception: {str(e)}",
        }


@app.post("/fix-workflow")
async def fix_workflow(error: WorkflowError):
    """Receive error from n8n and trigger Kimi CLI fix"""
    logger.info(f"Received error for workflow: {error.workflow_name} (ID: {error.workflow_id})")
    logger.info(f"Failed node: {error.failed_node}")
    logger.info(f"Error: {error.error_message[:200]}...")
    
    # Build prompt for Kimi
    prompt = build_kimi_prompt(error)
    
    # Spawn Kimi CLI
    result = spawn_kimi(prompt)
    
    logger.info(f"Kimi result: {result}")
    
    return JSONResponse(
        content={
            "status": "fix_attempted",
            "workflow_id": error.workflow_id,
            "workflow_name": error.workflow_name,
            "kimi_result": result,
            "timestamp": datetime.utcnow().isoformat(),
        }
    )


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "service": "n8n-auto-heal"}


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "service": "n8n Auto-Heal Listener",
        "version": "1.0.0",
        "endpoints": ["/fix-workflow", "/health"],
    }


if __name__ == "__main__":
    import uvicorn
    
    logger.info(f"Starting n8n Auto-Heal Listener on {HOST}:{PORT}")
    uvicorn.run(app, host=HOST, port=PORT, log_level="info")
