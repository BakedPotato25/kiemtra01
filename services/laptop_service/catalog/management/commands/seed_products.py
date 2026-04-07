from decimal import Decimal

from django.core.management.base import BaseCommand

from catalog.models import Product


LAPTOP_PRODUCTS = [
    ("Aster Pro 14", "Lenovo", "1199.00", 32, "Balanced 14-inch machine for development and productivity workflows."),
    ("Aster Pro 16", "Lenovo", "1549.00", 24, "Large-screen workstation with improved thermal capacity and typing comfort."),
    ("NovaBook Air 13", "ASUS", "999.00", 40, "Portable ultrabook with long battery life and quick wake behavior."),
    ("NovaBook Studio 15", "ASUS", "1849.00", 18, "Creator-focused laptop tuned for design and export-heavy sessions."),
    ("Titan Forge 17", "MSI", "2299.00", 12, "Performance platform with dedicated graphics and wide cooling headroom."),
    ("Titan Forge 15", "MSI", "1999.00", 16, "Compact high-power model for rendering and software build pipelines."),
    ("Latitude Sprint 14", "Dell", "1329.00", 28, "Business-ready chassis with dependable docking and stable connectivity."),
    ("Latitude Sprint 15", "Dell", "1399.00", 25, "Reliable office laptop with practical serviceability and battery longevity."),
    ("ThinkFlow Carbon 14", "Lenovo", "1699.00", 22, "Lightweight premium model with secure sign-in and quality keyboard."),
    ("ThinkFlow Ultra 16", "Lenovo", "1899.00", 15, "16-inch productivity device for presentations, coding, and multitasking."),
    ("ZenCore 14 OLED", "ASUS", "1499.00", 20, "OLED display option with sharp contrast and low-noise operation."),
    ("ZenCore 16 Creator", "ASUS", "2099.00", 14, "High-memory creator setup for graphics, edits, and analytics workloads."),
    ("PulseBook 13", "HP", "879.00", 44, "Entry workstation with quick charging and practical mobility features."),
    ("PulseBook 15", "HP", "1049.00", 36, "Mainstream 15-inch model built for everyday office and remote work."),
    ("Envision Work 15", "Acer", "949.00", 30, "Value-first device with stable wireless performance and broad compatibility."),
    ("Envision Work 17", "Acer", "1189.00", 26, "Large panel option ideal for spreadsheets and intensive browser workflows."),
    ("Orbit Prime 14", "Samsung", "1419.00", 21, "Refined build quality with clear webcam output and responsive daily speed."),
    ("Orbit Prime 16", "Samsung", "1769.00", 17, "Premium 16-inch laptop with boosted throughput for heavy productivity."),
    ("BladeCore R15", "Razer", "2399.00", 9, "High-end unibody performance machine with premium panel responsiveness."),
    ("BladeCore R14", "Razer", "2199.00", 11, "Portable performance model balancing power and travel-friendly form factor."),
    ("CreatorLite 15", "Gigabyte", "1599.00", 19, "Color-consistent workstation for creators and modern software projects."),
    ("CreatorLite 16", "Gigabyte", "1919.00", 13, "Large-panel creative workstation with stable sustained clock behavior."),
    ("EdgeBook Flex 13", "Dell", "1249.00", 23, "Convertible laptop with pen support for flexible presentation workflows."),
    ("EdgeBook Flex 14", "HP", "1299.00", 27, "2-in-1 productivity system for mixed writing, drawing, and review tasks."),
]


def _image_url(name, index):
    _ = name
    image_pool = [
        "https://images.unsplash.com/photo-1496181133206-80ce9b88a853?auto=format&fit=crop&w=1200&q=80",
        "https://images.unsplash.com/photo-1525547719571-a2d4ac8945e2?auto=format&fit=crop&w=1200&q=80",
        "https://images.unsplash.com/photo-1515879218367-8466d910aaa4?auto=format&fit=crop&w=1200&q=80",
        "https://images.unsplash.com/photo-1498050108023-c5249f4df085?auto=format&fit=crop&w=1200&q=80",
        "https://images.unsplash.com/photo-1517694712202-14dd9538aa97?auto=format&fit=crop&w=1200&q=80",
        "https://images.unsplash.com/photo-1611186871348-b1ce696e52c9?auto=format&fit=crop&w=1200&q=80",
        "https://images.unsplash.com/photo-1531297484001-80022131f5a1?auto=format&fit=crop&w=1200&q=80",
        "https://images.unsplash.com/photo-1484788984921-03950022c9ef?auto=format&fit=crop&w=1200&q=80",
    ]
    return image_pool[(index - 1) % len(image_pool)]


class Command(BaseCommand):
    help = "Seed laptop catalog with rich demo products and varied images"

    def add_arguments(self, parser):
        parser.add_argument("--reset", action="store_true", help="Delete existing products before seeding")

    def handle(self, *args, **options):
        if options["reset"]:
            deleted, _ = Product.objects.all().delete()
            self.stdout.write(self.style.WARNING(f"Deleted {deleted} existing laptop product rows."))

        created_count = 0
        updated_count = 0
        for index, item in enumerate(LAPTOP_PRODUCTS, start=1):
            name, brand, price, stock, description = item
            _, created = Product.objects.update_or_create(
                name=name,
                brand=brand,
                defaults={
                    "description": description,
                    "image_url": _image_url(name, index),
                    "price": Decimal(price),
                    "stock": stock,
                },
            )
            if created:
                created_count += 1
            else:
                updated_count += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"Laptop seed complete. Created: {created_count}, Updated: {updated_count}, Total now: {Product.objects.count()}."
            )
        )
