"""
Email output driver for sending emails via SMTP.
"""

import os
import json
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
from typing import Dict, Any
from .base import BaseDriver, DriverResponse


class EmailOutputDriver(BaseDriver):
    type = "email_output"

    def execute(self, node: Dict[str, Any], context: Dict[str, Any]) -> DriverResponse:
        """Send email via SMTP."""
        # Get configuration
        smtp_server = node.get("data", {}).get("smtp_server", "")
        smtp_port = int(node.get("data", {}).get("smtp_port", 587))
        use_tls = node.get("data", {}).get("use_tls", True)
        username = node.get("data", {}).get("username", "") or os.getenv("SMTP_USERNAME", "")
        password = node.get("data", {}).get("password", "") or os.getenv("SMTP_PASSWORD", "")

        from_email = node.get("data", {}).get("from_email", "")
        to_email = node.get("data", {}).get("to_email", "")
        cc_email = node.get("data", {}).get("cc_email", "")
        bcc_email = node.get("data", {}).get("bcc_email", "")
        subject = node.get("data", {}).get("subject", "")
        body = node.get("data", {}).get("body", "")
        html = node.get("data", {}).get("html", False)

        # Support {input} placeholder
        input_data = context.get("input", "")
        if isinstance(input_data, (dict, list)):
            input_str = json.dumps(input_data, indent=2)
        else:
            input_str = str(input_data)

        subject = subject.replace("{input}", input_str) if subject else ""
        body = body.replace("{input}", input_str) if body else input_str

        # Validate required fields
        if not smtp_server:
            return DriverResponse({
                "status": "error",
                "error": "SMTP server is required"
            })

        if not from_email:
            return DriverResponse({
                "status": "error",
                "error": "From email is required"
            })

        if not to_email:
            return DriverResponse({
                "status": "error",
                "error": "To email is required"
            })

        try:
            # Create message
            msg = MIMEMultipart()
            msg['From'] = from_email
            msg['To'] = to_email
            msg['Subject'] = subject

            if cc_email:
                msg['Cc'] = cc_email
            if bcc_email:
                msg['Bcc'] = bcc_email

            # Attach body
            if html:
                msg.attach(MIMEText(body, 'html'))
            else:
                msg.attach(MIMEText(body, 'plain'))

            # Collect all recipients
            recipients = [to_email]
            if cc_email:
                recipients.extend([email.strip() for email in cc_email.split(',')])
            if bcc_email:
                recipients.extend([email.strip() for email in bcc_email.split(',')])

            # Connect to SMTP server
            if use_tls:
                server = smtplib.SMTP(smtp_server, smtp_port)
                server.starttls()
            else:
                server = smtplib.SMTP_SSL(smtp_server, smtp_port)

            # Login if credentials provided
            if username and password:
                server.login(username, password)

            # Send email
            server.send_message(msg)
            server.quit()

            return DriverResponse({
                "status": "ok",
                "output": f"Email sent to {to_email}",
                "recipients": recipients,
                "subject": subject,
            })

        except smtplib.SMTPAuthenticationError as e:
            return DriverResponse({
                "status": "error",
                "error": f"SMTP authentication failed: {str(e)}"
            })
        except smtplib.SMTPException as e:
            return DriverResponse({
                "status": "error",
                "error": f"SMTP error: {str(e)}"
            })
        except Exception as e:
            return DriverResponse({
                "status": "error",
                "error": f"Email send failed: {str(e)}"
            })
