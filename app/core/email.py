"""Email service using Resend for sending verification codes."""
import resend
from typing import Optional

from app.core.config import get_settings

settings = get_settings()


def send_verification_email(email: str, code: str) -> bool:
    """Send verification code email using Resend.

    Args:
        email: Recipient email address
        code: 6-digit verification code

    Returns:
        True if email was sent successfully, False otherwise
    """
    if not settings.RESEND_API_KEY:
        print(f"[DEBUG] Resend API key not configured. Code for {email}: {code}")
        return False

    resend.api_key = settings.RESEND_API_KEY

    try:
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <style>
                body {{
                    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                    background-color: #f5f5f5;
                    margin: 0;
                    padding: 20px;
                    line-height: 1.6;
                }}
                .container {{
                    max-width: 560px;
                    margin: 0 auto;
                    background: white;
                    border-radius: 16px;
                    padding: 40px 48px;
                    box-shadow: 0 4px 6px rgba(0,0,0,0.1);
                }}
                .logo {{
                    font-size: 28px;
                    font-weight: bold;
                    color: #8B5CF6;
                    margin-bottom: 32px;
                }}
                .greeting {{
                    color: #1f2937;
                    font-size: 16px;
                    margin-bottom: 24px;
                }}
                .intro {{
                    color: #4b5563;
                    font-size: 15px;
                    margin-bottom: 24px;
                }}
                .code-section {{
                    margin: 28px 0;
                }}
                .code-label {{
                    color: #6b7280;
                    font-size: 14px;
                    margin-bottom: 12px;
                }}
                .code-box {{
                    background: linear-gradient(135deg, #8B5CF6 0%, #EC4899 100%);
                    border-radius: 12px;
                    padding: 20px;
                    text-align: center;
                    display: inline-block;
                }}
                .code {{
                    font-size: 32px;
                    font-weight: bold;
                    color: white;
                    letter-spacing: 6px;
                    font-family: 'SF Mono', Monaco, 'Courier New', monospace;
                }}
                .expire {{
                    color: #9ca3af;
                    font-size: 13px;
                    margin-top: 12px;
                }}
                .message {{
                    color: #4b5563;
                    font-size: 15px;
                    margin: 24px 0;
                }}
                .ps {{
                    color: #374151;
                    font-size: 14px;
                    margin-top: 28px;
                    padding-top: 20px;
                    border-top: 1px solid #e5e7eb;
                }}
                .ps strong {{
                    color: #1f2937;
                }}
                .signature {{
                    color: #374151;
                    font-size: 15px;
                    margin-top: 28px;
                }}
                .footer {{
                    color: #9ca3af;
                    font-size: 12px;
                    margin-top: 32px;
                    padding-top: 20px;
                    border-top: 1px solid #e5e7eb;
                }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="logo">🐱 Meowart</div>
                
                <p class="greeting">Hey,</p>
                
                <p class="intro">
                    我是 Jesse，Meowart 的创始人。非常高兴你决定加入我们！
                </p>
                
                <p class="message">
                    我们正在打造一款能让你与 AI 设计师进行对话的产品。
                    我们希望它是有趣的、真实的、<em>就是好用</em>。
                </p>
                
                <div class="code-section">
                    <p class="code-label">这是你的验证码：</p>
                    <div class="code-box">
                        <span class="code">{code}</span>
                    </div>
                    <p class="expire">验证码将在 {settings.VERIFICATION_CODE_EXPIRE_MINUTES} 分钟后失效</p>
                </div>
                
                <div class="ps">
                    <p><strong>P.S. 为什么想试试 Meowart？</strong></p>
                    <p>直接回复这封邮件告诉我，我会亲自回复每一封邮件。</p>
                </div>
                
                <div class="signature">
                    <p>Cheers,<br>Jesse</p>
                </div>
                
                <div class="footer">
                    如果你没有注册 Meowart 账号，请忽略此邮件。<br>
                    © 2026 Meowart. All rights reserved.
                </div>
            </div>
        </body>
        </html>
        """

        params: resend.Emails.SendParams = {
            "from": f"Meowart <{settings.RESEND_FROM_EMAIL}>",
            "to": [email],
            "subject": "欢迎加入 Meowart！🐱",
            "html": html_content,
        }

        resend.Emails.send(params)
        print(f"[INFO] Verification email sent to {email}")
        return True

    except Exception as e:
        print(f"[ERROR] Failed to send verification email to {email}: {e}")
        return False
