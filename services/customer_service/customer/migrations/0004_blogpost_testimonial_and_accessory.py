from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("customer", "0003_order_status_pending"),
    ]

    operations = [
        migrations.CreateModel(
            name="BlogPost",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("title", models.CharField(max_length=220)),
                ("slug", models.SlugField(unique=True)),
                ("category", models.CharField(max_length=80)),
                ("author", models.CharField(max_length=120)),
                ("excerpt", models.TextField()),
                ("body", models.TextField()),
                ("hero_image_url", models.URLField(blank=True)),
                ("published_at", models.DateField()),
                ("created_at", models.DateTimeField(auto_now_add=True)),
            ],
            options={"ordering": ["-published_at", "-id"]},
        ),
        migrations.CreateModel(
            name="Testimonial",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("name", models.CharField(max_length=120)),
                ("role", models.CharField(max_length=120)),
                ("rating", models.PositiveSmallIntegerField(default=5)),
                ("quote", models.TextField()),
                ("avatar_url", models.URLField(blank=True)),
                ("is_featured", models.BooleanField(default=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
            ],
            options={"ordering": ["-created_at"]},
        ),
    ]
