"""``python manage.py seed_groups`` - create role auth groups."""

from django.contrib.auth.models import Group, Permission
from django.contrib.contenttypes.models import ContentType
from django.core.management.base import BaseCommand

from news.models import Article, Newsletter


GROUP_PERMISSIONS = {
    'Reader': {
        'article': ['view'],
        'newsletter': ['view'],
    },
    'Editor': {
        'article': ['view', 'change', 'delete'],
        'newsletter': ['view', 'change', 'delete'],
    },
    'Journalist': {
        'article': ['add', 'view', 'change', 'delete'],
        'newsletter': ['add', 'view', 'change', 'delete'],
    },
}


class Command(BaseCommand):
    """Create the Reader / Editor / Journalist groups idempotently."""

    help = (
        'Create the Reader, Editor, and Journalist groups with '
        'their model permissions.'
    )

    def handle(self, *args, **options):
        """Create or update each group and attach the right permissions."""
        article_ct = ContentType.objects.get_for_model(Article)
        newsletter_ct = ContentType.objects.get_for_model(Newsletter)

        ct_map = {
            'article': article_ct,
            'newsletter': newsletter_ct,
        }

        for group_name, perms_by_model in GROUP_PERMISSIONS.items():
            group, created = Group.objects.get_or_create(name=group_name)
            verb = 'Created' if created else 'Updated'
            permission_objects = []
            for model_label, actions in perms_by_model.items():
                ct = ct_map[model_label]
                for action in actions:
                    codename = f'{action}_{model_label}'
                    try:
                        perm = Permission.objects.get(
                            codename=codename,
                            content_type=ct,
                        )
                    except Permission.DoesNotExist:
                        self.stderr.write(
                            f'  Missing permission {codename} - '
                            'skipping; run migrate first.'
                        )
                        continue
                    permission_objects.append(perm)
            group.permissions.set(permission_objects)
            self.stdout.write(
                f'{verb} group {group_name} with '
                f'{len(permission_objects)} permission(s).'
            )

        self.stdout.write(self.style.SUCCESS('Group seed complete.'))
