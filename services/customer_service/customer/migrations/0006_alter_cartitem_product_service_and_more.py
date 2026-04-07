from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("customer", "0005_saveditem_compareitem"),
    ]

    operations = [
        migrations.AlterField(
            model_name="cartitem",
            name="product_service",
            field=models.CharField(
                choices=[
                    ("laptop", "Laptop"),
                    ("mobile", "Mobile"),
                    ("accessory", "Accessory"),
                ],
                max_length=20,
            ),
        ),
        migrations.AlterField(
            model_name="orderitem",
            name="product_service",
            field=models.CharField(
                choices=[
                    ("laptop", "Laptop"),
                    ("mobile", "Mobile"),
                    ("accessory", "Accessory"),
                ],
                max_length=20,
            ),
        ),
    ]
