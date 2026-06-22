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


def _render_email_html(candidate_name: str, scheduled_time: str, interview_url: str, session_id: str) -> str:
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
                                            <a href="{interview_url}" style="display:inline-block;background:linear-gradient(135deg,#1F4E79,#2980b9);color:#fff;text-decoration:none;padding:14px 40px;border-radius:8px;font-size:16px;font-weight:600;letter-spacing:0.3px;">
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
                                                ⚡ <strong>Note:</strong> This interview is conducted by an AI system. You will be asked 3 questions. Your camera, microphone, and screen will be recorded for evaluation purposes.
                                            </p>
                                        </td>
                                    </tr>
                                </table>
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
    session_id: str,
) -> bool:
    """
    Send an interview invitation email to the candidate.
    Uses smtplib for Gmail SMTP when MOCK_EMAIL=false, else logs it.
    """
    from app.utils.security import generate_session_signature
    from datetime import timedelta
    
    settings = get_settings()

    try:
        dt = datetime.fromisoformat(scheduled_time.replace("Z", "+00:00"))
    except Exception:
        dt = datetime.utcnow()
    
    exp_time = dt + timedelta(hours=2)
    exp = str(int(exp_time.timestamp()))
    sig = generate_session_signature(session_id, exp)

    interview_url = f"{settings.INTERVIEW_PANEL_BASE_URL}?session_id={session_id}&exp={exp}&sig={sig}"

    # Render the HTML email
    html_content = _render_email_html(
        candidate_name=candidate_name,
        scheduled_time=scheduled_time,
        interview_url=interview_url,
        session_id=session_id,
    )

    # Log the email details for reference
    logger.info(f"──── Interview Email ────")
    logger.info(f"  To: {candidate_name} <{candidate_email}>")
    logger.info(f"  Subject: Interview Invitation")
    logger.info(f"  Scheduled: {scheduled_time}")
    logger.info(f"  Session ID: {session_id}")
    logger.info(f"  Interview URL: {interview_url}")
    logger.info(f"─────────────────────────")

    if settings.MOCK_EMAIL or not settings.GMAIL_USER or not settings.GMAIL_APP_PASSWORD:
        logger.warning("MOCK_EMAIL is True or Gmail credentials not configured. Email logged to console only.")
        logger.info(f"[MOCK EMAIL] HTML content length: {len(html_content)} characters")
        return True

    # Send via SMTP
    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = "Interview Invitation — Smart Interviewer"
        msg["From"] = settings.GMAIL_USER
        msg["To"] = candidate_email

        part = MIMEText(html_content, "html")
        msg.attach(part)

        # Connect to Gmail SMTP server
        logger.info(f"Connecting to Gmail SMTP server using user: {settings.GMAIL_USER}...")
        
        # Run blocking SMTP calls in executor
        import asyncio
        def _send():
            with smtplib.SMTP("smtp.gmail.com", 587) as server:
                server.starttls()
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
