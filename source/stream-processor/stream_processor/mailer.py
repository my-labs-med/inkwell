import html
import os

from inkwell.aws import cognito, ses


def email_for(user_id):
    users = cognito().list_users(
        UserPoolId=os.environ["USER_POOL_ID"], Filter=f'sub = "{user_id}"', Limit=1
    )["Users"]
    if not users:
        return None
    attributes = {attr["Name"]: attr["Value"] for attr in users[0].get("Attributes", [])}
    return attributes.get("email")


def send(recipient, subject, text):
    link = os.environ.get("APP_URL", "")
    body_text = f"{text}\n\n{link}".strip()
    button = f'<p><a href="{html.escape(link)}" style="color:#7a3b2e">Open Inkwell</a></p>'
    body_html = (
        '<div style="font-family:Georgia,serif;color:#2b2622;max-width:480px">'
        f'<h1 style="font-weight:normal">{html.escape(subject)}</h1>'
        f"<p>{html.escape(text)}</p>{button if link else ''}</div>"
    )
    ses().send_email(
        Source=os.environ["SENDER_EMAIL"],
        Destination={"ToAddresses": [recipient]},
        Message={
            "Subject": {"Data": subject},
            "Body": {"Text": {"Data": body_text}, "Html": {"Data": body_html}},
        },
    )
