resource "aws_ses_email_identity" "sender" {
  email = var.sender_email
}

resource "aws_ses_email_identity" "recipients" {
  for_each = toset([for email in var.demo_recipient_emails : email if email != var.sender_email])
  email    = each.value
}
