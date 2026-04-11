import os
import json
import base64
import urllib.request
import urllib.error
from datetime import datetime
import pytz

ET = pytz.timezone("America/New_York")

# In-memory buffer for today's log content (used for GitHub push and Discord at end of scan)
_log_buffer: list[str] = []
_discord_lines: list[str] = []


def _now() -> str:
    return datetime.now(ET).strftime("%H:%M:%S")


def _today() -> str:
    return datetime.now(ET).strftime("%Y-%m-%d")


def log(msg: str):
    """Print timestamped message to stdout — captured by DigitalOcean logs."""
    print(f"[{_now()}] {msg}", flush=True)


def _buffer(line: str):
    """Append a line to the in-memory log buffer."""
    _log_buffer.append(line)


def _write_obsidian(line: str):
    """Append a line to today's trade note in the Obsidian vault (local only)."""
    vault_path = os.getenv("OBSIDIAN_VAULT_PATH", "")
    if not vault_path:
        return

    trading_dir = os.path.join(vault_path, "Trading")
    os.makedirs(trading_dir, exist_ok=True)

    note_path = os.path.join(trading_dir, f"{_today()}.md")

    if not os.path.exists(note_path):
        with open(note_path, "w", encoding="utf-8") as f:
            f.write(f"# Trade Log — {_today()}\n")

    with open(note_path, "a", encoding="utf-8") as f:
        f.write(line + "\n")


def _send_discord(equity: float):
    """Post daily scan summary to Discord via webhook."""
    webhook_url = os.getenv("DISCORD_WEBHOOK_URL", "")
    if not webhook_url or not _discord_lines:
        return

    log_url = f"https://github.com/xx-r0ger-xx/alpaca-swing-bot/tree/main/storage/logs"

    body = {
        "embeds": [
            {
                "title": f"Alpaca Swing Bot — {_today()}",
                "color": 3066993,  # green
                "fields": [
                    {
                        "name": f"Account Equity: ${equity:.2f}",
                        "value": "\n".join(_discord_lines) or "No activity.",
                    }
                ],
                "footer": {
                    "text": f"Full log: {log_url}"
                },
            }
        ]
    }

    try:
        req = urllib.request.Request(
            webhook_url,
            data=json.dumps(body).encode(),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req):
            log("Discord notification sent")
    except urllib.error.HTTPError as e:
        log(f"Discord notify failed: {e.read().decode()}")


def _push_to_github():
    """
    Commits today's log buffer to storage/logs/YYYY-MM-DD.md in the bot repo.
    Requires GITHUB_TOKEN env var (classic token with repo scope).
    Repo is hardcoded to xx-r0ger-xx/alpaca-swing-bot.
    """
    token = os.getenv("GITHUB_TOKEN", "")
    if not token or not _log_buffer:
        return

    repo    = "xx-r0ger-xx/alpaca-swing-bot"
    path    = f"storage/logs/{_today()}.md"
    api_url = f"https://api.github.com/repos/{repo}/contents/{path}"

    content = "\n".join(_log_buffer)
    encoded = base64.b64encode(content.encode("utf-8")).decode("utf-8")

    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type":  "application/json",
        "Accept":        "application/vnd.github+json",
    }

    # Check if file already exists (need SHA to update)
    sha = None
    try:
        req = urllib.request.Request(api_url, headers=headers)
        with urllib.request.urlopen(req) as resp:
            sha = json.loads(resp.read()).get("sha")
    except urllib.error.HTTPError:
        pass  # File doesn't exist yet — that's fine

    body = {
        "message": f"Trade log {_today()}",
        "content": encoded,
    }
    if sha:
        body["sha"] = sha

    try:
        req = urllib.request.Request(
            api_url,
            data=json.dumps(body).encode(),
            headers=headers,
            method="PUT",
        )
        with urllib.request.urlopen(req):
            log(f"Trade log pushed to GitHub: storage/logs/{_today()}.md")
    except urllib.error.HTTPError as e:
        log(f"GitHub push failed: {e.read().decode()}")


# ── Public logging helpers ─────────────────────────────────────────────────────

_current_equity: float = 0.0


def log_scan_start(equity: float, trade_size: float, open_positions: int):
    global _current_equity
    _current_equity = equity

    msg = (
        f"Scan started | "
        f"Equity: ${equity:.2f} | "
        f"Trade size: ${trade_size:.2f} | "
        f"Open positions: {open_positions}/3"
    )
    log(msg)
    _write_obsidian(f"\n## Scan — {_now()}\n**{msg}**\n")
    _buffer(f"# Trade Log — {_today()}\n")
    _buffer(f"## Scan — {_now()}\n**{msg}**\n")


def log_decision(symbol: str, signal, reason: str, price: float):
    icon = {"BUY": "[BUY]", "SELL": "[SELL]"}.get(signal, "[SKIP]")
    msg  = f"{icon} {symbol} @ ${price:.2f} — {reason}"
    log(msg)
    _write_obsidian(f"- {msg}")
    _buffer(f"- {msg}")
    _discord_lines.append(msg)


def log_order(symbol: str, action: str, price: float, qty: float, tp: float, sl: float):
    msg = (
        f"ORDER {action} {qty:.4f} {symbol} @ ${price:.2f} | "
        f"TP: ${tp:.2f} (+{((tp/price)-1)*100:.1f}%) | "
        f"SL: ${sl:.2f} (-{(1-(sl/price))*100:.1f}%)"
    )
    log(msg)
    _write_obsidian(f"  - **{msg}**")
    _buffer(f"  - **{msg}**")
    _discord_lines.append(f"  -> {msg}")


def log_skipped(symbol: str, reason: str):
    msg = f"SKIPPED {symbol} — {reason}"
    log(msg)
    _write_obsidian(f"- {msg}")
    _buffer(f"- {msg}")


def log_error(msg: str):
    log(f"ERROR: {msg}")
    _write_obsidian(f"- ERROR: {msg}")
    _buffer(f"- ERROR: {msg}")


def log_scan_end():
    log("=== Scan complete ===")
    _write_obsidian("\n---\n")
    _buffer("\n---\n")
    _push_to_github()
    _send_discord(_current_equity)
    _log_buffer.clear()
    _discord_lines.clear()
