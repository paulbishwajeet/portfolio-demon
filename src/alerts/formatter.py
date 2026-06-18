from src.utils.date_utils import now_et


def _h(text: str) -> str:
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def _action_label(pct_below_ma: float, headroom: float, status: str) -> str:
    if status == "new":
        return "INITIATE on weakness"
    if pct_below_ma <= -8.0 and headroom > 50000:
        return "STRONG ADD"
    if pct_below_ma <= -7.0:
        return "ADD"
    return "WATCH"


def format_weekly_digest(
    holdings: list[dict], config: dict, breakdown: dict,
    health: dict, signals: list[dict],
) -> tuple[str, str, str]:
    """Returns (subject, plain_text, html)."""
    dt = now_et()
    date_str = dt.strftime("%a %b %d, %Y")
    owner = config.get("OWNER_NAME", "Portfolio Owner")
    subject = f"IRA Portfolio Digest — {dt.strftime('%b %d, %Y')}"

    # Band status
    equity_pct = health["equity_of_invested_pct"]
    fund_pct = health["fund_of_invested_pct"]
    if health["band_breach"]:
        band_label = f"⚠️ OUTSIDE 80/20 band"
    else:
        band_label = "✓ within 80/20 band"

    cash = breakdown["cash"]
    cash_pct = breakdown["cash_pct"]

    lines = [
        f"📊 IRA WEEKLY DIGEST — {date_str}",
        "",
        "💼 PORTFOLIO HEALTH",
        f"Total value:     ${breakdown['total_value']:,.0f}",
        f"Equity / Funds:  {equity_pct:.0f}% / {fund_pct:.0f}%  {band_label}",
        f"Cash remaining:  ${cash:,.0f}  ← {cash_pct:.1f}% — deploy priority",
        f"Cycle phase:     {health['cycle_phase']}  (set by you)",
    ]

    # Rebalance flags
    rebalance = [s for s in signals if s["type"] in ("band_breach", "overweight", "speculative_cap")]
    lines.extend(["", "⚖️ REBALANCE FLAGS"])
    if rebalance:
        for s in rebalance:
            lines.append(s["message"])
    else:
        lines.append("None this week — portfolio within bands")

    # Deployment opportunities
    deployment = [s for s in signals if s["type"] == "deployment_opportunity"]
    lines.extend(["", "🛒 DEPLOYMENT OPPORTUNITIES  (significant dips only)"])
    if deployment:
        for s in deployment[:8]:
            sym = s["symbol"]
            label = _action_label(s["pct_below_ma"], s["headroom_amount"], _get_status(holdings, sym))
            note = _get_note(holdings, sym)
            if _get_status(holdings, sym) == "new":
                lines.append(f"{sym:<8}new position{' ':>10}headroom ${s['headroom_amount']:,.0f}  → {label}")
            else:
                lines.append(f"{sym:<8}{s['pct_below_ma']:+.1f}% below 50d MA   headroom ${s['headroom_amount']:,.0f}  → {label}{note}")
    else:
        lines.append("✓ No qualifying dips this week")

    # Sector rotation watch
    rotation = [s for s in signals if s["type"] == "rotation"]
    lines.extend(["", f"🔄 SECTOR ROTATION WATCH  (cycle: {health['cycle_phase']})"])
    if rotation:
        for s in rotation:
            if s["reduce_symbols"]:
                reduce_names = " · ".join(r["symbol"] for r in s["reduce_symbols"][:6])
                lines.append(f"Consider reducing:  {reduce_names}  (tech ETFs)")
            if s["favor_symbols"]:
                favor_names = " · ".join(f["symbol"] for f in s["favor_symbols"][:6])
                lines.append(f"Consider adding:    {favor_names}  (defensive)")
        lines.append("No urgent action — monitor monthly")
    else:
        lines.append("✓ No rotation signals")

    # Speculative watchlist
    spec_holdings = [h for h in holdings if h["category"] == "speculative" and h["deployed_shares"] > 0]
    lines.extend(["", "📌 SPECULATIVE WATCHLIST"])
    if spec_holdings:
        for h in spec_holdings:
            if h["pl_pct"] >= 0:
                direction = "above"
                action = "thesis intact, hold" if h["status"] == "active" else h["status"]
            else:
                direction = "below"
                action = "watch, thesis intact" if abs(h["pl_pct"]) < h["stop_loss_pct"] else "⚠️ near stop-loss"
            lines.append(f"{h['symbol']:<8}{h['pl_pct']:+.0f}% {direction} cost  → {action}")
    else:
        lines.append("✓ No speculative positions")
    if health["speculative_over_cap"]:
        lines.append(f"⚠️ Speculative at {health['speculative_pct']:.1f}% — exceeds 8% cap")

    # Take profit
    take_profit = [s for s in signals if s["type"] == "take_profit"]
    if take_profit:
        lines.extend(["", "🟡 TAKE PROFIT CONSIDERATIONS"])
        for s in take_profit:
            lines.append(f"{s['symbol']:<8}+{s['pl_pct']:.0f}% (target: +{s['take_profit_pct']:.0f}%)  ${s['current_value']:,.0f}")

    # Stop-loss alerts
    stop_losses = [s for s in signals if s["type"] == "stop_loss"]
    if stop_losses:
        lines.extend(["", "🚨 STOP LOSS BREACHED"])
        for s in stop_losses:
            lines.append(f"{s['symbol']:<8}{s['pl_pct']:.1f}% loss  (floor: -{s['stop_loss_pct']:.0f}%)  → review thesis")

    # Pending actions
    pending = health["pending_actions"]
    if pending:
        lines.extend(["", "⚠️ PENDING ACTIONS  (exit/trim)"])
        for h in pending:
            lines.append(f"{h['symbol']:<8}[{h['status'].upper()}] {h['pl_pct']:+.1f}%  {h['notes'][:50]}")

    # Correction threshold reminder
    lines.extend([
        "",
        "⚡ CORRECTION ALERT THRESHOLD",
        f"Will notify immediately if S&P 500 drops > {config.get('SP500_CORRECTION_THRESHOLD', 3.0):.0f}% in one day",
    ])

    plain = "\n".join(lines)
    html = _build_digest_html(lines, date_str)
    return subject, plain, html


def _get_status(holdings: list[dict], symbol: str) -> str:
    for h in holdings:
        if h["symbol"] == symbol:
            return h["status"]
    return "active"


def _get_note(holdings: list[dict], symbol: str) -> str:
    for h in holdings:
        if h["symbol"] == symbol and "inflation" in h.get("notes", "").lower():
            return " — inflation hedge"
    return ""


def _build_digest_html(lines: list[str], date_str: str) -> str:
    html_lines = [
        '<!DOCTYPE html><html><head><meta charset="utf-8"></head>',
        '<body style="font-family:Menlo,Consolas,\'Courier New\',monospace;font-size:13px;'
        'line-height:1.5;color:#222;max-width:680px;margin:0 auto;padding:16px;">',
    ]
    for line in lines:
        if not line.strip():
            html_lines.append("<br>")
            continue
        escaped = _h(line)
        if line.startswith("📊") or line.startswith("🚨"):
            html_lines.append(f'<div style="font-size:16px;font-weight:bold;margin-top:12px;">{escaped}</div>')
        elif line.startswith(("💼", "⚖️", "🛒", "🔄", "📌", "🟡", "⚠️", "⚡")):
            html_lines.append(f'<div style="font-size:14px;font-weight:bold;margin-top:16px;'
                              f'border-bottom:1px solid #ddd;padding-bottom:4px;">{escaped}</div>')
        elif line.startswith("✓"):
            html_lines.append(f'<div style="color:#888;padding-left:8px;">{escaped}</div>')
        else:
            html_lines.append(f'<div style="padding-left:8px;white-space:pre;">{escaped}</div>')

    html_lines.append("</body></html>")
    return "\n".join(html_lines)


def format_correction_alert(
    change_pct: float, cash: float, opportunities: list[dict],
) -> tuple[str, str, str]:
    """Returns (subject, plain_text, html)."""
    subject = f"🔴 Market Correction Alert — SPY {change_pct:+.1f}%"

    lines = [
        "🔴 MARKET CORRECTION ALERT",
        f"S&P 500 (SPY) down {change_pct:.1f}% today",
        "",
        f"💵 Cash available to deploy: ${cash:,.0f}",
        "",
        "Top underweight positions with headroom:",
    ]
    for opp in opportunities[:5]:
        lines.append(f"  • {opp['symbol']}  {opp.get('pct_below_ma', 0):.1f}% below 50d MA  ${opp.get('headroom_amount', 0):,.0f} headroom")
    if not opportunities:
        lines.append("  No positions currently below threshold")
    lines.extend(["", "This is an opportunistic moment — your decision.", "No action required."])

    plain = "\n".join(lines)
    html = _build_digest_html(lines, "")
    return subject, plain, html


def format_stop_loss_alert(signal: dict) -> tuple[str, str, str]:
    """Returns (subject, plain_text, html)."""
    subject = f"🚨 Stop Loss Alert — {signal['symbol']} ({signal['pl_pct']:.1f}%)"

    lines = [
        f"🚨 STOP LOSS ALERT — {signal['symbol']}",
        signal["company_name"],
        "",
        f"Cost basis:   ${signal['avg_cost']:.2f} per share",
        f"Current:      ${signal['current_price']:.2f} per share",
        f"Loss:         {signal['pl_pct']:.1f}%  (${signal['pl_dollar']:,.0f} total)",
        f"Your floor:   -{signal['stop_loss_pct']:.0f}%",
        "",
        f"Category: {signal['category']} | Status: {signal['status']}",
        f"Thesis: {signal['notes']}",
        "",
        "Review thesis carefully before acting.",
        "No action required — your decision.",
    ]

    plain = "\n".join(lines)
    html = _build_digest_html(lines, "")
    return subject, plain, html
