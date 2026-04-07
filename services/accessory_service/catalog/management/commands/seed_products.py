from decimal import Decimal

from django.core.management.base import BaseCommand

from catalog.models import Product


ACCESSORY_PRODUCTS = [
    ("FluxCharge 100W USB-C Adapter", "Anker", "59.00", 120, "Compact GaN charger for laptops, tablets, and flagship phones."),
    ("MagLoop Wireless Pad", "Belkin", "39.00", 90, "Fast wireless charging pad with thermal regulation and anti-slip base."),
    ("PulseDock 8-in-1 Hub", "UGREEN", "89.00", 75, "Multiport USB-C hub with HDMI, SD, Ethernet, and passthrough charging."),
    ("AeroKey Mechanical Keyboard", "Keychron", "129.00", 64, "Low-profile wireless mechanical keyboard tuned for productivity."),
    ("TrackPro Ergonomic Mouse", "Logitech", "79.00", 88, "Comfort-focused precision mouse with programmable buttons."),
    ("CloudMic USB Condenser", "HyperX", "99.00", 43, "Plug-and-play desktop microphone for clear calls and recordings."),
    ("QuietBeats ANC Headphones", "Sony", "249.00", 52, "Noise-cancelling headphones with balanced sound profile."),
    ("StudioPods True Wireless", "Apple", "199.00", 66, "Wireless earbuds optimized for quick pairing and stable playback."),
    ("FrameStand Aluminum Laptop Stand", "Twelve South", "69.00", 101, "Adjustable stand for ergonomic typing and thermal airflow."),
    ("CoolFlow Notebook Cooler", "Thermaltake", "49.00", 73, "Active cooling pad designed for sustained laptop performance."),
    ("ShieldSleeve 14-inch", "Tomtoc", "35.00", 115, "Protective sleeve with soft interior and reinforced corner guards."),
    ("ShieldSleeve 16-inch", "Tomtoc", "39.00", 97, "Larger protective sleeve for creator and workstation laptops."),
    ("CrystalGuard Screen Protector", "Spigen", "19.00", 200, "Tempered glass protector with anti-fingerprint coating."),
    ("MagSnap Phone Grip", "MOFT", "29.00", 132, "Magnetic phone grip and stand for portrait or landscape use."),
    ("FlexTripod Mobile Rig", "Ulanzi", "45.00", 81, "Compact tripod rig for mobile photography and content capture."),
    ("PocketSSD 1TB", "Samsung", "129.00", 59, "Portable high-speed SSD for backups and media transfer workflows."),
    ("PocketSSD 2TB", "Samsung", "219.00", 38, "High-capacity portable SSD for creators and engineering teams."),
    ("Clarity 2K Webcam", "Logitech", "149.00", 47, "Crisp webcam with reliable autofocus and low-light improvements."),
    ("MeshBack Travel Backpack", "Peak Design", "189.00", 34, "Tech backpack with modular compartments for laptops and gear."),
    ("Orbit Cable Organizer Kit", "Native Union", "25.00", 150, "Cable management pack for clean desks and travel setups."),
    ("SurgeShield Power Strip", "APC", "55.00", 72, "Surge-protected strip with USB outputs and long braided cable."),
    ("NanoSIM Travel Bundle", "Nomad", "15.00", 175, "Compact SIM tools and adapters for international travel support."),
    ("ProStylus Universal Pen", "Adonit", "79.00", 58, "Pressure-sensitive stylus for tablets and compatible devices."),
    ("DeskGlow Monitor Light", "BenQ", "109.00", 41, "Asymmetric monitor light reducing glare and eye fatigue at night."),
]


def _image_url(name, index):
    _ = name
    image_pool = [
        "https://images.unsplash.com/photo-1583394838336-acd977736f90?auto=format&fit=crop&w=1200&q=80",
        "https://images.unsplash.com/photo-1518444065439-e933c06ce9cd?auto=format&fit=crop&w=1200&q=80",
        "https://images.unsplash.com/photo-1625842268584-8f3296236761?auto=format&fit=crop&w=1200&q=80",
        "https://images.unsplash.com/photo-1545127398-14699f92334b?auto=format&fit=crop&w=1200&q=80",
        "https://images.unsplash.com/photo-1585298723682-7115561c51b7?auto=format&fit=crop&w=1200&q=80",
        "https://images.unsplash.com/photo-1527814050087-3793815479db?auto=format&fit=crop&w=1200&q=80",
        "https://images.unsplash.com/photo-1618384887929-16ec33fab9ef?auto=format&fit=crop&w=1200&q=80",
        "https://images.unsplash.com/photo-1616627458258-18417f2f9c3b?auto=format&fit=crop&w=1200&q=80",
    ]
    return image_pool[(index - 1) % len(image_pool)]


class Command(BaseCommand):
    help = "Seed accessory catalog with practical laptop and mobile accessories"

    def add_arguments(self, parser):
        parser.add_argument("--reset", action="store_true", help="Delete existing products before seeding")

    def handle(self, *args, **options):
        if options["reset"]:
            deleted, _ = Product.objects.all().delete()
            self.stdout.write(self.style.WARNING(f"Deleted {deleted} existing accessory product rows."))

        created_count = 0
        updated_count = 0
        for index, item in enumerate(ACCESSORY_PRODUCTS, start=1):
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
                f"Accessory seed complete. Created: {created_count}, Updated: {updated_count}, Total now: {Product.objects.count()}."
            )
        )
