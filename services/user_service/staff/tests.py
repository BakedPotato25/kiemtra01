from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from unittest.mock import patch

User = get_user_model()


class StaffLoginTests(TestCase):
    def test_staff_login_rejects_superuser_accounts(self):
        User.objects.create_superuser(
            username="root",
            email="root@example.com",
            password="pass12345",
        )

        response = self.client.post(
            reverse("staff_login"),
            {"username": "root", "password": "pass12345"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Admin accounts should sign in via /admin/.")


class StaffGatewayFlowTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="ops",
            email="ops@example.com",
            password="pass12345",
        )
        self.user.is_staff = True
        self.user.save(update_fields=["is_staff"])
        self.client.force_login(self.user)

    def test_staff_items_accepts_legacy_service_query_but_renders_category_filters(self):
        categories = [
            {"id": 4, "slug": "smartphones", "name": "Smartphones"},
            {"id": 5, "slug": "tablets", "name": "Tablets"},
        ]
        items = [
            {
                "service": "smartphones",
                "category_slug": "smartphones",
                "category_name": "Smartphones",
                "id": 9,
                "name": "Pixel Frame 9",
                "description": "Clean Android phone.",
                "image_url": "https://example.com/pixel.jpg",
                "brand": "Google",
                "price": "899.00",
                "stock": 8,
            }
        ]

        with patch("staff.views.fetch_categories", return_value=categories), patch(
            "staff.views.fetch_products",
            return_value=items,
        ):
            response = self.client.get(reverse("staff_items"), {"service": "smartphones"})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["selected_category"], "smartphones")
        self.assertContains(response, "/staff/items/?category=smartphones")
        self.assertContains(response, 'name="return_category" value="smartphones"', html=False)
        self.assertNotContains(response, 'name="return_service"', html=False)

    def test_staff_orders_page_renders_upstream_orders_and_updates_shipping(self):
        orders = [
            {
                "id": 21,
                "user_id": 7,
                "payment_status": "paid",
                "shipping_status": "preparing",
                "total_amount": "199.00",
                "created_at": "2026-04-20T01:00:00Z",
                "shipping": {
                    "recipient_name": "Nguyen Van A",
                    "phone": "0123456789",
                    "city_or_region": "HCMC",
                    "country": "VN",
                },
                "items": [{"product_name": "QuietBeat ANC", "quantity": 1}],
            }
        ]

        with patch("staff.views.fetch_staff_orders", return_value=orders):
            response = self.client.get(reverse("staff_orders"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "QuietBeat ANC")
        self.assertContains(response, "PREPARING")

        with patch("staff.views.update_shipping_status", return_value=(True, {"id": 21}, None)):
            post_response = self.client.post(
                reverse("staff_orders"),
                {"order_id": 21, "shipping_status": "shipped"},
            )

        self.assertRedirects(post_response, "/staff/orders/")
