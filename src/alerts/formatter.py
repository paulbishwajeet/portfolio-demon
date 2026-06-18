from src.utils.date_utils import now_et


def format_weekly_digest(holdings: list[dict], config: dict, breakdown: dict, health: dict, signals: list[dict]) -> str:
    date_str = now_et().strftime("%B %d, %Y")
    owner = config.get("OWNER_NAME", "Portfolio Owner")

    # Band status
    if health["band_breach"]:
        band_emoji = "⚠️"
        band_text = health["band_status"].replace("_", " ").title()
    else:
        band_emoji = "✅"
        band_text = "Within target band"

    lines = [
        "\U0001f4ca *PORTFOLIO DEMON — WEEKLY DIGEST*",
        f"{date_str} | {owner}",
        "━" * 24,
        "",
        "\U0001f4bc *PORTFOLIO HEALTH*",
        f"Total Value:       ${breakdown['total_value']:>12,.0f}",
        f"  Cash (SPAXX):   ${breakdown['cash']:>12,.0f}  ({breakdown['cash_pct']:.1f}%)",
        f"  Core Funds:     ${breakdown['fund_value']:>12,.0f}  ({breakdown['fund_pct']:.1f}%)",
        f"  Equities:       ${breakdown['equity_value']:>12,.0f}  ({breakdown['equity_pct']:.1f}%)",
        f"Overall P&L:       ${breakdown['total_pl']:>+12,.0f}  ({breakdown['total_pl_pct']:+.1f}%)",
        f"80/20 Status:      {band_emoji} {band_text}",
        f"Business Cycle:    {health['cycle_phase']}",
    ]

    # Deployment opportunities
    deployment = [s for s in signals if s["type"] == "deployment_opportunity"]
    lines.extend(["", "━" * 24, "\U0001f6d2 *DEPLOYMENT OPPORTUNITIES*", "(Positions >7% below 50d MA with remaining headroom)"])
    if deployment:
        for s in deployment[:10]:
            lines.append(f"\U0001f7e2 *{s['symbol']}* — {s['pct_below_ma']:.1f}% below 50d MA")
            lines.append(f"   Headroom: ${s['headroom_amount']:,.0f} | Weight: {s['current_weight']:.1f}% (plan: {s['planned_weight']:.1f}%)")
            lines.append(f"   Price: ${s['current_price']:.2f} | Priority: {s['priority_score']:.0f}")
    else:
        lines.append("✓ No qualifying dips this week")

    # Rotation watch
    rotation = [s for s in signals if s["type"] == "rotation"]
    lines.extend(["", "━" * 24, "\U0001f504 *SECTOR ROTATION WATCH*", f"Cycle: {health['cycle_phase']}"])
    if rotation:
        for s in rotation:
            lines.append(s["message"])
            if s["reduce_symbols"]:
                lines.append("Reduce:")
                for r in s["reduce_symbols"][:5]:
                    lines.append(f"  • {r['symbol']} (${r['value']:,.0f}) — {r['category']}")
            if s["favor_symbols"]:
                lines.append("Favor:")
                for f in s["favor_symbols"][:5]:
                    lines.append(f"  • {f['symbol']} — ${f['headroom']:,.0f} headroom")
    else:
        lines.append("✓ No rotation signals")

    # Speculative watchlist
    spec_holdings = [h for h in holdings if h["category"] == "speculative" and h["deployed_shares"] > 0]
    lines.extend(["", "━" * 24, "\U0001f4cc *SPECULATIVE WATCHLIST*", "(Wide thresholds — long-term holds)"])
    if spec_holdings:
        for h in spec_holdings:
            status_tag = f"[{h['status'].upper()}]" if h["status"] != "active" else ""
            lines.append(f"  {h['symbol']}: ${h['current_price']:.2f} ({h['pl_pct']:+.1f}%) {status_tag}")
    else:
        lines.append("✓ No speculative positions")
    if health["speculative_over_cap"]:
        lines.append(f"⚠️ Speculative at {health['speculative_pct']:.1f}% — exceeds 8% cap")

    # Take profit
    take_profit = [s for s in signals if s["type"] == "take_profit"]
    lines.extend(["", "━" * 24, "\U0001f7e1 *TAKE PROFIT CONSIDERATIONS*"])
    if take_profit:
        for s in take_profit:
            lines.append(f"  {s['symbol']}: +{s['pl_pct']:.1f}% (target: +{s['take_profit_pct']:.0f}%) — ${s['current_value']:,.0f}")
    else:
        lines.append("✓ No positions at take-profit threshold")

    # Pending actions
    pending = health["pending_actions"]
    lines.extend(["", "━" * 24, "⚠️  *PENDING ACTIONS*", "(Positions marked exit or trim)"])
    if pending:
        for h in pending:
            lines.append(f"  {h['symbol']}: [{h['status'].upper()}] {h['pl_pct']:+.1f}% — {h['notes'][:60]}")
    else:
        lines.append("✓ No pending actions")

    lines.extend(["", "━" * 24, "_Your call — no action required._"])
    return "\n".join(lines)


def format_correction_alert(change_pct: float, cash: float, opportunities: list[dict]) -> str:
    lines = [
        "\U0001f534 *MARKET CORRECTION ALERT*",
        f"S&P 500 (SPY) down *{change_pct:.1f}%* today",
        "",
        f"\U0001f4b5 *Cash available to deploy: ${cash:,.0f}*",
        "",
        "Top underweight positions with headroom:",
    ]
    for opp in opportunities[:5]:
        lines.append(f"  • *{opp['symbol']}* — {opp.get('pct_below_ma', 0):.1f}% below 50d MA, ${opp.get('headroom_amount', 0):,.0f} headroom")

    if not opportunities:
        lines.append("  No positions currently below threshold")

    lines.extend([
        "",
        "This is an opportunistic moment — your decision.",
        "_No action required._",
    ])
    return "\n".join(lines)


def format_stop_loss_alert(signal: dict) -> str:
    lines = [
        f"\U0001f6a8 *STOP LOSS ALERT — {signal['symbol']}*",
        signal["company_name"],
        "",
        f"Cost basis:   ${signal['avg_cost']:.2f} per share",
        f"Current:      ${signal['current_price']:.2f} per share",
        f"Loss:         *{signal['pl_pct']:.1f}%*  (${signal['pl_dollar']:,.0f} total)",
        f"Your floor:   -{signal['stop_loss_pct']:.0f}%",
        "",
        f"Category: {signal['category']} | Status: {signal['status']}",
        f"Thesis reminder: {signal['notes']}",
        "",
        "Review thesis carefully before acting.",
        "_No action required — your decision._",
    ]
    return "\n".join(lines)
