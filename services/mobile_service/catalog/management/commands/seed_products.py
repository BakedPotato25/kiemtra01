from decimal import Decimal

from django.core.management.base import BaseCommand

from catalog.models import Product


MOBILE_PRODUCTS = [
    ("AeroPhone X1", "Apple", "1299.00", 36, "Flagship model with premium frame, fast silicon, and stable camera output."),
    ("AeroPhone X1 Max", "Apple", "1499.00", 28, "Large-display variant with long endurance for media-heavy users."),
    ("AeroPhone X1 Mini", "Apple", "999.00", 31, "Compact flagship with one-hand ergonomics and excellent responsiveness."),
    ("Galaxy Nova S24", "Samsung", "1099.00", 42, "Balanced premium Android phone with vivid display and practical AI tools."),
    ("Galaxy Nova S24 Ultra", "Samsung", "1399.00", 25, "Ultra series device with advanced zoom and high multitasking performance."),
    ("Galaxy Nova A56", "Samsung", "489.00", 58, "Value-centric smartphone with dependable battery and smooth interface flow."),
    ("Pixel Vision 9", "Google", "899.00", 39, "Smart camera phone with clean software and fast security patch cycles."),
    ("Pixel Vision 9 Pro", "Google", "1149.00", 27, "Pro-level photography controls with brighter panel and telephoto range."),
    ("Pixel Vision 8a", "Google", "549.00", 63, "Affordable Pixel option with practical AI features and fluid navigation."),
    ("OnePlus Velocity 13", "OnePlus", "799.00", 47, "Performance Android device with quick charging and gaming-ready tuning."),
    ("OnePlus Velocity 13R", "OnePlus", "659.00", 52, "Strong value profile with smooth display and efficient battery behavior."),
    ("OnePlus Velocity Fold", "OnePlus", "1699.00", 12, "Foldable phone designed for split-screen productivity and immersive media."),
    ("Xiaomi Hyper 14", "Xiaomi", "599.00", 55, "High-value smartphone with bright AMOLED visuals and quick refueling."),
    ("Xiaomi Hyper 14 Pro", "Xiaomi", "799.00", 34, "Improved image pipeline and stronger processor for advanced workflows."),
    ("Xiaomi Hyper 14 Lite", "Xiaomi", "379.00", 70, "Entry-friendly model that keeps daily interactions responsive and stable."),
    ("Moto Edge Prime", "Motorola", "649.00", 43, "Simple Android experience with curved display and practical daily speed."),
    ("Moto Edge Plus", "Motorola", "899.00", 29, "Premium Motorola variant with improved low-light capture performance."),
    ("Sony Xperia Core 1", "Sony", "1049.00", 19, "Creator-focused handset with cinematic profile and manual camera controls."),
    ("Sony Xperia Core 1 Pro", "Sony", "1299.00", 15, "Pro-grade capture option with high color precision and strong detail."),
    ("Nokia Aurora 10", "Nokia", "459.00", 46, "Durable phone engineered for practical use and consistent battery behavior."),
    ("Nokia Aurora 10 Plus", "Nokia", "579.00", 33, "Expanded memory and camera improvements in a reliable body design."),
    ("Vivo Vision Pro", "Vivo", "739.00", 37, "Portrait-oriented camera tuning for social content and creator workflows."),
    ("Oppo Find Zenith", "Oppo", "869.00", 30, "Premium curved smartphone with rapid charging and balanced thermals."),
    ("Oppo Find Zenith Lite", "Oppo", "499.00", 51, "Cost-effective option with smooth interactions and efficient power draw."),
]


def _image_url(name, index):
    _ = name
    image_pool = [
        "https://images.unsplash.com/photo-1511707171634-5f897ff02aa9?auto=format&fit=crop&w=1200&q=80",
        "https://images.unsplash.com/photo-1510557880182-3f8c2b11d7f8?auto=format&fit=crop&w=1200&q=80",
        "https://images.unsplash.com/photo-1598327105666-5b89351aff97?auto=format&fit=crop&w=1200&q=80",
        "https://images.unsplash.com/photo-1605236453806-6ff36851218e?auto=format&fit=crop&w=1200&q=80",
        "https://images.unsplash.com/photo-1574944985070-8f3ebc6b79d2?auto=format&fit=crop&w=1200&q=80",
        "https://images.unsplash.com/photo-1567581935884-3349723552ca?auto=format&fit=crop&w=1200&q=80",
        "https://images.unsplash.com/photo-1556656793-08538906a9f8?auto=format&fit=crop&w=1200&q=80",
        "https://images.unsplash.com/photo-1580910051074-3eb694886505?auto=format&fit=crop&w=1200&q=80",
    ]
    return image_pool[(index - 1) % len(image_pool)]


class Command(BaseCommand):
    help = "Seed mobile catalog with rich demo products and varied images"

    def add_arguments(self, parser):
        parser.add_argument("--reset", action="store_true", help="Delete existing products before seeding")

    def handle(self, *args, **options):
        if options["reset"]:
            deleted, _ = Product.objects.all().delete()
            self.stdout.write(self.style.WARNING(f"Deleted {deleted} existing mobile product rows."))

        created_count = 0
        updated_count = 0
        for index, item in enumerate(MOBILE_PRODUCTS, start=1):
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
                f"Mobile seed complete. Created: {created_count}, Updated: {updated_count}, Total now: {Product.objects.count()}."
            )
        )
