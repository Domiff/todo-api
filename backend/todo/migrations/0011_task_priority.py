import django.db.models.deletion
from django.db import migrations, models

URGENCY_TO_PRIORITY = {"low": 1, "middle": 2, "medium": 2, "high": 3}


def move_urgency_to_priority(apps, schema_editor):
    Category = apps.get_model("todo", "Category")
    Task = apps.get_model("todo", "Task")

    for category in Category.objects.all():
        priority = URGENCY_TO_PRIORITY.get(category.urgency.lower(), 2)
        Task.objects.filter(category=category).update(priority=priority)

    Task.objects.update(category=None)
    Category.objects.all().delete()


class Migration(migrations.Migration):
    dependencies = [
        ("todo", "0010_alter_task_options_alter_task_category_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="task",
            name="priority",
            field=models.PositiveSmallIntegerField(
                choices=[(1, "Low"), (2, "Middle"), (3, "High")],
                default=2,
                verbose_name="Priority",
            ),
        ),
        migrations.AlterField(
            model_name="task",
            name="category",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="tasks",
                to="todo.category",
                verbose_name="Category",
            ),
        ),
        migrations.RunPython(move_urgency_to_priority, migrations.RunPython.noop),
    ]
