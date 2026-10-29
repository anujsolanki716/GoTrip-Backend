
# import logging
# import smtplib
# import ssl
# from dataclasses import dataclass, field
# from email.message import EmailMessage
# from html import escape

# import httpx

# from app.core.config import Settings, get_settings
# from app.models import Enquiry

# logger = logging.getLogger("gotrip.email")


# @dataclass
# class OutgoingEmail:
#     to: list[str]
#     subject: str
#     text: str
#     html: str | None = None
#     reply_to: str | None = None
#     headers: dict[str, str] = field(default_factory=dict)


# BRAND_COLOR = "#F2BF45"
# BACKGROUND_COLOR = "#0B0D0F"
# CARD_COLOR = "#17191C"
# TEXT_COLOR = "#FFFFFF"
# MUTED_COLOR = "#B8B8B8"
# BORDER_COLOR = "#34363A"

# LOGO_URL = "https://your-domain.com/static/gotrip-logo.png"

# NOT_A_BOOKING = (
#     "Please note: this enquiry is not a booking or reservation. "
#     "No payment has been taken. Availability, eligibility, pricing "
#     "and rental terms are confirmed directly with the GoTrip team, "
#     "and the rental agreement, verification, payment and handover "
#     "happen offline."
# )


# def send_email(
#     message: OutgoingEmail,
#     settings: Settings | None = None,
# ) -> None:
#     settings = settings or get_settings()
#     provider = settings.email_provider

#     if provider == "disabled" or not message.to:
#         return

#     try:
#         if provider == "console":
#             logger.info(
#                 "EMAIL to=%s subject=%r\n%s",
#                 message.to,
#                 message.subject,
#                 message.text,
#             )
#         elif provider == "smtp":
#             _send_smtp(message, settings)
#         elif provider == "resend":
#             _send_resend(message, settings)
#         else:
#             logger.warning("Unknown email provider: %s", provider)

#     except Exception:
#         logger.exception(
#             "Failed to send email %r via %s",
#             message.subject,
#             provider,
#         )


# def _send_smtp(
#     message: OutgoingEmail,
#     settings: Settings,
# ) -> None:
#     msg = EmailMessage()
#     msg["From"] = settings.email_from
#     msg["To"] = ", ".join(message.to)
#     msg["Subject"] = message.subject

#     if message.reply_to:
#         msg["Reply-To"] = message.reply_to

#     for key, value in message.headers.items():
#         if key.lower() not in {"from", "to", "subject", "reply-to"}:
#             msg[key] = value

#     msg.set_content(message.text)

#     if message.html:
#         msg.add_alternative(message.html, subtype="html")

#     password = (
#         settings.smtp_password.get_secret_value()
#         if settings.smtp_password
#         else None
#     )

#     context = ssl.create_default_context()

#     if settings.smtp_use_ssl:
#         server: smtplib.SMTP = smtplib.SMTP_SSL(
#             settings.smtp_host,
#             settings.smtp_port,
#             context=context,
#             timeout=15,
#         )
#     else:
#         server = smtplib.SMTP(
#             settings.smtp_host,
#             settings.smtp_port,
#             timeout=15,
#         )

#     with server:
#         if settings.smtp_starttls and not settings.smtp_use_ssl:
#             server.starttls(context=context)

#         if settings.smtp_username and password:
#             server.login(settings.smtp_username, password)

#         server.send_message(msg)


# # def _send_resend(
# #     message: OutgoingEmail,
# #     settings: Settings,
# # ) -> None:
# #     if not settings.resend_api_key:
# #         raise RuntimeError("RESEND_API_KEY is not configured")

# #     payload: dict[str, object] = {
# #         "from": settings.email_from,
# #         "to": message.to,
# #         "subject": message.subject,
# #         "text": message.text,
# #     }

# #     if message.html:
# #         payload["html"] = message.html

# #     if message.reply_to:
# #         payload["reply_to"] = message.reply_to

# #     if message.headers:
# #         payload["headers"] = message.headers

# #     response = httpx.post(
# #         "https://api.resend.com/emails",
# #         json=payload,
# #         headers={
# #             "Authorization": (
# #                 f"Bearer {settings.resend_api_key.get_secret_value()}"
# #             )
# #         },
# #         timeout=15,
# #     )
# #     response.raise_for_status()


# def _send_resend(
#     message: OutgoingEmail,
#     settings: Settings,
# ) -> None:
#     if not settings.resend_api_key:
#         raise RuntimeError("RESEND_API_KEY is not configured")

#     payload: dict[str, object] = {
#         "from": settings.email_from,
#         "to": message.to,
#         "subject": message.subject,
#         "text": message.text,
#     }

#     if message.html:
#         payload["html"] = message.html

#     if message.reply_to:
#         payload["reply_to"] = message.reply_to

#     if message.headers:
#         payload["headers"] = message.headers

#     response = httpx.post(
#         "https://api.resend.com/emails",
#         json=payload,
#         headers={
#             "Authorization": (
#                 f"Bearer {settings.resend_api_key.get_secret_value()}"
#             ),
#         },
#         timeout=15,
#     )

#     if response.is_error:
#         logger.error(
#             "Resend rejected email: status=%s body=%s",
#             response.status_code,
#             response.text,
#         )

#     response.raise_for_status()


# def _enquiry_lines(
#     enquiry: Enquiry,
# ) -> list[tuple[str, str]]:
#     return [
#         ("Reference", enquiry.reference),
#         ("Car", enquiry.car_name_snapshot or "General enquiry"),
#         ("Name", enquiry.full_name),
#         ("Phone", enquiry.phone),
#         ("Email", enquiry.email or "-"),
#         ("Customer type", enquiry.customer_type.value),
#         ("Preferred contact", enquiry.preferred_contact.value),
#         ("Pickup date", str(enquiry.pickup_date or "-")),
#         ("Return date", str(enquiry.return_date or "-")),
#         ("Pickup area", enquiry.pickup_area or "-"),
#         ("Message", enquiry.message or "-"),
#     ]


# def _gotrip_logo(business_name: str) -> str:
#     if LOGO_URL.startswith("https://"):
#         return f"""
#         <img
#           src="{escape(LOGO_URL, quote=True)}"
#           alt="{escape(business_name, quote=True)}"
#           width="150"
#           style="display:block;width:150px;max-width:100%;
#                  height:auto;border:0;margin:0 auto;"
#         >
#         """

#     # Fallback if no logo URL is configured.
#     return f"""
#     <div style="font-family:Arial,Helvetica,sans-serif;
#                 font-size:29px;font-weight:800;color:{TEXT_COLOR};">
#       {escape(business_name)}
#     </div>
#     """


# def _gotrip_email_shell(
#     settings: Settings,
#     title: str,
#     preheader: str,
#     content: str,
# ) -> str:
#     business_name = escape(settings.business_name)
#     phone = escape(settings.business_phone)
#     logo = _gotrip_logo(settings.business_name)

#     return f"""\
# <!DOCTYPE html>
# <html lang="en">
# <head>
#   <meta charset="UTF-8">
#   <meta name="viewport" content="width=device-width,initial-scale=1.0">
#   <title>{escape(title)}</title>
# </head>

# <body style="margin:0;padding:0;background:{BACKGROUND_COLOR};
#              font-family:Arial,Helvetica,sans-serif;color:{TEXT_COLOR};">

#   <div style="display:none;max-height:0;overflow:hidden;opacity:0;
#               color:transparent;">
#     {escape(preheader)}
#   </div>

#   <table role="presentation" width="100%" cellpadding="0" cellspacing="0"
#          border="0" style="background:{BACKGROUND_COLOR};">
#     <tr>
#       <td align="center" style="padding:28px 12px;">

#         <table role="presentation" width="600" cellpadding="0" cellspacing="0"
#                border="0"
#                style="width:100%;max-width:600px;background:{CARD_COLOR};
#                       border:1px solid {BORDER_COLOR};">

#           <tr>
#             <td align="center"
#                 style="padding:28px 20px 22px;background:{BACKGROUND_COLOR};">
#                 <p style="margin:0 0 8px;font-size:16px;font-weight:700;
#                             color:{BRAND_COLOR};">
#                     {business_name}
#                 </p>

#               <p style="margin:7px 0 0;font-size:9px;letter-spacing:2px;
#                         color:{MUTED_COLOR};">
#                 SELF-DRIVE CAR RENT
#               </p>

#               <p style="margin:12px 0 0;font-size:12px;color:{MUTED_COLOR};">
#                 {escape(settings.business_tagline)}
#               </p>
#             </td>
#           </tr>

#           <tr>
#             <td style="height:4px;background:{BRAND_COLOR};
#                        line-height:4px;font-size:1px;">&nbsp;</td>
#           </tr>

#           <tr>
#             <td style="padding:30px 28px 12px;">
#               <h1 style="margin:0;font-size:25px;line-height:34px;
#                          font-weight:800;color:{TEXT_COLOR};">
#                 {escape(title)}
#               </h1>
#             </td>
#           </tr>

#           <tr>
#             <td style="padding:8px 28px 30px;color:{TEXT_COLOR};
#                        font-size:14px;line-height:23px;">
#               {content}
#             </td>
#           </tr>

#           <tr>
#             <td align="center"
#                 style="padding:23px 20px;background:{BACKGROUND_COLOR};
#                        border-top:1px solid {BORDER_COLOR};">

#               <p style="margin:0 0 8px;font-size:14px;font-weight:700;
#                         color:{BRAND_COLOR};">
#                 {business_name}
#               </p>

#               <p style="margin:0 0 8px;font-size:12px;color:{MUTED_COLOR};">
#                 Greater Noida | NCR
#               </p>

#               <p style="margin:0 0 14px;font-size:12px;color:{MUTED_COLOR};">
#                 Contact:
#                 <a href="tel:{phone}"
#                    style="color:{BRAND_COLOR};text-decoration:none;">
#                   {phone}
#                 </a>
#               </p>

#               <p style="margin:0;font-size:10px;line-height:17px;
#                         color:{MUTED_COLOR};">
#                 This is an automated email regarding your enquiry.
#                 Please retain your reference number for future communication.
#               </p>
#             </td>
#           </tr>

#         </table>
#       </td>
#     </tr>
#   </table>
# </body>
# </html>
# """


# def _detail_table(
#     lines: list[tuple[str, str]],
# ) -> str:
#     rows = []

#     for label, value in lines:
#         rows.append(f"""
#         <tr>
#           <td width="38%" valign="top"
#               style="padding:11px 12px 11px 0;border-bottom:1px solid
#                      {BORDER_COLOR};font-size:12px;color:{MUTED_COLOR};">
#             {escape(label)}
#           </td>

#           <td valign="top"
#               style="padding:11px 0;border-bottom:1px solid {BORDER_COLOR};
#                      font-size:13px;line-height:20px;color:{TEXT_COLOR};
#                      font-weight:600;overflow-wrap:anywhere;">
#             {escape(str(value))}
#           </td>
#         </tr>
#         """)

#     return f"""
#     <table role="presentation" width="100%" cellpadding="0" cellspacing="0"
#            border="0" style="border-collapse:collapse;">
#       {''.join(rows)}
#     </table>
#     """


# def _reference_card(
#     reference: str,
#     car_name: str,
# ) -> str:
#     return f"""
#     <table role="presentation" width="100%" cellpadding="0" cellspacing="0"
#            border="0"
#            style="background:{BACKGROUND_COLOR};border:1px solid {BORDER_COLOR};">
#       <tr>
#         <td style="padding:18px;">

#           <p style="margin:0 0 6px;font-size:10px;letter-spacing:1.5px;
#                     color:{MUTED_COLOR};">
#             ENQUIRY REFERENCE
#           </p>

#           <p style="margin:0;font-size:23px;line-height:31px;
#                     font-weight:800;color:{BRAND_COLOR};">
#             {escape(str(reference))}
#           </p>

#           <p style="margin:10px 0 0;font-size:13px;color:{TEXT_COLOR};">
#             <span style="color:{MUTED_COLOR};">Vehicle:</span>
#             <strong>{escape(str(car_name))}</strong>
#           </p>

#         </td>
#       </tr>
#     </table>
#     """


# def _booking_disclaimer() -> str:
#     return f"""
#     <table role="presentation" width="100%" cellpadding="0" cellspacing="0"
#            border="0"
#            style="margin-top:22px;background:#211D12;
#                   border-left:4px solid {BRAND_COLOR};">
#       <tr>
#         <td style="padding:14px 16px;font-size:12px;line-height:20px;
#                    color:#E5DCC8;">

#           <strong style="color:{BRAND_COLOR};">
#             Important: This is not a booking
#           </strong>

#           <br>
#           {escape(NOT_A_BOOKING)}

#         </td>
#       </tr>
#     </table>
#     """


# def notify_new_enquiry(enquiry: Enquiry) -> None:
#     settings = get_settings()
#     lines = _enquiry_lines(enquiry)

#     business_name = settings.business_name
#     car_name = enquiry.car_name_snapshot or "General enquiry"

#     # ------------------------------------------------------
#     # 1. ADMIN NOTIFICATION EMAIL
#     # ------------------------------------------------------

#     admin_text = (
#         f"New enquiry received on {business_name}.\n\n"
#         + "\n".join(f"{label}: {value}" for label, value in lines)
#     )

#     admin_content = f"""
#     <p style="margin:0 0 20px;color:{MUTED_COLOR};">
#       A new enquiry has been submitted through your GoTrip website.
#       Review the details below and contact the customer.
#     </p>

#     {_reference_card(enquiry.reference, car_name)}

#     <h2 style="margin:26px 0 12px;font-size:16px;color:{BRAND_COLOR};">
#       Customer enquiry details
#     </h2>

#     {_detail_table(lines)}

#     <p style="margin:22px 0 0;font-size:12px;color:{MUTED_COLOR};">
#       Use the customer's contact information to follow up on this enquiry.
#     </p>
#     """

#     admin_html = _gotrip_email_shell(
#         settings=settings,
#         title="New customer enquiry",
#         preheader=f"New GoTrip enquiry received: {enquiry.reference}",
#         content=admin_content,
#     )

#     send_email(
#         OutgoingEmail(
#             to=settings.enquiry_notification_to,
#             subject=f"New enquiry {enquiry.reference} | {car_name}",
#             text=admin_text,
#             html=admin_html,
#             reply_to=enquiry.email,
#         ),
#         settings,
#     )


#     if not settings.send_customer_acknowledgement or not enquiry.email:
#         return

#     name = (
#         enquiry.full_name.strip().split()[0]
#         if enquiry.full_name and enquiry.full_name.strip()
#         else "there"
#     )

#     preferred_contact = enquiry.preferred_contact.value

#     ack_text = (
#         f"Hi {name},\n\n"
#         f"Thank you for contacting {business_name}.\n\n"
#         f"We have received your enquiry successfully.\n"
#         f"Reference: {enquiry.reference}\n"
#         f"Vehicle: {car_name}\n\n"
#         f"Our team will contact you shortly by {preferred_contact}.\n\n"
#         f"What happens next?\n"
#         f"Our team will review your requirements and confirm availability, "
#         f"pricing and rental terms directly with you.\n\n"
#         f"{NOT_A_BOOKING}\n\n"
#         f"Phone / WhatsApp: {settings.business_phone}\n"
#         f"{business_name} - {settings.business_tagline}"
#     )

#     customer_content = f"""
#     <p style="margin:0 0 14px;font-size:15px;color:{TEXT_COLOR};">
#       Hi <strong>{escape(name)}</strong>,
#     </p>

#     <p style="margin:0 0 16px;color:{MUTED_COLOR};">
#       Thank you for choosing
#       <strong style="color:{TEXT_COLOR};">{escape(business_name)}</strong>.
#       We have received your enquiry and appreciate your interest in our
#       self-drive cars.
#     </p>

#     <p style="margin:0 0 20px;color:{MUTED_COLOR};">
#       Our team will contact you shortly via
#       <strong style="color:{BRAND_COLOR};">
#         {escape(preferred_contact)}
#       </strong>.
#     </p>

#     {_reference_card(enquiry.reference, car_name)}

#     <h2 style="margin:26px 0 8px;font-size:16px;color:{BRAND_COLOR};">
#       What happens next?
#     </h2>

#     <p style="margin:0;color:{MUTED_COLOR};">
#       We will review your requirements and discuss vehicle availability,
#       pricing and rental terms with you directly.
#     </p>

#     {_booking_disclaimer()}

#     <p style="margin:22px 0 0;color:{MUTED_COLOR};">
#       Have a question? Contact our team at
#       <strong style="color:{TEXT_COLOR};">
#         {escape(settings.business_phone)}
#       </strong>.
#     </p>

#     <p style="margin:18px 0 0;color:{TEXT_COLOR};">
#       Thank you,<br>
#       <strong style="color:{BRAND_COLOR};">
#         Team {escape(business_name)}
#       </strong>
#     </p>
#     """

#     customer_html = _gotrip_email_shell(
#         settings=settings,
#         title="We've received your enquiry!",
#         preheader=(
#             f"Thank you for contacting {business_name}. "
#             f"Reference: {enquiry.reference}"
#         ),
#         content=customer_content,
#     )

#     send_email(
#         OutgoingEmail(
#             to=[enquiry.email],
#             subject=(
#                 f"Enquiry received - {enquiry.reference} | {business_name}"
#             ),
#             text=ack_text,
#             html=customer_html,
#         ),
#         settings,
#     )





import base64
import logging
import os
import smtplib
import ssl
from dataclasses import dataclass, field
from email.message import EmailMessage
from html import escape

import httpx
from dotenv import load_dotenv
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

from app.core.config import Settings, get_settings
from app.models import Enquiry

logger = logging.getLogger("gotrip.email")

# Load backend/.env for local runs; Render environment variables still take precedence.
load_dotenv()


@dataclass
class OutgoingEmail:
    to: list[str]
    subject: str
    text: str
    html: str | None = None
    reply_to: str | None = None
    headers: dict[str, str] = field(default_factory=dict)


BRAND_COLOR = "#F2BF45"
BACKGROUND_COLOR = "#0B0D0F"
CARD_COLOR = "#17191C"
TEXT_COLOR = "#FFFFFF"
MUTED_COLOR = "#B8B8B8"
BORDER_COLOR = "#34363A"

LOGO_URL = "https://your-domain.com/static/gotrip-logo.png"

NOT_A_BOOKING = (
    "Please note: this enquiry is not a booking or reservation. "
    "No payment has been taken. Availability, eligibility, pricing "
    "and rental terms are confirmed directly with the GoTrip team, "
    "and the rental agreement, verification, payment and handover "
    "happen offline."
)


def send_email(
    message: OutgoingEmail,
    settings: Settings | None = None,
) -> None:
    settings = settings or get_settings()
    provider = settings.email_provider

    if provider == "disabled" or not message.to:
        return

    try:
        if provider == "console":
            logger.info(
                "EMAIL to=%s subject=%r\n%s",
                message.to,
                message.subject,
                message.text,
            )
        elif provider == "smtp":
            _send_smtp(message, settings)
        elif provider == "resend":
            _send_resend(message, settings)
        elif provider == "gmail_api":
            _send_gmail_api(message, settings)
        else:
            logger.warning("Unknown email provider: %s", provider)

    except Exception:
        logger.exception(
            "Failed to send email %r via %s",
            message.subject,
            provider,
        )



def _send_gmail_api(
    message: OutgoingEmail,
    settings: Settings,
) -> None:
    """Send an email through Gmail API using an OAuth refresh token.

    Required environment variables:
      GMAIL_CLIENT_ID
      GMAIL_CLIENT_SECRET
      GMAIL_REFRESH_TOKEN

    EMAIL_FROM must be the same Gmail address that was authorized,
    or a sender alias configured in that Gmail account.
    """
    client_id = os.getenv("GMAIL_CLIENT_ID")
    client_secret = os.getenv("GMAIL_CLIENT_SECRET")
    refresh_token = os.getenv("GMAIL_REFRESH_TOKEN")

    missing = [
        name for name, value in (
            ("GMAIL_CLIENT_ID", client_id),
            ("GMAIL_CLIENT_SECRET", client_secret),
            ("GMAIL_REFRESH_TOKEN", refresh_token),
        )
        if not value
    ]
    if missing:
        raise RuntimeError(
            "Missing Gmail API environment variables: " + ", ".join(missing)
        )

    credentials = Credentials(
        token=None,
        refresh_token=refresh_token,
        token_uri="https://oauth2.googleapis.com/token",
        client_id=client_id,
        client_secret=client_secret,
        scopes=["https://www.googleapis.com/auth/gmail.send"],
    )
    credentials.refresh(Request())

    msg = EmailMessage()
    msg["From"] = settings.email_from
    msg["To"] = ", ".join(message.to)
    msg["Subject"] = message.subject

    if message.reply_to:
        msg["Reply-To"] = message.reply_to

    for key, value in message.headers.items():
        if key.lower() not in {"from", "to", "subject", "reply-to"}:
            msg[key] = value

    msg.set_content(message.text)
    if message.html:
        msg.add_alternative(message.html, subtype="html")

    raw_message = base64.urlsafe_b64encode(msg.as_bytes()).decode("utf-8")

    service = build(
        "gmail",
        "v1",
        credentials=credentials,
        cache_discovery=False,
    )
    result = service.users().messages().send(
        userId="me",
        body={"raw": raw_message},
    ).execute()

    logger.info(
        "Gmail API accepted email: message_id=%s subject=%r",
        result.get("id"),
        message.subject,
    )


def _send_smtp(
    message: OutgoingEmail,
    settings: Settings,
) -> None:
    msg = EmailMessage()
    msg["From"] = settings.email_from
    msg["To"] = ", ".join(message.to)
    msg["Subject"] = message.subject

    if message.reply_to:
        msg["Reply-To"] = message.reply_to

    for key, value in message.headers.items():
        if key.lower() not in {"from", "to", "subject", "reply-to"}:
            msg[key] = value

    msg.set_content(message.text)

    if message.html:
        msg.add_alternative(message.html, subtype="html")

    password = (
        settings.smtp_password.get_secret_value()
        if settings.smtp_password
        else None
    )

    context = ssl.create_default_context()

    if settings.smtp_use_ssl:
        server: smtplib.SMTP = smtplib.SMTP_SSL(
            settings.smtp_host,
            settings.smtp_port,
            context=context,
            timeout=15,
        )
    else:
        server = smtplib.SMTP(
            settings.smtp_host,
            settings.smtp_port,
            timeout=15,
        )

    with server:
        if settings.smtp_starttls and not settings.smtp_use_ssl:
            server.starttls(context=context)

        if settings.smtp_username and password:
            server.login(settings.smtp_username, password)

        server.send_message(msg)


# def _send_resend(
#     message: OutgoingEmail,
#     settings: Settings,
# ) -> None:
#     if not settings.resend_api_key:
#         raise RuntimeError("RESEND_API_KEY is not configured")

#     payload: dict[str, object] = {
#         "from": settings.email_from,
#         "to": message.to,
#         "subject": message.subject,
#         "text": message.text,
#     }

#     if message.html:
#         payload["html"] = message.html

#     if message.reply_to:
#         payload["reply_to"] = message.reply_to

#     if message.headers:
#         payload["headers"] = message.headers

#     response = httpx.post(
#         "https://api.resend.com/emails",
#         json=payload,
#         headers={
#             "Authorization": (
#                 f"Bearer {settings.resend_api_key.get_secret_value()}"
#             )
#         },
#         timeout=15,
#     )
#     response.raise_for_status()


def _send_resend(
    message: OutgoingEmail,
    settings: Settings,
) -> None:
    if not settings.resend_api_key:
        raise RuntimeError("RESEND_API_KEY is not configured")

    payload: dict[str, object] = {
        "from": settings.email_from,
        "to": message.to,
        "subject": message.subject,
        "text": message.text,
    }

    if message.html:
        payload["html"] = message.html

    if message.reply_to:
        payload["reply_to"] = message.reply_to

    if message.headers:
        payload["headers"] = message.headers

    response = httpx.post(
        "https://api.resend.com/emails",
        json=payload,
        headers={
            "Authorization": (
                f"Bearer {settings.resend_api_key.get_secret_value()}"
            ),
        },
        timeout=15,
    )

    if response.is_error:
        logger.error(
            "Resend rejected email: status=%s body=%s",
            response.status_code,
            response.text,
        )

    response.raise_for_status()


def _enquiry_lines(
    enquiry: Enquiry,
) -> list[tuple[str, str]]:
    return [
        ("Reference", enquiry.reference),
        ("Car", enquiry.car_name_snapshot or "General enquiry"),
        ("Name", enquiry.full_name),
        ("Phone", enquiry.phone),
        ("Email", enquiry.email or "-"),
        ("Customer type", enquiry.customer_type.value),
        ("Preferred contact", enquiry.preferred_contact.value),
        ("Pickup date", str(enquiry.pickup_date or "-")),
        ("Return date", str(enquiry.return_date or "-")),
        ("Pickup area", enquiry.pickup_area or "-"),
        ("Message", enquiry.message or "-"),
    ]


def _gotrip_logo(business_name: str) -> str:
    if LOGO_URL.startswith("https://"):
        return f"""
        <img
          src="{escape(LOGO_URL, quote=True)}"
          alt="{escape(business_name, quote=True)}"
          width="150"
          style="display:block;width:150px;max-width:100%;
                 height:auto;border:0;margin:0 auto;"
        >
        """

    # Fallback if no logo URL is configured.
    return f"""
    <div style="font-family:Arial,Helvetica,sans-serif;
                font-size:29px;font-weight:800;color:{TEXT_COLOR};">
      {escape(business_name)}
    </div>
    """


def _gotrip_email_shell(
    settings: Settings,
    title: str,
    preheader: str,
    content: str,
) -> str:
    business_name = escape(settings.business_name)
    phone = escape(settings.business_phone)
    logo = _gotrip_logo(settings.business_name)

    return f"""\
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width,initial-scale=1.0">
  <title>{escape(title)}</title>
</head>

<body style="margin:0;padding:0;background:{BACKGROUND_COLOR};
             font-family:Arial,Helvetica,sans-serif;color:{TEXT_COLOR};">

  <div style="display:none;max-height:0;overflow:hidden;opacity:0;
              color:transparent;">
    {escape(preheader)}
  </div>

  <table role="presentation" width="100%" cellpadding="0" cellspacing="0"
         border="0" style="background:{BACKGROUND_COLOR};">
    <tr>
      <td align="center" style="padding:28px 12px;">

        <table role="presentation" width="600" cellpadding="0" cellspacing="0"
               border="0"
               style="width:100%;max-width:600px;background:{CARD_COLOR};
                      border:1px solid {BORDER_COLOR};">

          <tr>
            <td align="center"
                style="padding:28px 20px 22px;background:{BACKGROUND_COLOR};">
                <p style="margin:0 0 8px;font-size:16px;font-weight:700;
                            color:{BRAND_COLOR};">
                    {business_name}
                </p>

              <p style="margin:7px 0 0;font-size:9px;letter-spacing:2px;
                        color:{MUTED_COLOR};">
                SELF-DRIVE CAR RENT
              </p>

              <p style="margin:12px 0 0;font-size:12px;color:{MUTED_COLOR};">
                {escape(settings.business_tagline)}
              </p>
            </td>
          </tr>

          <tr>
            <td style="height:4px;background:{BRAND_COLOR};
                       line-height:4px;font-size:1px;">&nbsp;</td>
          </tr>

          <tr>
            <td style="padding:30px 28px 12px;">
              <h1 style="margin:0;font-size:25px;line-height:34px;
                         font-weight:800;color:{TEXT_COLOR};">
                {escape(title)}
              </h1>
            </td>
          </tr>

          <tr>
            <td style="padding:8px 28px 30px;color:{TEXT_COLOR};
                       font-size:14px;line-height:23px;">
              {content}
            </td>
          </tr>

          <tr>
            <td align="center"
                style="padding:23px 20px;background:{BACKGROUND_COLOR};
                       border-top:1px solid {BORDER_COLOR};">

              <p style="margin:0 0 8px;font-size:14px;font-weight:700;
                        color:{BRAND_COLOR};">
                {business_name}
              </p>

              <p style="margin:0 0 8px;font-size:12px;color:{MUTED_COLOR};">
                Greater Noida | NCR
              </p>

              <p style="margin:0 0 14px;font-size:12px;color:{MUTED_COLOR};">
                Contact:
                <a href="tel:{phone}"
                   style="color:{BRAND_COLOR};text-decoration:none;">
                  {phone}
                </a>
              </p>

              <p style="margin:0;font-size:10px;line-height:17px;
                        color:{MUTED_COLOR};">
                This is an automated email regarding your enquiry.
                Please retain your reference number for future communication.
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


def _detail_table(
    lines: list[tuple[str, str]],
) -> str:
    rows = []

    for label, value in lines:
        rows.append(f"""
        <tr>
          <td width="38%" valign="top"
              style="padding:11px 12px 11px 0;border-bottom:1px solid
                     {BORDER_COLOR};font-size:12px;color:{MUTED_COLOR};">
            {escape(label)}
          </td>

          <td valign="top"
              style="padding:11px 0;border-bottom:1px solid {BORDER_COLOR};
                     font-size:13px;line-height:20px;color:{TEXT_COLOR};
                     font-weight:600;overflow-wrap:anywhere;">
            {escape(str(value))}
          </td>
        </tr>
        """)

    return f"""
    <table role="presentation" width="100%" cellpadding="0" cellspacing="0"
           border="0" style="border-collapse:collapse;">
      {''.join(rows)}
    </table>
    """


def _reference_card(
    reference: str,
    car_name: str,
) -> str:
    return f"""
    <table role="presentation" width="100%" cellpadding="0" cellspacing="0"
           border="0"
           style="background:{BACKGROUND_COLOR};border:1px solid {BORDER_COLOR};">
      <tr>
        <td style="padding:18px;">

          <p style="margin:0 0 6px;font-size:10px;letter-spacing:1.5px;
                    color:{MUTED_COLOR};">
            ENQUIRY REFERENCE
          </p>

          <p style="margin:0;font-size:23px;line-height:31px;
                    font-weight:800;color:{BRAND_COLOR};">
            {escape(str(reference))}
          </p>

          <p style="margin:10px 0 0;font-size:13px;color:{TEXT_COLOR};">
            <span style="color:{MUTED_COLOR};">Vehicle:</span>
            <strong>{escape(str(car_name))}</strong>
          </p>

        </td>
      </tr>
    </table>
    """


def _booking_disclaimer() -> str:
    return f"""
    <table role="presentation" width="100%" cellpadding="0" cellspacing="0"
           border="0"
           style="margin-top:22px;background:#211D12;
                  border-left:4px solid {BRAND_COLOR};">
      <tr>
        <td style="padding:14px 16px;font-size:12px;line-height:20px;
                   color:#E5DCC8;">

          <strong style="color:{BRAND_COLOR};">
            Important: This is not a booking
          </strong>

          <br>
          {escape(NOT_A_BOOKING)}

        </td>
      </tr>
    </table>
    """


def notify_new_enquiry(enquiry: Enquiry) -> None:
    settings = get_settings()
    lines = _enquiry_lines(enquiry)

    business_name = settings.business_name
    car_name = enquiry.car_name_snapshot or "General enquiry"

    # ------------------------------------------------------
    # 1. ADMIN NOTIFICATION EMAIL
    # ------------------------------------------------------

    admin_text = (
        f"New enquiry received on {business_name}.\n\n"
        + "\n".join(f"{label}: {value}" for label, value in lines)
    )

    admin_content = f"""
    <p style="margin:0 0 20px;color:{MUTED_COLOR};">
      A new enquiry has been submitted through your GoTrip website.
      Review the details below and contact the customer.
    </p>

    {_reference_card(enquiry.reference, car_name)}

    <h2 style="margin:26px 0 12px;font-size:16px;color:{BRAND_COLOR};">
      Customer enquiry details
    </h2>

    {_detail_table(lines)}

    <p style="margin:22px 0 0;font-size:12px;color:{MUTED_COLOR};">
      Use the customer's contact information to follow up on this enquiry.
    </p>
    """

    admin_html = _gotrip_email_shell(
        settings=settings,
        title="New customer enquiry",
        preheader=f"New GoTrip enquiry received: {enquiry.reference}",
        content=admin_content,
    )

    send_email(
        OutgoingEmail(
            to=settings.enquiry_notification_to,
            subject=f"New enquiry {enquiry.reference} | {car_name}",
            text=admin_text,
            html=admin_html,
            reply_to=enquiry.email,
        ),
        settings,
    )


    if not settings.send_customer_acknowledgement or not enquiry.email:
        return

    name = (
        enquiry.full_name.strip().split()[0]
        if enquiry.full_name and enquiry.full_name.strip()
        else "there"
    )

    preferred_contact = enquiry.preferred_contact.value

    ack_text = (
        f"Hi {name},\n\n"
        f"Thank you for contacting {business_name}.\n\n"
        f"We have received your enquiry successfully.\n"
        f"Reference: {enquiry.reference}\n"
        f"Vehicle: {car_name}\n\n"
        f"Our team will contact you shortly by {preferred_contact}.\n\n"
        f"What happens next?\n"
        f"Our team will review your requirements and confirm availability, "
        f"pricing and rental terms directly with you.\n\n"
        f"{NOT_A_BOOKING}\n\n"
        f"Phone / WhatsApp: {settings.business_phone}\n"
        f"{business_name} - {settings.business_tagline}"
    )

    customer_content = f"""
    <p style="margin:0 0 14px;font-size:15px;color:{TEXT_COLOR};">
      Hi <strong>{escape(name)}</strong>,
    </p>

    <p style="margin:0 0 16px;color:{MUTED_COLOR};">
      Thank you for choosing
      <strong style="color:{TEXT_COLOR};">{escape(business_name)}</strong>.
      We have received your enquiry and appreciate your interest in our
      self-drive cars.
    </p>

    <p style="margin:0 0 20px;color:{MUTED_COLOR};">
      Our team will contact you shortly via
      <strong style="color:{BRAND_COLOR};">
        {escape(preferred_contact)}
      </strong>.
    </p>

    {_reference_card(enquiry.reference, car_name)}

    <h2 style="margin:26px 0 8px;font-size:16px;color:{BRAND_COLOR};">
      What happens next?
    </h2>

    <p style="margin:0;color:{MUTED_COLOR};">
      We will review your requirements and discuss vehicle availability,
      pricing and rental terms with you directly.
    </p>

    {_booking_disclaimer()}

    <p style="margin:22px 0 0;color:{MUTED_COLOR};">
      Have a question? Contact our team at
      <strong style="color:{TEXT_COLOR};">
        {escape(settings.business_phone)}
      </strong>.
    </p>

    <p style="margin:18px 0 0;color:{TEXT_COLOR};">
      Thank you,<br>
      <strong style="color:{BRAND_COLOR};">
        Team {escape(business_name)}
      </strong>
    </p>
    """

    customer_html = _gotrip_email_shell(
        settings=settings,
        title="We've received your enquiry!",
        preheader=(
            f"Thank you for contacting {business_name}. "
            f"Reference: {enquiry.reference}"
        ),
        content=customer_content,
    )

    send_email(
        OutgoingEmail(
            to=[enquiry.email],
            subject=(
                f"Enquiry received - {enquiry.reference} | {business_name}"
            ),
            text=ack_text,
            html=customer_html,
        ),
        settings,
    )
