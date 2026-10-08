from django.core.management.base import BaseCommand

from apps.cart.models import DeliveryAgent


class Command(BaseCommand):
    help = "Seed idempotent delivery partners for local testing."

    agents = [
        ("Amit Verma", "9876500001", "GJ-06-AB-1201"),
        ("Neha Patel", "9876500002", "GJ-06-CD-2202"),
        ("Ravi Solanki", "9876500003", "GJ-06-EF-3303"),
    ]

    def handle(self, *args, **options):
        for name, phone, vehicle_number in self.agents:
            agent, created = DeliveryAgent.objects.update_or_create(
                phone=phone,
                defaults={"name": name, "vehicle_number": vehicle_number},
            )
            action = "Created" if created else "Updated"
            self.stdout.write(f"{action} delivery agent: {agent.name}")
