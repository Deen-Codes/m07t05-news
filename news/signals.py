"""Signal handlers for the news app."""

import logging

import requests
from django.conf import settings
from django.contrib.auth.models import Group
from django.core.mail import send_mail
from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver

from news.models import Article, CustomUser


logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Group / role synchronisation
# ---------------------------------------------------------------------------


@receiver(post_save, sender=CustomUser)
def sync_user_group(sender, instance, created, **kwargs):
    """Match auth.Group membership to CustomUser.role on save."""
    role_to_group = {
        CustomUser.ROLE_READER: 'Reader',
        CustomUser.ROLE_EDITOR: 'Editor',
        CustomUser.ROLE_JOURNALIST: 'Journalist',
    }
    target_group_name = role_to_group.get(instance.role)
    if not target_group_name:
        return

    # drop the other two role groups so role changes don't stack
    for other_name in role_to_group.values():
        if other_name == target_group_name:
            continue
        try:
            other = Group.objects.get(name=other_name)
        except Group.DoesNotExist:
            continue
        instance.groups.remove(other)

    try:
        target_group = Group.objects.get(name=target_group_name)
    except Group.DoesNotExist:
        # group not seeded yet, skip; next save after seed_groups picks it up
        return
    instance.groups.add(target_group)


# ---------------------------------------------------------------------------
# Article approval workflow
# ---------------------------------------------------------------------------


@receiver(pre_save, sender=Article)
def remember_previous_approval(sender, instance, **kwargs):
    """Cache previous ``approved`` value for the post-save handler."""
    if instance.pk is None:
        instance._was_approved = False
        return
    try:
        previous = Article.objects.only('approved').get(pk=instance.pk)
    except Article.DoesNotExist:
        instance._was_approved = False
    else:
        instance._was_approved = previous.approved


@receiver(post_save, sender=Article)
def article_approval_handler(sender, instance, created, **kwargs):
    """Fires notifications on the False -> True approval transition."""
    if not instance.approved:
        return
    was_approved = getattr(instance, '_was_approved', False)
    if was_approved:
        return

    notify_subscribers(instance)
    post_to_approved_webhook(instance)


def notify_subscribers(article):
    """Email subscribers of the article's journalist + publisher."""
    recipients = set()

    journalist_subs = article.author.reader_followers.all()
    for reader in journalist_subs:
        if reader.email:
            recipients.add(reader.email)

    if article.publisher_id is not None:
        publisher_subs = article.publisher.reader_subscribers.all()
        for reader in publisher_subs:
            if reader.email:
                recipients.add(reader.email)

    if not recipients:
        return

    subject = f'New article approved: {article.title}'
    body = (
        f'A new article by {article.author.username} has just been '
        f'approved.\n\n'
        f'Title: {article.title}\n\n'
        f'{article.content}\n'
    )
    try:
        send_mail(
            subject=subject,
            message=body,
            from_email=getattr(
                settings,
                'DEFAULT_FROM_EMAIL',
                'news-app@example.com',
            ),
            recipient_list=sorted(recipients),
            fail_silently=True,
        )
    except Exception as exc:  # pragma: no cover - defensive logging
        logger.warning('Could not send approval email: %s', exc)


def post_to_approved_webhook(article):
    """POST the article JSON to APPROVED_ARTICLE_WEBHOOK."""
    url = getattr(settings, 'APPROVED_ARTICLE_WEBHOOK', '')
    if not url:
        return
    payload = {
        'id': article.pk,
        'title': article.title,
        'content': article.content,
        'author': article.author.username,
        'publisher': (
            article.publisher.name if article.publisher_id else None
        ),
    }
    try:
        requests.post(url, json=payload, timeout=5)
    except requests.RequestException as exc:
        # webhook is best-effort: log a one-liner and move on
        logger.warning('Could not POST approved article to %s: %s', url, exc)
