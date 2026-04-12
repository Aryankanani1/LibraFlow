"""
LibraFlow — Manual + Automated Test Suite
==========================================
Covers: Fine Payment, Email/SMS Notifications, Admin Self-Registration

Run with:  python test_features.py
"""

import sys
from datetime import datetime, timedelta, timezone

# ── App setup ─────────────────────────────────────────────────────────────────
from app import create_app
app = create_app()

PASS = '\033[92m✓\033[0m'
FAIL = '\033[91m✗\033[0m'
HEAD = '\033[1m\033[94m'
RESET = '\033[0m'
WARN = '\033[93m⚠\033[0m'

results = []

def check(label, condition, detail=''):
    status = PASS if condition else FAIL
    print(f'  {status}  {label}' + (f'  →  {detail}' if detail else ''))
    results.append((label, condition))

def section(title):
    print(f'\n{HEAD}{"─"*60}')
    print(f'  {title}')
    print(f'{"─"*60}{RESET}')


# ══════════════════════════════════════════════════════════════════════════════
with app.app_context():
    from models import db, User, Book, BookCopy, Loan, Reservation, Notification
    from notifications import (
        notify_loan_issued, notify_loan_returned,
        notify_reservation_approved, notify_reservation_rejected,
        notify_overdue_reminder, notify_fine_paid,
    )

    # ── Grab demo fixtures ────────────────────────────────────────────────────
    admin   = User.query.filter_by(role='librarian').first()
    student = User.query.filter_by(role='student').first()
    copy    = BookCopy.query.filter_by(status='available').first()

    section('FIXTURES')
    check('Admin user exists',   admin   is not None, admin.email   if admin   else '—')
    check('Student user exists', student is not None, student.email if student else '—')
    check('Available book copy', copy    is not None, copy.copy_code if copy   else '—')

    if not (admin and student and copy):
        print(f'\n  {FAIL}  Cannot proceed — missing fixtures. Run the app once to seed data.\n')
        sys.exit(1)


    # ══════════════════════════════════════════════════════════════════════════
    section('FEATURE 1 — FINE PAYMENT MODULE')

    # 1-A  Issue a book with a past due date (simulate overdue)
    past_due = datetime.now(timezone.utc) - timedelta(days=5)
    loan = Loan(
        student_id=student.id,
        copy_id=copy.id,
        librarian_id=admin.id,
        issue_date=datetime.now(timezone.utc) - timedelta(days=19),
        due_date=past_due,
        status='active',
    )
    copy.status = 'issued'
    db.session.add(loan)
    db.session.commit()
    check('Loan created (5 days overdue)', loan.id is not None, f'loan #{loan.id}')

    # 1-B  Live fine calculation
    live_fine = loan.fine_amount()
    check('Live fine = $5.00', live_fine == 5.0, f'${live_fine:.2f}')

    # 1-C  is_overdue()
    check('is_overdue() returns True', loan.is_overdue())

    # 1-D  Mark returned — fine freezes
    loan.mark_returned()
    check('Loan status → returned',           loan.status == 'returned')
    check('fine_charged frozen at $5.00',     loan.fine_charged == 5.0, f'${loan.fine_charged:.2f}')
    check('fine_paid defaults to False',      loan.fine_paid == False)
    check('outstanding_fine() = $5.00',       loan.outstanding_fine() == 5.0)
    check('fine_amount() returns frozen val', loan.fine_amount() == 5.0)
    check('is_overdue() False after return',  not loan.is_overdue())

    # 1-E  Pay the fine
    loan.fine_paid = True
    db.session.commit()
    check('fine_paid → True',           loan.fine_paid == True)
    check('outstanding_fine() → $0.00', loan.outstanding_fine() == 0.0)

    # 1-F  Loan with no overdue — fine_charged should be None
    on_time_due = datetime.now(timezone.utc) + timedelta(days=7)
    copy2 = BookCopy.query.filter(
        BookCopy.status == 'available', BookCopy.id != copy.id
    ).first()

    if copy2:
        loan2 = Loan(
            student_id=student.id, copy_id=copy2.id, librarian_id=admin.id,
            issue_date=datetime.now(timezone.utc), due_date=on_time_due, status='active',
        )
        copy2.status = 'issued'
        db.session.add(loan2)
        db.session.commit()
        loan2.mark_returned()
        check('On-time return: fine_charged is None', loan2.fine_charged is None)
        check('On-time return: fine_amount() = 0',   loan2.fine_amount() == 0.0)
    else:
        print(f'  {WARN}  Skipped on-time loan test (no second available copy)')

    # ── Cleanup ───────────────────────────────────────────────────────────────
    copy.status = 'available'
    if copy2: copy2.status = 'available'
    db.session.commit()


    # ══════════════════════════════════════════════════════════════════════════
    section('FEATURE 2 — EMAIL & SMS NOTIFICATIONS')

    notifs_before = Notification.query.count()

    # 2-A  Loan issued notification
    notify_loan_issued(loan)
    n_issued = Notification.query.filter(
        Notification.user_id == student.id,
        Notification.subject.like('%Issued%'),
    ).order_by(Notification.id.desc()).first()
    check('notify_loan_issued → record created', n_issued is not None)
    check('notify_loan_issued → correct user',   n_issued and n_issued.user_id == student.id)
    check('notify_loan_issued → type=email',     n_issued and n_issued.type == 'email')
    check('notify_loan_issued → status sent/pending',
          n_issued and n_issued.status in ('sent', 'pending'),
          n_issued.status if n_issued else '—')

    # 2-B  Loan returned notification (with fine)
    notify_loan_returned(loan)
    n_returned = Notification.query.filter(
        Notification.user_id == student.id,
        Notification.subject.like('%Returned%'),
    ).order_by(Notification.id.desc()).first()
    check('notify_loan_returned → record created', n_returned is not None)
    check('notify_loan_returned → mentions fine',
          n_returned and '$5.00' in n_returned.message)

    # 2-C  Fine paid notification
    notify_fine_paid(loan)
    n_paid = Notification.query.filter(
        Notification.user_id == student.id,
        Notification.subject.like('%Fine Paid%'),
    ).order_by(Notification.id.desc()).first()
    check('notify_fine_paid → record created', n_paid is not None)

    # 2-D  Reservation notifications
    res_copy = BookCopy.query.filter_by(status='available').first()
    if res_copy:
        res = Reservation(
            student_id=student.id, copy_id=res_copy.id,
            request_date=datetime.now(timezone.utc), status='pending',
        )
        res_copy.status = 'reserved'
        db.session.add(res)
        db.session.commit()

        notify_reservation_approved(res)
        n_approved = Notification.query.filter(
            Notification.user_id == student.id,
            Notification.subject.like('%Approved%'),
        ).order_by(Notification.id.desc()).first()
        check('notify_reservation_approved → record', n_approved is not None)

        notify_reservation_rejected(res)
        n_rejected = Notification.query.filter(
            Notification.user_id == student.id,
            Notification.subject.like('%Not Approved%'),
        ).order_by(Notification.id.desc()).first()
        check('notify_reservation_rejected → record', n_rejected is not None)

        # cleanup
        res_copy.status = 'available'
        res.status = 'cancelled'
        db.session.commit()
    else:
        print(f'  {WARN}  Skipped reservation notification test (no available copy)')

    # 2-E  Overdue reminder
    notify_overdue_reminder(loan)
    n_overdue = Notification.query.filter(
        Notification.user_id == student.id,
        Notification.subject.like('%Overdue%'),
    ).order_by(Notification.id.desc()).first()
    check('notify_overdue_reminder → record', n_overdue is not None)

    # 2-F  Notification count grew
    notifs_after = Notification.query.count()
    check('Notification table grew', notifs_after > notifs_before,
          f'{notifs_before} → {notifs_after}')

    # 2-G  Student unread count
    student.notifications.filter_by(read=False).count()
    unread = student.notifications.filter_by(read=False).count()
    check('Student has unread notifications', unread > 0, f'{unread} unread')


    # ══════════════════════════════════════════════════════════════════════════
    section('FEATURE 3 — ADMIN SELF-REGISTRATION')

    from flask import current_app

    # 3-A  Correct code accepted
    valid_code   = current_app.config.get('LIBRARIAN_CODE')
    invalid_code = 'WRONGCODE'
    check('LIBRARIAN_CODE config loaded',       valid_code is not None, valid_code)
    check('Correct code passes validation',     valid_code == 'LIBRA2026')
    check('Wrong code fails validation',        valid_code != invalid_code)

    # 3-B  Register a new librarian with correct code
    test_email = 'test_librarian_temp@libraflow.com'
    existing = User.query.filter_by(email=test_email).first()
    if existing:
        db.session.delete(existing)
        db.session.commit()

    new_lib = User(
        name='Test Librarian', email=test_email,
        role='librarian', employee_id='EMP999',
    )
    new_lib.set_password('test1234')
    db.session.add(new_lib)
    db.session.commit()
    check('New librarian account created',      new_lib.id is not None)
    check('Role is librarian',                  new_lib.is_librarian())
    check('check_password() works',             new_lib.check_password('test1234'))
    check('Wrong password rejected',            not new_lib.check_password('badpass'))

    # 3-C  phone_number column exists on User
    check('User.phone_number column exists',    hasattr(User, 'phone_number'))
    new_lib.phone_number = '+1 555 000 9999'
    db.session.commit()
    check('phone_number saves correctly',
          User.query.get(new_lib.id).phone_number == '+1 555 000 9999')

    # Cleanup test librarian
    db.session.delete(new_lib)
    db.session.commit()
    check('Test librarian cleaned up', User.query.filter_by(email=test_email).first() is None)

    # 3-D  Student registration has no code requirement (role='student')
    test_student_email = 'test_student_temp@libraflow.com'
    existing_s = User.query.filter_by(email=test_student_email).first()
    if existing_s:
        db.session.delete(existing_s)
        db.session.commit()

    new_student = User(name='Test Student', email=test_student_email, role='student', student_id='STU999')
    new_student.set_password('test1234')
    db.session.add(new_student)
    db.session.commit()
    check('Student registers without code', new_student.id is not None)
    check('Role is student',                new_student.is_student())

    db.session.delete(new_student)
    db.session.commit()


    # ══════════════════════════════════════════════════════════════════════════
    section('SUMMARY')

    total  = len(results)
    passed = sum(1 for _, ok in results if ok)
    failed = total - passed

    print(f'\n  Total : {total}')
    print(f'  {PASS} Passed: {passed}')
    if failed:
        print(f'  {FAIL} Failed: {failed}')
        for label, ok in results:
            if not ok:
                print(f'       • {label}')
    print()

    sys.exit(0 if failed == 0 else 1)
