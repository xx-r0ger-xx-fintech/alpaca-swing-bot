"""
deploy.py — Alpaca Swing Bot DigitalOcean deployment script

Usage:
    python deploy.py

Credentials are loaded from a local .env file (never committed to git).
See .env.example for required variables.
"""

import os
import sys
import time

from dotenv import load_dotenv
load_dotenv()
import json
import urllib.request
import urllib.error

# ── Config ─────────────────────────────────────────────────────────────────────

APP_NAME    = "alpaca-swing-bot"
GITHUB_REPO = "xx-r0ger-xx-fintech/alpaca-swing-bot"
BRANCH      = "main"
RUN_COMMAND = "python -m app.main"
REGION      = "nyc"
DO_API      = "https://api.digitalocean.com/v2"

# ── Helpers ────────────────────────────────────────────────────────────────────

def get_token() -> str:
    token = os.getenv("DO_TOKEN")
    if not token:
        print("ERROR: DO_TOKEN environment variable is not set.")
        sys.exit(1)
    return token


def get_alpaca_keys() -> tuple:
    key    = os.getenv("ALPACA_API_KEY")
    secret = os.getenv("ALPACA_API_SECRET")
    if not key or not secret:
        print("ERROR: ALPACA_API_KEY and ALPACA_API_SECRET must be set.")
        sys.exit(1)
    return key, secret


def get_optional_envs() -> dict:
    return {
        "GITHUB_TOKEN":        os.getenv("GITHUB_TOKEN", ""),
        "DISCORD_WEBHOOK_URL": os.getenv("DISCORD_WEBHOOK_URL", ""),
    }


def api_request(method: str, path: str, token: str, body: dict = None) -> dict:
    url  = f"{DO_API}{path}"
    data = json.dumps(body).encode() if body else None

    req = urllib.request.Request(
        url,
        data=data,
        method=method,
        headers={
            "Authorization":  f"Bearer {token}",
            "Content-Type":   "application/json",
        },
    )

    try:
        with urllib.request.urlopen(req) as resp:
            return json.loads(resp.read())
    except urllib.error.HTTPError as e:
        error_body = e.read().decode()
        print(f"ERROR {e.code}: {error_body}")
        sys.exit(1)


def log(msg: str):
    print(f"  {msg}")


# ── App spec ───────────────────────────────────────────────────────────────────

def build_app_spec(alpaca_key: str, alpaca_secret: str, extras: dict) -> dict:
    envs = [
        {"key": "ALPACA_API_KEY",    "value": alpaca_key,    "type": "SECRET", "scope": "RUN_TIME"},
        {"key": "ALPACA_API_SECRET", "value": alpaca_secret, "type": "SECRET", "scope": "RUN_TIME"},
    ]

    for key, value in extras.items():
        if value:
            envs.append({"key": key, "value": value, "type": "SECRET", "scope": "RUN_TIME"})

    return {
        "name":   APP_NAME,
        "region": REGION,
        "workers": [
            {
                "name":        "worker",
                "run_command": RUN_COMMAND,
                "github": {
                    "repo":           GITHUB_REPO,
                    "branch":         BRANCH,
                    "deploy_on_push": True,
                },
                "envs": envs,
            }
        ],
    }


# ── Core deploy logic ──────────────────────────────────────────────────────────

def find_existing_app(token: str) -> dict | None:
    """Returns the app dict if APP_NAME already exists, else None."""
    resp = api_request("GET", "/apps", token)
    for app in resp.get("apps", []):
        if app["spec"]["name"] == APP_NAME:
            return app
    return None


def create_app(token: str, spec: dict) -> dict:
    print("Creating new app...")
    resp = api_request("POST", "/apps", token, {"spec": spec})
    return resp["app"]


def update_app(token: str, app_id: str, spec: dict) -> dict:
    print("App already exists — updating spec and triggering redeploy...")
    resp = api_request("PUT", f"/apps/{app_id}", token, {"spec": spec})
    return resp["app"]


def trigger_deployment(token: str, app_id: str) -> str:
    resp = api_request("POST", f"/apps/{app_id}/deployments", token, {"force_build": True})
    return resp["deployment"]["id"]


def wait_for_deployment(token: str, app_id: str, deployment_id: str):
    print("Waiting for deployment to complete...")
    print()

    terminal_phases = {"ACTIVE", "ERROR", "CANCELED"}
    dots = 0

    while True:
        resp  = api_request("GET", f"/apps/{app_id}/deployments/{deployment_id}", token)
        phase = resp["deployment"]["phase"]

        print(f"\r  Phase: {phase}" + "." * (dots % 4) + "   ", end="", flush=True)
        dots += 1

        if phase in terminal_phases:
            print()
            return phase

        time.sleep(5)


# ── Entry point ────────────────────────────────────────────────────────────────

def main():
    print()
    print("=" * 50)
    print("  Alpaca Swing Bot — DigitalOcean Deploy")
    print("=" * 50)
    print()

    token          = get_token()
    alpaca_key, alpaca_secret = get_alpaca_keys()
    extras         = get_optional_envs()
    spec           = build_app_spec(alpaca_key, alpaca_secret, extras)

    # Check if app exists
    existing = find_existing_app(token)

    if existing:
        app    = update_app(token, existing["id"], spec)
        app_id = app["id"]
        log(f"App ID: {app_id}")
        deployment_id = trigger_deployment(token, app_id)
    else:
        app    = create_app(token, spec)
        app_id = app["id"]
        log(f"App ID: {app_id}")
        # DO auto-triggers first deployment on create
        print("Waiting for first deployment to initialize...")
        time.sleep(5)
        deployments   = api_request("GET", f"/apps/{app_id}/deployments", token)
        deployment_id = deployments["deployments"][0]["id"]

    log(f"Deployment ID: {deployment_id}")
    print()

    final_phase = wait_for_deployment(token, app_id, deployment_id)

    print()
    if final_phase == "ACTIVE":
        print("SUCCESS: Deployment successful! Bot is live.")
        print()
        print(f"  Dashboard: https://cloud.digitalocean.com/apps/{app_id}")
        print(f"  Logs:      https://cloud.digitalocean.com/apps/{app_id}/runtime-logs")
    else:
        print(f"FAILED: Deployment ended with phase: {final_phase}")
        print(f"  Check logs: https://cloud.digitalocean.com/apps/{app_id}/runtime-logs")
        sys.exit(1)

    print()


if __name__ == "__main__":
    main()
