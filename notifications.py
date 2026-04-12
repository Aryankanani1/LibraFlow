"""
LibraFlow — Notification Service
---------------------------------
Sends email (Flask-Mail/SMTP) and SMS (Twilio) notifications.
Both channels degrade gracefully when not configured:
  - Email logs to console and stores a 'pending' record.
  - SMS is skipped if no phone number or Twilio credentials.
All sent (or attempted) notifications are persisted in the Notification table.
"""

from flask import current_app
from models import db, Notification


# ── Internal helpers ──────────────────────────────────────────────────────────

def _record(user, ntype, subject, message, status='sent'):
    notif = Notification(
        user_id=user.id,
        type=ntype,
        subject=subject,
        message=message,
        status=status,
    )
    db.session.add(notif)
    # Caller is responsible for commit (batching with other changes is fine)


def send_email(user, subject, body):
    """Send an email to *user*. Falls back to console logging if unconfigured."""
    try:
        from flask_mail import Message as MailMessage
        mail = current_app.extensions.get('mail')
        if mail and current_app.config.get('MAIL_USERNAME'):
            msg = MailMessage(
                subject=subject,
                recipients=[user.email],
                body=body,
                sender=current_app.config.get('MAIL_DEFAULT_SENDER', 'noreply@libraflow.com'),
            )
            mail.send(msg)
            _record(user, 'email', subject, body, 'sent')
        else:
            current_app.logger.info(f'[EMAIL — not configured] To: {user.email} | {subject}')
            _record(user, 'email', subject, body, 'pending')
    except Exception as exc:
        current_app.logger.error(f'Email error for {user.email}: {exc}')
        _record(user, 'email', subject, body, 'failed')
    db.session.commit()


def send_sms(user, message):
    """Send an SMS to *user.phone_number*. Skipped if no phone or Twilio unconfigured."""
    if not user.phone_number:
        return
    try:
        sid  = current_app.config.get('TWILIO_ACCOUNT_SID')
        tok  = current_app.config.get('TWILIO_AUTH_TOKEN')
        frm  = current_app.config.get('TWILIO_FROM_NUMBER')
        if sid and tok and frm:
            from twilio.rest import Client
            Client(sid, tok).messages.create(body=message, from_=frm, to=user.phone_number)
            _record(user, 'sms', 'SMS', message, 'sent')
        else:
            current_app.logger.info(f'[SMS — not configured] To: {user.phone_number} | {message}')
            _record(user, 'sms', 'SMS', message, 'pending')
    except Exception as exc:
        current_app.logger.error(f'SMS error for {user.phone_number}: {exc}')
        _record(user, 'sms', 'SMS', message, 'failed')
    db.session.commit()


# ── Notification events ───────────────────────────────────────────────────────

def notify_loan_issued(loan):
    s = loan.student
    due = loan.due_date.strftime('%B %d, %Y')
    send_email(
        s,
        f'Book Issued: {loan.copy.book.title}',
        f'Hi {s.name},\n\n'
        f'"{loan.copy.book.title}" has been issued to you.\n'
        f'Due Date : {due}\n'
        f'Copy Code: {loan.copy.copy_code}\n\n'
        f'Please return it on time to avoid a $1/day late fine.\n\n'
        f'— LibraFlow Library',
    )
    send_sms(
        s,
        f'LibraFlow: "{loan.copy.book.title}" issued. Due {loan.due_date.strftime("%b %d, %Y")}. Return on time!',
    )


def notify_loan_returned(loan):
    s = loan.student
    fine = loan.fine_charged or 0.0
    if fine > 0:
        send_email(
            s,
            f'Book Returned — Fine Due: {loan.copy.book.title}',
            f'Hi {s.name},\n\n'
            f'"{loan.copy.book.title}" has been returned.\n'
            f'Fine Amount: ${fine:.2f} (payable at the library desk).\n\n'
            f'— LibraFlow Library',
        )
        send_sms(
            s,
            f'LibraFlow: "{loan.copy.book.title}" returned. Fine: ${fine:.2f} — please pay at the desk.',
        )
    else:
        send_email(
            s,
            f'Book Returned: {loan.copy.book.title}',
            f'Hi {s.name},\n\n'
            f'"{loan.copy.book.title}" has been returned on time. No fines!\n\n'
            f'Thank you — LibraFlow Library',
        )
        send_sms(
            s,
            f'LibraFlow: "{loan.copy.book.title}" returned on time. No fines! Thanks.',
        )


def notify_reservation_approved(reservation):
    s = reservation.student
    book = reservation.copy.book
    send_email(
        s,
        f'Reservation Approved: {book.title}',
        f'Hi {s.name},\n\n'
        f'Your reservation for "{book.title}" has been approved.\n'
        f'Please visit the library to collect your book within 3 days.\n\n'
        f'— LibraFlow Library',
    )
    send_sms(
        s,
        f'LibraFlow: Reservation for "{book.title}" approved! Collect within 3 days.',
    )


def notify_reservation_rejected(reservation):
    s = reservation.student
    book = reservation.copy.book
    send_email(
        s,
        f'Reservation Not Approved: {book.title}',
        f'Hi {s.name},\n\n'
        f'Unfortunately your reservation for "{book.title}" could not be approved.\n'
        f'Please contact the library or search for another available copy.\n\n'
        f'— LibraFlow Library',
    )
    send_sms(
        s,
        f'LibraFlow: Reservation for "{book.title}" was not approved. Visit library for help.',
    )


def notify_overdue_reminder(loan):
    s = loan.student
    fine = loan.fine_amount()
    send_email(
        s,
        f'Overdue Notice: {loan.copy.book.title}',
        f'Hi {s.name},\n\n'
        f'"{loan.copy.book.title}" was due on {loan.due_date.strftime("%B %d, %Y")}.\n'
        f'Current Fine: ${fine:.2f}\n\n'
        f'Please return it immediately — the fine increases by $1 each day.\n\n'
        f'— LibraFlow Library',
    )
    send_sms(
        s,
        f'LibraFlow OVERDUE: "{loan.copy.book.title}" due {loan.due_date.strftime("%b %d")}. '
        f'Fine: ${fine:.2f}. Return ASAP!',
    )


def notify_fine_paid(loan):
    s = loan.student
    fine = loan.fine_charged or 0.0
    send_email(
        s,
        f'Fine Paid: {loan.copy.book.title}',
        f'Hi {s.name},\n\n'
        f'Your fine of ${fine:.2f} for "{loan.copy.book.title}" has been marked as paid.\n'
        f'Thank you!\n\n'
        f'— LibraFlow Library',
    )
    send_sms(
        s,
        f'LibraFlow: Fine of ${fine:.2f} for "{loan.copy.book.title}" paid. Thank you!',
    )
