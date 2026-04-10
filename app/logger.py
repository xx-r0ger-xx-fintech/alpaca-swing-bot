import os
from datetime import datetime
import pytz

ET = pytz.timezone("America/New_York")


def _now() -> str:
    return datetime.now(ET).strftime("%H:%M:%S")


def _today() -> str:
    return datetime.now(ET).strftime("%Y-%m-%d")


def log(msg: str):
    """Print timestamped message to stdout — captured by DigitalOcean logs."""
    print(f"[{_now()}] {msg}", flush=True)


def _write_obsidian(line: str):
    """Append a line to today's trade note in the Obsidian vault (local only)."""
    vault_path = os.getenv("OBSIDIAN_VAULT_PATH", "")
    if not vault_path:
        return

    trading_dir = os.path.join(vault_path, "Trading")
    os.makedirs(trading_dir, exist_ok=True)

    note_path = os.path.join(trading_dir, f"{_today()}.md")

    # Write header on first entry of the day
    if not os.path.exists(note_path):
        with open(note_path, "w", encoding="utf-8") as f:
            f.write(f"# Trade Log — {_today()}\n")

    with open(note_path, "a", encoding="utf-8") as f:
        f.write(line + "\n")


# ── Public logging helpers ─────────────────────────────────────────────────────

def log_scan_start(equity: float, trade_size: float, open_positions: int):
    msg = (
        f"Scan started | "
        f"Equity: ${equity:.2f} | "
        f"Trade size: ${trade_size:.2f} | "
        f"Open positions: {open_positions}/3"
    )
    log(msg)
    _write_obsidian(f"\n## Scan — {_now()}\n**{msg}**\n")


def log_decision(symbol: str, signal, reason: str, price: float):
    icon = {"BUY": "✅", "SELL": "🔴"}.get(signal, "⏭️")
    msg  = f"{icon} {symbol} @ ${price:.2f} — {reason}"
    log(msg)
    _write_obsidian(f"- {msg}")


def log_order(symbol: str, action: str, price: float, qty: float, tp: float, sl: float):
    msg = (
        f"ORDER {action} {qty:.4f} {symbol} @ ${price:.2f} | "
        f"TP: ${tp:.2f} (+{((tp/price)-1)*100:.1f}%) | "
        f"SL: ${sl:.2f} (-{(1-(sl/price))*100:.1f}%)"
    )
    log(msg)
    _write_obsidian(f"  - **{msg}**")


def log_skipped(symbol: str, reason: str):
    msg = f"SKIPPED {symbol} — {reason}"
    log(msg)
    _write_obsidian(f"- ⏩ {msg}")


def log_error(msg: str):
    log(f"ERROR: {msg}")
    _write_obsidian(f"- ❌ ERROR: {msg}")


def log_scan_end():
    log("=== Scan complete ===")
    _write_obsidian("\n---\n")
