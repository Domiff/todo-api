from django.db import migrations, models

CATEGORIES = [
    ("work", "Work"),
    ("study", "Study"),
    ("personal", "Personal"),
    ("home", "Home"),
    ("shopping", "Shopping"),
    ("health", "Health"),
    ("finance", "Finance"),
    ("other", "Other"),
]


def create_categories(apps, schema_editor):
    Category = apps.get_model("todo", "Category")
    for slug, name in CATEGORIES:
        Category.objects.get_or_create(slug=slug, defaults={"name": name})


class Migration(migrations.Migration):
    dependencies = [
        ("todo", "0011_task_priority"),
    ]

    operations = [
        migrations.AlterModelOptions(
            name="category",
            options={
                "ordering": ["id"],
                "verbose_name": "Category",
                "verbose_name_plural": "Categories",
            },
        ),
        migrations.RemoveField(
            model_name="category",
            name="urgency",
        ),
        migrations.AddField(
            model_name="category",
            name="slug",
            field=models.SlugField(
                default="",
                max_length=50,
                unique=True,
                verbose_name="Slug",
            ),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name="category",
            name="name",
            field=models.CharField(default="", max_length=50, verbose_name="Name"),
            preserve_default=False,
        ),
        migrations.RunPython(create_categories, migrations.RunPython.noop),
    ]
