import random
import unicodedata
from datetime import timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.utils import timezone

from customer.models import Order, OrderItem


GLOBAL_FIRST_NAMES = [
    "Emma", "Liam", "Olivia", "Noah", "Ava", "Mason", "Sophia", "Lucas", "Mia", "Ethan",
    "Isabella", "James", "Amelia", "Logan", "Harper", "Benjamin", "Evelyn", "Elijah", "Abigail", "Henry",
    "Ella", "Jackson", "Scarlett", "Aiden", "Aria", "Sebastian", "Chloe", "Daniel", "Grace", "Leo",
]

GLOBAL_LAST_NAMES = [
    "Nguyen", "Tran", "Le", "Pham", "Hoang", "Huynh", "Vo", "Dang", "Bui", "Do",
    "Smith", "Johnson", "Brown", "Taylor", "Anderson", "Thomas", "Moore", "Martin", "Lee", "Walker",
]

VI_FAMILY_NAMES = [
    "Nguyen", "Tran", "Le", "Pham", "Hoang", "Huynh", "Vo", "Dang", "Bui", "Do", "Ngo", "Duong", "Ly",
]

VI_MIDDLE_NAMES = [
    "Van", "Thi", "Ngoc", "Thanh", "Minh", "Duc", "Quoc", "Gia", "Bao", "Phuong", "Anh", "Khanh", "Thu", "Huu",
]

VI_GIVEN_NAMES = [
    "An", "Binh", "Chau", "Dung", "Giang", "Ha", "Hanh", "Khanh", "Lam", "Linh", "Mai", "My", "Nam", "Ngan",
    "Ngoc", "Nhi", "Phat", "Phuc", "Phuong", "Quang", "Quynh", "Son", "Thao", "Trang", "Trinh", "Trung", "Tuan", "Vy",
]

EMAIL_DOMAINS_VN = ["gmail.com", "outlook.com", "yahoo.com", "icloud.com", "fpt.com.vn", "vnpt.vn"]
EMAIL_WEIGHTS_VN = [0.58, 0.17, 0.08, 0.07, 0.06, 0.04]

EMAIL_DOMAINS_GLOBAL = ["gmail.com", "outlook.com", "yahoo.com", "hotmail.com", "icloud.com"]
EMAIL_WEIGHTS_GLOBAL = [0.48, 0.2, 0.12, 0.1, 0.1]


PRODUCT_CATALOG = {
    "laptop": [
        ("EdgeBook Flex 14", "HP", Decimal("1299.00")),
        ("EdgeBook Flex 13", "Dell", Decimal("1249.00")),
        ("CreatorLite 16", "Gigabyte", Decimal("1919.00")),
        ("PulseBook 13", "HP", Decimal("879.00")),
        ("ThinkFlow Carbon 14", "Lenovo", Decimal("1699.00")),
    ],
    "mobile": [
        ("Oppo Find Zenith Lite", "Oppo", Decimal("499.00")),
        ("Xiaomi Hyper 14", "Xiaomi", Decimal("599.00")),
        ("Galaxy Nova S24", "Samsung", Decimal("1099.00")),
        ("Pixel Vision 8a", "Google", Decimal("549.00")),
        ("OnePlus Velocity 13", "OnePlus", Decimal("799.00")),
    ],
    "accessory": [
        ("FluxCharge 100W USB-C Adapter", "Anker", Decimal("59.00")),
        ("MagLoop Wireless Pad", "Belkin", Decimal("39.00")),
        ("AeroKey Mechanical Keyboard", "Keychron", Decimal("129.00")),
        ("PocketSSD 1TB", "Samsung", Decimal("129.00")),
        ("QuietBeats ANC Headphones", "Sony", Decimal("249.00")),
    ],
}


def _is_auto_seed_user(username):
    lowered = (username or "").strip().lower()
    return lowered.startswith("customer_auto_") or lowered.startswith("customer_seed_")


def _slug_part(text):
    normalized = unicodedata.normalize("NFKD", str(text or ""))
    ascii_text = normalized.encode("ascii", "ignore").decode("ascii")
    return "".join(ch for ch in ascii_text.lower() if ch.isalnum())


def _pick_locale(profile):
    if profile in {"vn", "global"}:
        return profile
    return "vn" if random.random() < 0.8 else "global"


def _pick_vn_name_parts():
    family = random.choice(VI_FAMILY_NAMES)
    if random.random() < 0.85:
        middle = random.choice(VI_MIDDLE_NAMES)
    else:
        middle = random.choice(VI_MIDDLE_NAMES) + " " + random.choice(VI_MIDDLE_NAMES)
    given = random.choice(VI_GIVEN_NAMES)
    first_name = f"{family} {middle}".strip()
    last_name = given
    return first_name, last_name


def _pick_global_name_parts():
    return random.choice(GLOBAL_FIRST_NAMES), random.choice(GLOBAL_LAST_NAMES)


def _pick_email_domain(locale):
    if locale == "vn":
        return random.choices(EMAIL_DOMAINS_VN, weights=EMAIL_WEIGHTS_VN, k=1)[0]
    return random.choices(EMAIL_DOMAINS_GLOBAL, weights=EMAIL_WEIGHTS_GLOBAL, k=1)[0]


def _compose_base_username(first_name, last_name, locale):
    first_slug = _slug_part(first_name)
    last_slug = _slug_part(last_name)
    if locale == "vn":
        first_tokens = [token for token in first_slug.split() if token]
        family_slug = _slug_part(first_name.split()[0]) if first_name.split() else ""
        if first_tokens:
            middle_slug = _slug_part(first_name.split()[-1])
        else:
            middle_slug = ""
        candidates = [
            f"{last_slug}.{family_slug}",
            f"{last_slug}.{middle_slug}",
            f"{family_slug}.{last_slug}",
            f"{last_slug}{family_slug}",
        ]
    else:
        candidates = [
            f"{first_slug}.{last_slug}",
            f"{first_slug}{last_slug}",
            f"{last_slug}.{first_slug}",
        ]

    for candidate in candidates:
        normalized = "".join(ch for ch in candidate if ch.isalnum() or ch == ".")
        if normalized.strip("."):
            return normalized.strip(".")
    return "customer.seed"


def _next_identity(used_usernames, used_emails, profile):
    locale = _pick_locale(profile)
    if locale == "vn":
        first_name, last_name = _pick_vn_name_parts()
    else:
        first_name, last_name = _pick_global_name_parts()

    base_username = _compose_base_username(first_name, last_name, locale)
    username = base_username or "customer.seed"
    suffix = 1
    while username.lower() in used_usernames:
        suffix += 1
        username = f"{base_username}{suffix:02d}"

    domain = _pick_email_domain(locale)
    email = f"{username}@{domain}"
    while email.lower() in used_emails:
        suffix += 1
        username = f"{base_username}{suffix:02d}"
        email = f"{username}@{domain}"

    used_usernames.add(username.lower())
    used_emails.add(email.lower())

    return {
        "first_name": first_name,
        "last_name": last_name,
        "username": username,
        "email": email,
        "locale": locale,
    }


class Command(BaseCommand):
    help = "Seed customer users, orders, and order history for staff analytics demo"

    def add_arguments(self, parser):
        parser.add_argument("--customers", type=int, default=80, help="Number of customer accounts to ensure")
        parser.add_argument("--orders-per-customer", type=int, default=6, help="Maximum orders generated per customer")
        parser.add_argument("--seed", type=int, default=20260407, help="Random seed for deterministic demo data")
        parser.add_argument("--reset-orders", action="store_true", help="Delete all existing orders and re-seed from scratch")
        parser.add_argument(
            "--profile",
            choices=["vn", "mixed", "global"],
            default="vn",
            help="Identity profile for generated customer names and emails",
        )
        parser.add_argument(
            "--rename-existing",
            action="store_true",
            help="Rename existing non-staff users (except preserved usernames) to generated identities",
        )
        parser.add_argument(
            "--preserve-usernames",
            default="customer1,customer_demo",
            help="Comma-separated usernames to keep unchanged when --rename-existing is used",
        )

    def handle(self, *args, **options):
        random.seed(int(options["seed"]))
        user_model = get_user_model()
        profile = options["profile"]
        rename_existing = bool(options["rename_existing"])
        preserve_usernames = {
            value.strip().lower()
            for value in str(options.get("preserve_usernames") or "").split(",")
            if value.strip()
        }

        customer_total = max(10, int(options["customers"]))
        max_orders = max(1, int(options["orders_per_customer"]))

        if options["reset_orders"]:
            deleted_items, _ = OrderItem.objects.all().delete()
            deleted_orders, _ = Order.objects.all().delete()
            self.stdout.write(self.style.WARNING(f"Deleted {deleted_orders} orders and {deleted_items} order items."))

        existing_customers = list(user_model.objects.filter(is_staff=False, is_superuser=False).order_by("id"))
        rename_candidates = []
        for customer in existing_customers:
            if (customer.username or "").lower() in preserve_usernames:
                continue
            if _is_auto_seed_user(customer.username) or rename_existing:
                rename_candidates.append(customer)

        rename_candidate_ids = {customer.id for customer in rename_candidates}
        used_usernames = {
            customer.username.lower()
            for customer in existing_customers
            if customer.username and customer.id not in rename_candidate_ids
        }
        used_emails = {
            customer.email.lower()
            for customer in existing_customers
            if customer.email and customer.id not in rename_candidate_ids
        }

        renamed_customers = 0
        for customer in rename_candidates:
            identity = _next_identity(used_usernames, used_emails, profile)
            customer.username = identity["username"]
            customer.email = identity["email"]
            customer.first_name = identity["first_name"]
            customer.last_name = identity["last_name"]
            customer.is_staff = False
            customer.is_superuser = False
            customer.save(
                update_fields=[
                    "username",
                    "email",
                    "first_name",
                    "last_name",
                    "is_staff",
                    "is_superuser",
                ]
            )
            renamed_customers += 1

        current_total = user_model.objects.filter(is_staff=False, is_superuser=False).count()
        created_customers = 0
        while current_total < customer_total:
            identity = _next_identity(used_usernames, used_emails, profile)
            user = user_model.objects.create_user(
                username=identity["username"],
                email=identity["email"],
                password="Customer@123",
            )
            user.first_name = identity["first_name"]
            user.last_name = identity["last_name"]
            user.is_staff = False
            user.is_superuser = False
            user.save(update_fields=["first_name", "last_name", "is_staff", "is_superuser"])
            created_customers += 1
            current_total += 1

        all_customers = list(user_model.objects.filter(is_staff=False, is_superuser=False).order_by("id"))

        created_orders = 0
        created_items = 0

        for customer in all_customers:
            existing_count = Order.objects.filter(user=customer).count()

            activity_bucket = random.random()
            if activity_bucket < 0.20:
                target_total = random.randint(0, max(1, max_orders // 3))
            elif activity_bucket < 0.75:
                target_total = random.randint(max(1, max_orders // 3), max(2, (max_orders * 2) // 3))
            else:
                target_total = random.randint(max(2, (max_orders * 2) // 3), max_orders)

            missing = max(0, target_total - existing_count)

            for _ in range(missing):
                line_count = random.randint(1, 4)
                order_lines = []
                order_total = Decimal("0")
                for _ in range(line_count):
                    service_name = random.choice(list(PRODUCT_CATALOG.keys()))
                    product_name, product_brand, unit_price = random.choice(PRODUCT_CATALOG[service_name])
                    quantity = random.randint(1, 3)
                    order_total += unit_price * quantity
                    order_lines.append(
                        {
                            "service": service_name,
                            "name": product_name,
                            "brand": product_brand,
                            "unit_price": unit_price,
                            "quantity": quantity,
                            "product_id": random.randint(1, 120),
                        }
                    )

                status = random.choices(
                    population=[Order.STATUS_PAID, Order.STATUS_PENDING, Order.STATUS_CANCELLED],
                    weights=[0.78, 0.18, 0.04],
                    k=1,
                )[0]

                order = Order.objects.create(
                    user=customer,
                    total_amount=order_total,
                    status=status,
                )

                days_back = int(random.triangular(0, 120, 18))
                minutes_back = random.randint(0, 1439)
                random_created_at = timezone.now() - timedelta(days=days_back, minutes=minutes_back)
                Order.objects.filter(id=order.id).update(created_at=random_created_at)
                created_orders += 1

                item_objects = []
                for line in order_lines:
                    item_objects.append(
                        OrderItem(
                            order=order,
                            product_service=line["service"],
                            product_id=line["product_id"],
                            product_name=line["name"],
                            product_brand=line["brand"],
                            unit_price=line["unit_price"],
                            quantity=line["quantity"],
                        )
                    )
                OrderItem.objects.bulk_create(item_objects)
                created_items += len(item_objects)

        total_customers = user_model.objects.filter(is_staff=False, is_superuser=False).count()
        total_orders = Order.objects.count()

        self.stdout.write(
            self.style.SUCCESS(
                f"Customer activity seed complete. Customers: {total_customers}, "
                f"Profile: {profile}, "
                f"Renamed auto users: {renamed_customers}, Created customers: {created_customers}, "
                f"Orders added: {created_orders}, Items added: {created_items}, Total orders: {total_orders}."
            )
        )
