from django.db import models


class Category(models.Model):
    slug = models.SlugField(max_length=50, unique=True, verbose_name="Slug")
    name = models.CharField(max_length=50, verbose_name="Name")

    class Meta:
        ordering = ["id"]
        verbose_name = "Category"
        verbose_name_plural = "Categories"

    def __str__(self):
        return self.name


class Task(models.Model):
    class Priority(models.IntegerChoices):
        LOW = 1, "Low"
        MIDDLE = 2, "Middle"
        HIGH = 3, "High"

    creator = models.ForeignKey("auth_user.Profile", on_delete=models.CASCADE)
    title = models.CharField(max_length=200)
    body = models.TextField()
    completed = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    deadline = models.DateTimeField()
    priority = models.PositiveSmallIntegerField(
        choices=Priority.choices,
        default=Priority.MIDDLE,
        verbose_name="Priority",
    )
    category = models.ForeignKey(
        Category,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="tasks",
        verbose_name="Category",
    )

    class Meta:
        ordering = ["-updated_at"]
        indexes = [
            models.Index(fields=["-created_at"]),
        ]

    def __str__(self):
        return self.title
