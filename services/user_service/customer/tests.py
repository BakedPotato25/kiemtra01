from io import StringIO
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.test import TestCase
from django.urls import reverse

from .legacy_users import merge_legacy_accounts
from .models import LegacyUserMapping

User = get_user_model()


class LegacyUserMergeTests(TestCase):
    def test_merge_prefers_staff_on_conflict_and_unions_roles(self):
        merged = merge_legacy_accounts(
            [
                {
                    "id": 1,
                    "source": "customer",
                    "username": "alex",
                    "email": "alex@example.com",
                    "password": "cust-hash",
                    "first_name": "Alex",
                    "last_name": "Customer",
                    "is_staff": False,
                    "is_superuser": False,
                },
                {
                    "id": 3,
                    "source": "staff",
                    "username": "alex.staff",
                    "email": "alex@example.com",
                    "password": "staff-hash",
                    "first_name": "Alex",
                    "last_name": "Staff",
                    "is_staff": True,
                    "is_superuser": False,
                },
            ]
        )

        self.assertEqual(len(merged), 1)
        account = merged[0]
        self.assertEqual(account["username"], "alex.staff")
        self.assertEqual(account["password"], "staff-hash")
        self.assertTrue(account["is_staff"])
        self.assertFalse(account["is_superuser"])
        self.assertEqual(len(account["legacy_rows"]), 2)

    def test_merge_falls_back_to_username_when_email_missing(self):
        merged = merge_legacy_accounts(
            [
                {
                    "id": 10,
                    "source": "customer",
                    "username": "kim",
                    "email": "",
                    "password": "cust",
                    "first_name": "Kim",
                    "last_name": "One",
                    "is_staff": False,
                    "is_superuser": False,
                },
                {
                    "id": 11,
                    "source": "staff",
                    "username": "kim",
                    "email": "",
                    "password": "staff",
                    "first_name": "Kim",
                    "last_name": "Two",
                    "is_staff": True,
                    "is_superuser": False,
                },
            ]
        )

        self.assertEqual(len(merged), 1)
        self.assertEqual(merged[0]["username"], "kim")
        self.assertTrue(merged[0]["is_staff"])


class MigrateLegacyUsersCommandTests(TestCase):
    def test_command_merges_existing_shared_auth_user_by_email_before_username(self):
        shared_user = User.objects.create_user(
            username="shared-auth",
            email="alex@example.com",
            password="pass12345",
        )
        colliding_user = User.objects.create_user(
            username="alex.staff",
            email="other@example.com",
            password="pass12345",
        )

        stdout = StringIO()
        customer_rows = [
            {
                "id": 1,
                "source": "customer",
                "username": "alex",
                "email": "alex@example.com",
                "password": "cust-hash",
                "first_name": "Alex",
                "last_name": "Customer",
                "is_staff": False,
                "is_superuser": False,
            }
        ]
        staff_rows = [
            {
                "id": 3,
                "source": "staff",
                "username": "alex.staff",
                "email": "alex@example.com",
                "password": "staff-hash",
                "first_name": "Alex",
                "last_name": "Staff",
                "is_staff": True,
                "is_superuser": False,
            }
        ]

        with patch(
            "customer.management.commands.migrate_legacy_users._fetch_legacy_users",
            side_effect=[customer_rows, staff_rows],
        ):
            call_command("migrate_legacy_users", stdout=stdout)

        shared_user.refresh_from_db()
        colliding_user.refresh_from_db()

        self.assertEqual(shared_user.username, "shared-auth")
        self.assertEqual(shared_user.email, "alex@example.com")
        self.assertEqual(shared_user.password, "staff-hash")
        self.assertEqual(shared_user.first_name, "Alex")
        self.assertEqual(shared_user.last_name, "Staff")
        self.assertTrue(shared_user.is_staff)
        self.assertFalse(shared_user.is_superuser)
        self.assertEqual(colliding_user.username, "alex.staff")
        self.assertEqual(colliding_user.email, "other@example.com")
        self.assertEqual(LegacyUserMapping.objects.filter(user=shared_user).count(), 2)

        mapping = LegacyUserMapping.objects.get(legacy_source="staff", legacy_user_id=3)
        self.assertIn("existing_match=email", mapping.note)
        self.assertIn("primary_role=staff", mapping.note)
        self.assertIn("username collision in shared auth", mapping.note)

        output = stdout.getvalue()
        self.assertIn("matched_email=1", output)
        self.assertIn("conflicts=1", output)


class SharedAuthFlowTests(TestCase):
    def test_customer_login_redirects_staff_user_to_staff_dashboard(self):
        user = User.objects.create_user(
            username="ops",
            email="ops@example.com",
            password="pass12345",
        )
        user.is_staff = True
        user.save(update_fields=["is_staff"])

        response = self.client.post(
            reverse("customer_login"),
            {"username": "ops", "password": "pass12345"},
        )

        self.assertRedirects(response, reverse("staff_dashboard"))


class CustomerGatewayFlowTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="customer1",
            email="customer1@example.com",
            password="pass12345",
        )
        self.client.force_login(self.user)

    def test_dashboard_accepts_legacy_service_query_but_renders_category_slug_links(self):
        categories = [
            {
                "id": 4,
                "slug": "smartphones",
                "name": "Smartphones",
                "description": "Phones for communication and capture.",
                "hero_image_url": "https://example.com/smartphones.jpg",
                "sort_order": 40,
            },
            {
                "id": 5,
                "slug": "tablets",
                "name": "Tablets",
                "description": "Portable tablets for study and work.",
                "hero_image_url": "https://example.com/tablets.jpg",
                "sort_order": 50,
            },
        ]
        products = [
            {
                "service": "smartphones",
                "category_slug": "smartphones",
                "category_name": "Smartphones",
                "id": 42,
                "name": "Pixel Frame 9",
                "description": "Clean Android experience.",
                "image_url": "https://example.com/pixel.jpg",
                "brand": "Google",
                "price": "899.00",
                "stock": 8,
            }
        ]

        with patch("customer.views.fetch_categories", return_value=categories), patch(
            "customer.views.fetch_products",
            side_effect=lambda filters=None: list(products),
        ), patch("customer.views.list_saved_items", return_value=[]), patch(
            "customer.views.list_cart_items",
            return_value=[],
        ):
            response = self.client.get(reverse("customer_dashboard"), {"service": "mobile"})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["filters"]["category"], "mobile")
        self.assertContains(response, "/customer/dashboard/?category=smartphones")
        self.assertNotContains(response, "/customer/dashboard/?category=laptop")
        self.assertContains(response, '/customer/products/smartphones/42/')
        self.assertContains(response, 'name="category_slug" value="smartphones"', html=False)

    def test_product_detail_uses_category_slug_in_forms_recommendations_and_chat_widget(self):
        product = {
            "service": "tablets",
            "category_slug": "tablets",
            "category_name": "Tablets",
            "id": 55,
            "name": "Slate Pro 11",
            "description": "Tablet for note-taking.",
            "image_url": "https://example.com/tablet.jpg",
            "brand": "Apple",
            "price": "899.00",
            "stock": 5,
        }
        related_products = [
            {
                "service": "tablets",
                "category_slug": "tablets",
                "category_name": "Tablets",
                "id": 77,
                "name": "Pad Air Neo",
                "description": "Value tablet.",
                "image_url": "https://example.com/neo.jpg",
                "brand": "Xiaomi",
                "price": "499.00",
                "stock": 12,
            }
        ]

        with patch("customer.views.fetch_categories", return_value=[]), patch(
            "customer.views.fetch_category_lookup",
            return_value={"tablets": {"hero_image_url": "https://example.com/tablets-hero.jpg"}},
        ), patch("customer.views.fetch_product_detail", return_value=product), patch(
            "customer.views.recommend_products_for_detail",
            return_value=related_products,
        ), patch("customer.views.list_cart_items", return_value=[]), patch(
            "customer.views.list_saved_items",
            return_value=[],
        ), patch("customer.views.list_compare_items", return_value=[]):
            response = self.client.get(reverse("customer_product_detail", args=["tablets", 55]))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'name="category_slug" value="tablets"', html=False)
        self.assertContains(response, 'data-category-slug="tablets"', html=False)
        self.assertContains(response, "/customer/products/tablets/77/")
