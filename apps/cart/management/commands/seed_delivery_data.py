from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
import os
import secrets

from apps.cart.models import DeliveryAgent


class Command(BaseCommand):
    help = "Seed idempotent delivery partners for local testing."

    agents = [
        ("Amit Verma", "9876500001", "GJ-06-AB-1201"),
        ("Neha Patel", "9876500002", "GJ-06-CD-2202"),
        ("Ravi Solanki", "9876500003", "GJ-06-EF-3303"),
    ]

    def handle(self, *args, **options):
        User = get_user_model()
        configured_password = os.getenv("SEED_DEMO_PASSWORD", "").strip()
        password = configured_password or secrets.token_urlsafe(18)
        generated_password = not configured_password
        for name, phone, vehicle_number in self.agents:
            username = f"demo_rider_{phone[-4:]}"
            user, created = User.objects.get_or_create(
                username=username,
                defaults={"email": f"{username}@example.com", "role": User.Role.RIDER, "phone": phone},
            )
            if created or not user.has_usable_password():
                user.set_password(password)
                user.save(update_fields=["password"])
            agent, created = DeliveryAgent.objects.update_or_create(
                phone=phone,
                defaults={"name": name, "vehicle_number": vehicle_number, "user": user},
            )
            action = "Created" if created else "Updated"
            self.stdout.write(f"{action} delivery agent: {agent.name}")
        if generated_password:
            self.stdout.write(f"Generated rider demo password once (all new riders): {password}")
