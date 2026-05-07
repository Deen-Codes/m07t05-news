"""Admin registrations for the news app."""

from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from news.models import Article, CustomUser, Newsletter, Publisher


@admin.register(CustomUser)
class CustomUserAdmin(UserAdmin):
    """Admin for the custom user model with the role column visible."""

    list_display = ('username', 'email', 'role', 'is_staff')
    list_filter = ('role', 'is_staff', 'is_superuser')
    fieldsets = UserAdmin.fieldsets + (
        (
            'News role',
            {
                'fields': (
                    'role',
                    'subscriptions_publishers',
                    'subscriptions_journalists',
                ),
            },
        ),
    )


@admin.register(Publisher)
class PublisherAdmin(admin.ModelAdmin):
    """Admin for publisher records."""

    list_display = ('name', 'created_at')
    search_fields = ('name',)


@admin.register(Article)
class ArticleAdmin(admin.ModelAdmin):
    """Admin for article records, with the approval flag in the list."""

    list_display = ('title', 'author', 'publisher', 'approved', 'created_at')
    list_filter = ('approved', 'publisher')
    search_fields = ('title', 'content')


@admin.register(Newsletter)
class NewsletterAdmin(admin.ModelAdmin):
    """Admin for newsletter records."""

    list_display = ('title', 'author', 'created_at')
    search_fields = ('title', 'description')
