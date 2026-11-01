from django.contrib import admin
from unfold.admin import ModelAdmin

from auth_user.models import Profile


@admin.register(Profile)
class ProfileAdmin(ModelAdmin):
    list_display = ["user", "tg_id", "email"]
