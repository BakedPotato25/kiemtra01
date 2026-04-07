from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("customer", "0002_order_and_brand"),
    ]

    operations = [
        migrations.AlterField(
            model_name="order",
            name="status",
            field=models.CharField(
                choices=[("pending", "Pending"), ("paid", "Paid"), ("cancelled", "Cancelled")],
                default="pending",
                max_length=20,
            ),
        ),
    ]
