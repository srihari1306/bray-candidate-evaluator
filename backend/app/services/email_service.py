"""
Gmail SMTP Email Service for interview invitations.
Sends interview scheduling emails using smtplib when MOCK_EMAIL=false.
Otherwise, falls back to logging the invitation to the console.
"""

import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from datetime import datetime
from app.config import get_settings
from app.utils.logger import get_logger

logger = get_logger("services.email_service")


def _render_email_html(candidate_name: str, scheduled_time: str, teams_link: str, session_id: str) -> str:
    """Render a polished HTML email template for the interview invitation."""
    try:
        dt = datetime.fromisoformat(scheduled_time.replace("Z", "+00:00"))
        formatted_time = dt.strftime("%A, %B %d, %Y at %I:%M %p %Z")
    except Exception:
        formatted_time = scheduled_time

    return f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
    </head>
    <body style="margin:0;padding:0;background:#f4f6f9;font-family:'Segoe UI',Tahoma,Geneva,Verdana,sans-serif;">
        <table width="100%" cellpadding="0" cellspacing="0" style="background:#f4f6f9;padding:40px 0;">
            <tr>
                <td align="center">
                    <table width="600" cellpadding="0" cellspacing="0" style="background:#ffffff;border-radius:12px;overflow:hidden;box-shadow:0 4px 24px rgba(0,0,0,0.08);">
                        <!-- Header -->
                        <tr>
                            <td style="background:linear-gradient(135deg,#1F4E79 0%,#2980b9 100%);padding:32px 40px;text-align:center;">
                                <h1 style="color:#ffffff;margin:0;font-size:24px;font-weight:600;">Interview Invitation</h1>
                            </td>
                        </tr>
                        <!-- Body -->
                        <tr>
                            <td style="padding:40px;">
                                <p style="color:#333;font-size:16px;line-height:1.6;margin:0 0 20px;">
                                    Dear <strong>{candidate_name}</strong>,
                                </p>
                                <p style="color:#555;font-size:15px;line-height:1.6;margin:0 0 20px;">
                                    You have been invited to an AI-powered interview. Please join at the scheduled time below.
                                </p>

                                <!-- Schedule Box -->
                                <table width="100%" cellpadding="0" cellspacing="0" style="background:#f0f7ff;border-radius:8px;border-left:4px solid #1F4E79;margin:24px 0;">
                                    <tr>
                                        <td style="padding:20px 24px;">
                                            <p style="color:#1F4E79;font-size:14px;font-weight:600;margin:0 0 4px;text-transform:uppercase;letter-spacing:0.5px;">
                                                Scheduled Time
                                            </p>
                                            <p style="color:#333;font-size:18px;font-weight:700;margin:0;">
                                                {formatted_time}
                                            </p>
                                        </td>
                                    </tr>
                                </table>

                                <!-- Join Button -->
                                <table width="100%" cellpadding="0" cellspacing="0" style="margin:28px 0;">
                                    <tr>
                                        <td align="center">
                                            <a href="{teams_link}" style="display:inline-block;background:linear-gradient(135deg,#1F4E79,#2980b9);color:#fff;text-decoration:none;padding:14px 40px;border-radius:8px;font-size:16px;font-weight:600;letter-spacing:0.3px;">
                                                Join Interview Meeting
                                            </a>
                                        </td>
                                    </tr>
                                </table>

                                <!-- Instructions -->
                                <h3 style="color:#333;font-size:15px;font-weight:600;margin:28px 0 12px;">Before you join:</h3>
                                <ul style="color:#555;font-size:14px;line-height:2;padding-left:20px;margin:0;">
                                    <li>Ensure your <strong>camera</strong> is working</li>
                                    <li>Ensure your <strong>microphone</strong> is working</li>
                                    <li>Be in a <strong>quiet environment</strong></li>
                                    <li>Use <strong>Google Chrome</strong> or <strong>Microsoft Edge</strong> for the best experience</li>
                                </ul>

                                <!-- AI Note -->
                                <table width="100%" cellpadding="0" cellspacing="0" style="background:#fef3cd;border-radius:8px;margin:24px 0;">
                                    <tr>
                                        <td style="padding:16px 20px;">
                                            <p style="color:#856404;font-size:13px;margin:0;line-height:1.5;">
                                                ⚡ <strong>Note:</strong> This interview is conducted by an AI system. You will be asked 3 questions and your responses will be recorded for evaluation.
                                            </p>
                                        </td>
                                    </tr>
                                </table>

                                <p style="color:#777;font-size:12px;margin:20px 0 0 0;">
                                    Session Reference ID: <code style="background:#eef;padding:2px 6px;border-radius:4px;">{session_id}</code>
                                </p>
                            </td>
                        </tr>
                        <!-- Footer -->
                        <tr>
                            <td style="background:#f8f9fa;padding:20px 40px;text-align:center;border-top:1px solid #e9ecef;">
                                <p style="color:#999;font-size:12px;margin:0;">
                                    This is an automated message. Please do not reply to this email.
                                </p>
                            </td>
                        </tr>
                    </table>
                </td>
            </tr>
        </table>
    </body>
    </html>
    """


async def send_interview_email(
    candidate_name: str,
    candidate_email: str,
    scheduled_time: str,
    teams_link: str,
    session_id: str,
) -> bool:
    """
    Send an interview invitation email to the candidate.
    Uses smtplib for Gmail SMTP when MOCK_EMAIL=false, else logs it.
    """
    settings = get_settings()

    # Build the Teams link with session_id parameter
    separator = "&" if "?" in teams_link else "?"
    teams_link_with_session = f"{teams_link}{separator}context=%7B%22session_id%22%3A%22{session_id}%22%7D"

    # Render the HTML email
    html_content = _render_email_html(
        candidate_name=candidate_name,
        scheduled_time=scheduled_time,
        teams_link=teams_link_with_session,
        session_id=session_id,
    )

    # Format plain text content for email clients that don't support HTML
    try:
        dt = datetime.fromisoformat(scheduled_time.replace("Z", "+00:00"))
        formatted_time = dt.strftime("%A, %B %d, %Y at %I:%M %p %Z")
    except Exception:
        formatted_time = scheduled_time

    text_content = (
        f"Dear {candidate_name},\n\n"
        f"You have been invited to an AI-powered interview. Please join at the scheduled time:\n"
        f"{formatted_time}\n\n"
        f"Join the interview using this Teams meeting link:\n"
        f"{teams_link_with_session}\n\n"
        f"Before you join:\n"
        f"- Ensure your camera is working\n"
        f"- Ensure your microphone is working\n"
        f"- Be in a quiet environment\n"
        f"- Use Google Chrome or Microsoft Edge\n\n"
        f"Note: This interview is conducted by an AI system. You will be asked 3 questions and your responses will be recorded for evaluation.\n\n"
        f"Session Reference ID: {session_id}\n"
    )

    # Log the email details for reference
    logger.info(f"──── Interview Email ────")
    logger.info(f"  To: {candidate_name} <{candidate_email}>")
    logger.info(f"  Subject: Interview Invitation")
    logger.info(f"  Scheduled: {scheduled_time}")
    logger.info(f"  Session ID: {session_id}")
    logger.info(f"  Teams Link: {teams_link_with_session}")
    logger.info(f"─────────────────────────")

    if settings.MOCK_EMAIL:
        logger.info("MOCK_EMAIL is True. Email logged to console only.")
        logger.info(f"[MOCK EMAIL] HTML content length: {len(html_content)} characters")
        return True

    if not settings.GMAIL_USER or not settings.GMAIL_APP_PASSWORD:
        logger.error("✗ Gmail credentials not configured. Cannot send email when MOCK_EMAIL is False.")
        return False

    # Send via SMTP
    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = "Interview Invitation — Smart Interviewer"
        msg["From"] = f"Smart Interviewer <{settings.GMAIL_USER}>"
        msg["To"] = candidate_email

        # Attach text and HTML parts
        msg.attach(MIMEText(text_content, "plain"))
        msg.attach(MIMEText(html_content, "html"))

        # Connect to Gmail SMTP server
        logger.info(f"Connecting to Gmail SMTP server (smtp.gmail.com:587) using user: {settings.GMAIL_USER}...")
        
        # Run blocking SMTP calls in executor
        import asyncio
        import ssl
        def _send():
            context = ssl.create_default_context()
            with smtplib.SMTP("smtp.gmail.com", 587, timeout=15) as server:
                server.ehlo()
                server.starttls(context=context)
                server.ehlo()
                server.login(settings.GMAIL_USER, settings.GMAIL_APP_PASSWORD)
                server.sendmail(settings.GMAIL_USER, candidate_email, msg.as_string())
        
        loop = asyncio.get_running_loop()
        await loop.run_in_executor(None, _send)
        
        logger.info(f"✓ Email sent successfully via Gmail SMTP to {candidate_email}")
        return True

    except Exception as e:
        logger.error(f"✗ Gmail SMTP send failed: {e}", exc_info=True)
        logger.info("Email content was logged above for manual reference.")
        return False
