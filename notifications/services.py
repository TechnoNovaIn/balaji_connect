import logging
from django.utils import timezone
from accounts.models import Employee
from .models import Notification

logger = logging.getLogger(__name__)

def check_and_dispatch_daily_birthdays():
    """
    Checks for active employees celebrating birthdays today and dispatches:
    1. Celebration notifications to all active company colleagues.
    2. A personalized congratulatory message to the birthday celebrant.
    Guarantees idempotency (dispatches only once per celebrant per birthday per year).
    """
    today = timezone.localdate()

    # Active employees with birthday today (matching month and day)
    birthday_employees = Employee.objects.filter(
        is_active=True,
        date_of_birth__isnull=False,
        date_of_birth__month=today.month,
        date_of_birth__day=today.day
    ).select_related('department')

    if not birthday_employees.exists():
        return 0

    all_active_employees = list(Employee.objects.filter(is_active=True))
    total_sent = 0

    for celebrant in birthday_employees:
        celebrant_name = celebrant.full_name or celebrant.display_name or celebrant.username

        # 1. Congratulate the celebrant themselves
        already_greeted = Notification.objects.filter(
            recipient=celebrant,
            sender=celebrant,
            notification_type=Notification.NotificationType.BIRTHDAY,
            created_at__year=today.year,
            created_at__month=today.month,
            created_at__day=today.day
        ).exists()

        if not already_greeted:
            Notification.objects.create(
                recipient=celebrant,
                sender=celebrant,
                notification_type=Notification.NotificationType.BIRTHDAY,
                title='🎉 Happy Birthday from Balaji Transports!',
                message=f"Wishing you a very Happy Birthday, {celebrant.first_name or celebrant_name}! May this year bring you great joy, health, and success! 🎂🎈"
            )
            total_sent += 1

        # 2. Notify all colleagues in the company
        for colleague in all_active_employees:
            if colleague.id == celebrant.id:
                continue

            already_notified = Notification.objects.filter(
                recipient=colleague,
                sender=celebrant,
                notification_type=Notification.NotificationType.BIRTHDAY,
                created_at__year=today.year,
                created_at__month=today.month,
                created_at__day=today.day
            ).exists()

            if not already_notified:
                Notification.objects.create(
                    recipient=colleague,
                    sender=celebrant,
                    notification_type=Notification.NotificationType.BIRTHDAY,
                    title='🎂 Birthday Celebration',
                    message=f"Today is {celebrant_name}'s birthday! Wish them a wonderful year ahead! 🎂"
                )
                total_sent += 1

    if total_sent > 0:
        logger.info("Dispatched %d birthday notification(s) for %d celebrant(s) today.", total_sent, len(birthday_employees))

    return total_sent

