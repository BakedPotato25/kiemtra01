from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("customer", "0004_blogpost_testimonial_and_accessory"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="SavedItem",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("product_service", models.CharField(choices=[("laptop", "Laptop"), ("mobile", "Mobile"), ("accessory", "Accessory")], max_length=20)),
                ("product_id", models.PositiveIntegerField()),
                ("product_name", models.CharField(max_length=255)),
                ("product_brand", models.CharField(blank=True, max_length=120)),
                ("product_image_url", models.URLField(blank=True)),
                ("unit_price", models.DecimalField(decimal_places=2, max_digits=12)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("user", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="saved_items", to=settings.AUTH_USER_MODEL)),
            ],
            options={"ordering": ["-created_at"], "unique_together": {("user", "product_service", "product_id")}},
        ),
        migrations.CreateModel(
            name="CompareItem",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("product_service", models.CharField(choices=[("laptop", "Laptop"), ("mobile", "Mobile"), ("accessory", "Accessory")], max_length=20)),
                ("product_id", models.PositiveIntegerField()),
                ("product_name", models.CharField(max_length=255)),
                ("product_brand", models.CharField(blank=True, max_length=120)),
                ("product_image_url", models.URLField(blank=True)),
                ("unit_price", models.DecimalField(decimal_places=2, max_digits=12)),
                ("stock", models.PositiveIntegerField(default=0)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("user", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="compare_items", to=settings.AUTH_USER_MODEL)),
            ],
            options={"ordering": ["-created_at"], "unique_together": {("user", "product_service", "product_id")}},
        ),
    ]
