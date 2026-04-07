from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("customer", "0006_alter_cartitem_product_service_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="cartitem",
            name="product_image_url",
            field=models.URLField(blank=True),
        ),
    ]
