"""
Scoop — Email delivery via Gmail SMTP

Uses a Gmail account with an App Password to send digests.
No external dependencies beyond the standard library.

Setup:
  1. Go to myaccount.google.com > Security > 2-Step Verification (enable it)
  2. Go to myaccount.google.com > Security > App passwords
  3. Create an app password for "Mail"
  4. Set GMAIL_ADDRESS and GMAIL_APP_PASSWORD in .env

To swap to another provider (Resend, SendGrid, SES), just change
the send_raw_email() function.
"""

from __future__ import annotations

import asyncio
import logging
import os
import smtplib
from datetime import date, timedelta
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from html import escape as html_escape

from exceptions import EmailError

logger = logging.getLogger(__name__)

GMAIL_ADDRESS = os.getenv("GMAIL_ADDRESS", "")
GMAIL_APP_PASSWORD = os.getenv("GMAIL_APP_PASSWORD", "")
GMAIL_DISPLAY_NAME = os.getenv("GMAIL_DISPLAY_NAME", "Scoop 🐶🗞️")


def send_raw_email(to: str, subject: str, html: str) -> None:
    """Send an email via Gmail SMTP. Runs synchronously."""
    msg = MIMEMultipart("alternative")
    msg["From"] = f"{GMAIL_DISPLAY_NAME} <{GMAIL_ADDRESS}>"
    msg["To"] = to
    msg["Subject"] = subject
    msg.attach(MIMEText(html, "html"))

    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(GMAIL_ADDRESS, GMAIL_APP_PASSWORD)
            server.sendmail(GMAIL_ADDRESS, to, msg.as_string())
    except smtplib.SMTPException as exc:
        raise EmailError(f"Failed to send email to {to}: {exc}") from exc


async def send_digest_email(user: dict, items: list[dict]) -> None:
    """Send a rendered digest email to a user."""
    if not GMAIL_ADDRESS or not GMAIL_APP_PASSWORD:
        logger.info("  [dry-run] Would send %d items to %s", len(items), user["email"])
        return

    html = render_digest(user, items)
    subject = f"🐶🗞️ {len(items)} signals this week"

    # Run SMTP in a thread so we don't block the event loop
    loop = asyncio.get_event_loop()
    await loop.run_in_executor(None, send_raw_email, user["email"], subject, html)


async def send_welcome_email(email: str) -> None:
    """Send a short welcome email after signup."""
    if not GMAIL_ADDRESS or not GMAIL_APP_PASSWORD:
        logger.info("  [dry-run] Would send welcome to %s", email)
        return

    name = html_escape(email.split("@")[0].title())
    html = f"""<!DOCTYPE html><html><head><meta charset="UTF-8"></head>
<body style="margin:0; padding:0; background:#f8fafc; font-family:-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;">
<table width="100%" cellpadding="0" cellspacing="0" style="background:#f8fafc;">
<tr><td align="center" style="padding:32px 16px;">
<table width="560" cellpadding="0" cellspacing="0" style="background:#fff; border-radius:12px; overflow:hidden;">
  <tr><td style="padding:32px;">
    <p style="margin:0 0 16px; font-size:24px;">🐶🗞️</p>
    <p style="margin:0 0 16px; font-size:16px; font-weight:700; color:#0f172a;">Welcome to Scoop, {name}!</p>
    <p style="margin:0 0 16px; font-size:15px; line-height:1.6; color:#475569;">
      Your first digest arrives <strong>Monday at 7am</strong>. We'll cover all the accounts you listed
      and tell you exactly why each signal matters for your deals.
    </p>
    <p style="margin:0; font-size:15px; line-height:1.6; color:#475569;">
      That's it. No login, no dashboard. Just open your email on Monday morning.
    </p>
  </td></tr>
  <tr><td style="padding:16px 32px; background:#f8fafc; border-top:1px solid #f1f5f9;">
    <p style="margin:0; font-size:13px; color:#94a3b8; text-align:center;">Reply "stop" to unsubscribe anytime.</p>
  </td></tr>
</table>
</td></tr></table>
</body></html>"""

    subject = "🐶🗞️ Welcome to Scoop!"
    loop = asyncio.get_event_loop()
    await loop.run_in_executor(None, send_raw_email, email, subject, html)


def _render_source_links(sources: list) -> str:
    """Render source URLs as clickable links."""
    if not sources:
        return ""
    links = []
    for url in sources[:3]:
        if not isinstance(url, str):
            continue
        # Extract domain for display
        display = html_escape(url)
        try:
            domain = url.split("//")[-1].split("/")[0].replace("www.", "")
        except Exception:
            domain = display[:40]
        links.append(
            f'<a href="{display}" style="color:#6366f1; text-decoration:none; '
            f'font-size:12px;">{html_escape(domain)}</a>'
        )
    if not links:
        return ""
    return (
        '<p style="margin:12px 0 0; padding:8px 0 0; '
        'border-top:1px solid #f1f5f9; font-size:12px; color:#94a3b8;">'
        "Source: " + " · ".join(links) + "</p>"
    )


def render_digest(user: dict, items: list[dict]) -> str:
    """Build the HTML digest email."""
    today = date.today()
    next_monday = today + timedelta(days=(7 - today.weekday()) % 7 or 7)

    tag_colors: dict[str, dict[str, str]] = {
        "red": {"bg": "#fef2f2", "fg": "#dc2626", "border": "#fecaca"},
        "green": {"bg": "#ecfdf5", "fg": "#059669", "border": "#a7f3d0"},
        "amber": {"bg": "#fffbeb", "fg": "#d97706", "border": "#fde68a"},
        "blue": {"bg": "#eff6ff", "fg": "#2563eb", "border": "#bfdbfe"},
    }

    urgency_styles: dict[str, dict[str, str]] = {
        "IMMEDIATE": {"bg": "#dc2626", "fg": "#ffffff", "label": "ACT NOW"},
        "THIS_WEEK": {"bg": "#f59e0b", "fg": "#ffffff", "label": "THIS WEEK"},
        "THIS_MONTH": {"bg": "#6366f1", "fg": "#ffffff", "label": "THIS MONTH"},
        "THIS_QUARTER": {"bg": "#94a3b8", "fg": "#ffffff", "label": "THIS QUARTER"},
    }

    # ── Signal cards ──
    items_html = ""
    for i, item in enumerate(items):
        colors = tag_colors.get(item.get("tag_color", "blue"), tag_colors["blue"])
        is_risk = item.get("risk_or_opportunity", "") in ("risk", "both")
        urgency_key = item.get("urgency", "THIS_QUARTER")
        urgency = urgency_styles.get(urgency_key, urgency_styles["THIS_QUARTER"])

        # Escape all user/API-sourced strings
        tag = html_escape(item.get("tag", ""))
        company = html_escape(item.get("company", ""))
        headline = html_escape(item.get("headline", ""))
        why_text = html_escape(item.get("why", ""))
        window = html_escape(item.get("window", ""))
        action = html_escape(item.get("suggested_action", ""))
        opener = html_escape(item.get("opening_line", ""))
        signal_date = html_escape(item.get("date", ""))
        sources = item.get("sources", [])

        # Why block with timing window on its own line
        why_block = why_text
        if window:
            why_block += f'<br><span style="color:#6366f1; font-weight:600; font-size:12px;">&#9200; {window}</span>'

        # Card border and background for risk signals
        card_bg = "#fff5f5" if is_risk else "#ffffff"
        card_border = colors["fg"]

        # Urgency badge only
        badge_html = (
            f'<span style="display:inline; padding:2px 8px; border-radius:3px; '
            f'background:{urgency["bg"]}; color:{urgency["fg"]}; '
            f'font-size:10px; font-weight:700; letter-spacing:0.05em;">{urgency["label"]}</span>'
        )

        # Header line: COMPANY · Tag · Date
        date_html = ""
        if signal_date:
            date_html = f' <span style="color:#94a3b8; font-weight:400;">· {signal_date}</span>'

        # "Scoop recommends" block: action + opening line bundled
        recommend_html = ""
        if action or opener:
            inner = ""
            if action:
                inner += (
                    f'<p style="margin:0; font-size:13px; line-height:1.5; '
                    f'color:#4f46e5; font-weight:600;">&#10140; {action}</p>'
                )
            if opener:
                inner += (
                    f'<p style="margin:{"8" if action else "0"}px 0 0; font-size:13px; '
                    f'font-style:italic; line-height:1.5; color:#334155;">'
                    f'&ldquo;{opener}&rdquo;</p>'
                )
            recommend_html = (
                f'<table cellpadding="0" cellspacing="0" width="100%" style="margin:14px 0 0;">'
                f'<tr><td style="background:#f8fafc; border-radius:6px; padding:12px 16px; '
                f'border-left:3px solid #c7d2fe;">'
                f'<p style="margin:0 0 6px; font-size:10px; font-weight:700; color:#6366f1; '
                f'text-transform:uppercase; letter-spacing:0.06em;">Scoop recommends</p>'
                f'{inner}'
                f'</td></tr></table>'
            )

        # Source links
        source_html = _render_source_links(sources)

        items_html += f"""
        <tr><td style="padding:0 24px;">
          <table cellpadding="0" cellspacing="0" width="100%" style="margin:14px 0; border:1px solid #e2e8f0; border-radius:8px; border-left:4px solid {card_border}; background:{card_bg};">
            <tr><td style="padding:18px 20px;">

              <!-- Company · Tag · Date + Urgency -->
              <table cellpadding="0" cellspacing="0" width="100%">
                <tr>
                  <td>
                    <span style="font-size:13px; color:#64748b; text-transform:uppercase; letter-spacing:0.05em; font-weight:700;">{company}</span>
                    <span style="display:inline; margin-left:6px; padding:1px 8px; border-radius:100px; background:{colors['bg']}; color:{colors['fg']}; font-size:11px; font-weight:700;">{tag}</span>{date_html}
                  </td>
                  <td style="text-align:right;">{badge_html}</td>
                </tr>
              </table>

              <!-- Headline -->
              <p style="margin:10px 0 0; font-size:15px; font-weight:700; line-height:1.4; color:#0f172a;">{headline}</p>

              <!-- Why this matters -->
              <p style="margin:10px 0 0; font-size:13px; line-height:1.6; color:#475569;">{why_block}</p>

              <!-- Scoop recommends -->
              {recommend_html}

              <!-- Sources -->
              {source_html}

            </td></tr>
          </table>
        </td></tr>"""

    company_count = len(user.get("companies", []))
    user_email = user.get("email", "")
    user_name = html_escape(user_email.split("@")[0].title()) if user_email else "there"
    risk_count = sum(1 for i in items if i.get("risk_or_opportunity", "") in ("risk", "both"))

    # Unsubscribe + tracking URLs
    from urls import build_unsubscribe_url, build_tracking_url
    unsub_url = html_escape(build_unsubscribe_url(user_email))
    track_url = html_escape(build_tracking_url(user.get("id", "")))

    # Forward mailto
    fwd_subject = html_escape(f"Check out Scoop - account intelligence for sales")
    fwd_body = html_escape("I've been using Scoop to get weekly signals on my accounts. Free to try: https://noptus.github.io/Scoop/")

    return f"""<!DOCTYPE html><html><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0"></head>
<body style="margin:0; padding:0; background:#f4f4f5; font-family:-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;">
<table width="100%" cellpadding="0" cellspacing="0" style="background:#f4f4f5;">
<tr><td align="center" style="padding:24px 12px;">
<table width="100%" cellpadding="0" cellspacing="0" style="max-width:600px; background:#ffffff; border-radius:12px; overflow:hidden; box-shadow:0 1px 3px rgba(0,0,0,0.08);">

  <!-- Header -->
  <tr><td style="padding:20px 24px; background:#0f172a;">
    <table cellpadding="0" cellspacing="0" width="100%">
      <tr>
        <td><span style="font-size:20px; vertical-align:middle;">&#128054;&#128240;</span> <span style="font-size:18px; font-weight:700; color:#ffffff; vertical-align:middle;">Scoop</span> <span style="font-size:14px; color:#94a3b8; vertical-align:middle;">Weekly Intel</span></td>
        <td style="text-align:right;"><span style="font-size:13px; color:#94a3b8;">{today.strftime('%b %d, %Y')}</span></td>
      </tr>
    </table>
  </td></tr>

  <!-- Greeting -->
  <tr><td style="padding:20px 24px 8px;">
    <p style="margin:0; font-size:14px; color:#475569;">Hi {user_name}, {len(items)} signal{"s" if len(items) != 1 else ""} across {company_count} account{"s" if company_count != 1 else ""} this week.{f" {risk_count} need attention." if risk_count else ""}</p>
  </td></tr>

  <!-- Signals -->
  {items_html}

  <!-- Forward CTA -->
  <tr><td style="padding:16px 24px;">
    <p style="margin:0; font-size:13px; color:#64748b; text-align:center;">
      Know a colleague who'd find this useful?
      <a href="mailto:?subject={fwd_subject}&amp;body={fwd_body}" style="color:#4f46e5; font-weight:600; text-decoration:none;">Share Scoop</a>
    </p>
  </td></tr>

  <!-- Footer -->
  <tr><td style="padding:16px 24px; background:#f8fafc; border-top:1px solid #e2e8f0;">
    <table cellpadding="0" cellspacing="0" width="100%">
      <tr>
        <td style="font-size:12px; color:#94a3b8;">Next digest: {next_monday.strftime('%b %d')}</td>
        <td style="text-align:right; font-size:12px; color:#94a3b8;">Tracking {company_count} accounts</td>
      </tr>
    </table>
    <p style="margin:8px 0 0; font-size:11px; color:#cbd5e1; text-align:center;">
      <a href="{unsub_url}" style="color:#cbd5e1; text-decoration:underline;">Unsubscribe</a> &middot; Powered by Scoop
    </p>
  </td></tr>

</table>
</td></tr></table>
<!-- Open tracking -->
<img src="{track_url}" width="1" height="1" alt="" style="display:none;">
</body></html>"""


async def send_preview_email(user: dict, items: list[dict]) -> None:
    """Send a preview email with the first signal after signup."""
    if not GMAIL_ADDRESS or not GMAIL_APP_PASSWORD:
        logger.info("  [dry-run] Would send preview to %s", user["email"])
        return

    html = render_digest(user, items)
    subject = f"Here's your first signal"

    loop = asyncio.get_event_loop()
    await loop.run_in_executor(None, send_raw_email, user["email"], subject, html)
