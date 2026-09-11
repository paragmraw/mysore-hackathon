from django.contrib import admin
from django.contrib.auth import forms as auth_forms
from django.contrib.auth.admin import UserAdmin

from apps.accounts.models import Profile, User


class MobileUserCreationForm(auth_forms.UserCreationForm):

    class Meta(auth_forms.UserCreationForm.Meta):
        model = User
        fields = ("mobile", "name")


class MobileUserChangeForm(auth_forms.UserChangeForm):

    class Meta(auth_forms.UserChangeForm.Meta):
        model = User
        fields = "__all__"


@admin.register(User)
class MobileUserAdmin(UserAdmin):
    form = MobileUserChangeForm
    add_form = MobileUserCreationForm

    list_display = ["mobile", "name", "is_active"]
    search_fields = ["mobile", "name"]
    ordering = ["mobile"]
    list_filter = ["is_active", "is_staff", "is_superuser"]

    fieldsets = [
        (None, {"fields": ["mobile", "password"]}),
        ("Personal info", {"fields": ["name"]}),
        (
            "Permissions",
            {"fields": ["is_active", "is_staff", "is_superuser", "groups", "user_permissions"]},
        ),
        ("Important dates", {"fields": ["date_joined"]}),
    ]
    add_fieldsets = [
        (None, {"classes": ["wide"], "fields": ["mobile", "name", "password1", "password2"]}),
    ]


@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):

    list_display = ["user", "answers", "deep_check_answers"]
    search_fields = ["user__mobile"]
    raw_id_fields = ["user"]
