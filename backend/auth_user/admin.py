from django.contrib import admin
from unfold.admin import ModelAdmin

from auth_user.models import TgProfile, WebProfile

base_list_display = ["user", "username", "first_name", "last_name"]


@admin.register(TgProfile)
class TgProfileAdmin(ModelAdmin):
    list_display = base_list_display + ["tg_id"]


@admin.register(WebProfile)
class WebProfileAdmin(ModelAdmin):
    list_display = base_list_display + ["email"]
