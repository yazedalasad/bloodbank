# utils/email_service.py
from django.core.mail import EmailMessage
from django.conf import settings
import os

def send_email_with_attachment(subject, message, recipient_list, attachment_path=None):
    """Send email with optional attachment"""
    email = EmailMessage(
        subject,
        message,
        settings.DEFAULT_FROM_EMAIL,
        recipient_list,
    )
    
    if attachment_path and os.path.exists(attachment_path):
        email.attach_file(attachment_path)
    
    return email.send()