"""Models: CustomUser, Publisher, Article, Newsletter."""

from django.contrib.auth.models import AbstractUser
from django.db import models


class CustomUser(AbstractUser):
    """User with a role (reader / editor / journalist)."""

    ROLE_READER = 'reader'
    ROLE_EDITOR = 'editor'
    ROLE_JOURNALIST = 'journalist'

    ROLE_CHOICES = [
        (ROLE_READER, 'Reader'),
        (ROLE_EDITOR, 'Editor'),
        (ROLE_JOURNALIST, 'Journalist'),
    ]

    role = models.CharField(
        max_length=16,
        choices=ROLE_CHOICES,
        default=ROLE_READER,
        help_text='Determines which auth.Group the user belongs to.',
    )

    subscriptions_publishers = models.ManyToManyField(
        'Publisher',
        related_name='reader_subscribers',
        blank=True,
        help_text='Publishers this Reader is subscribed to.',
    )

    subscriptions_journalists = models.ManyToManyField(
        'self',
        symmetrical=False,
        related_name='reader_followers',
        blank=True,
        help_text='Journalist accounts this Reader is subscribed to.',
    )

    class Meta:
        """Order users alphabetically by username for predictable lists."""

        ordering = ['username']

    def __str__(self):
        """Return a human-readable label including the user's role."""
        return f'{self.username} ({self.get_role_display()})'

    @property
    def is_reader(self):
        """Return ``True`` if the user has the Reader role."""
        return self.role == self.ROLE_READER

    @property
    def is_editor(self):
        """Return ``True`` if the user has the Editor role."""
        return self.role == self.ROLE_EDITOR

    @property
    def is_journalist(self):
        """Return ``True`` if the user has the Journalist role."""
        return self.role == self.ROLE_JOURNALIST

    def reader_fields(self):
        """Reader subscription fields, or ``None`` for non-readers."""
        if not self.is_reader:
            return None
        return {
            'publishers': list(self.subscriptions_publishers.all()),
            'journalists': list(self.subscriptions_journalists.all()),
        }

    def journalist_fields(self):
        """Journalist articles + newsletters, or ``None`` otherwise."""
        if not self.is_journalist:
            return None
        return {
            'articles': list(self.articles.all()),
            'newsletters': list(self.newsletters.all()),
        }


class Publisher(models.Model):
    """A publisher account, M2M-linked to editors and journalists."""

    name = models.CharField(max_length=200, unique=True)
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    editors = models.ManyToManyField(
        CustomUser,
        related_name='editor_at',
        blank=True,
        limit_choices_to={'role': CustomUser.ROLE_EDITOR},
        help_text='Editor accounts that work for this publisher.',
    )
    journalists = models.ManyToManyField(
        CustomUser,
        related_name='journalist_at',
        blank=True,
        limit_choices_to={'role': CustomUser.ROLE_JOURNALIST},
        help_text='Journalist accounts that write for this publisher.',
    )

    class Meta:
        """Sort publishers alphabetically for browse/list views."""

        ordering = ['name']

    def __str__(self):
        """Return the publisher's name."""
        return self.name


class Article(models.Model):
    """News article, written by a Journalist user.

    publisher is optional - blank means the article is independent.
    approved is flipped by an editor; the post_save signal in
    news.signals catches the False -> True transition and emails
    subscribers + POSTs to /api/approved/.
    """

    title = models.CharField(max_length=200)
    content = models.TextField()
    author = models.ForeignKey(
        CustomUser,
        on_delete=models.CASCADE,
        related_name='articles',
        limit_choices_to={'role': CustomUser.ROLE_JOURNALIST},
        help_text='Journalist who wrote the article.',
    )
    publisher = models.ForeignKey(
        Publisher,
        on_delete=models.SET_NULL,
        related_name='articles',
        null=True,
        blank=True,
        help_text='Publisher that owns the article (blank for independent).',
    )
    approved = models.BooleanField(
        default=False,
        help_text='True once an editor has approved the article.',
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        """Show newest articles first by default."""

        ordering = ['-created_at']

    def __str__(self):
        """Return the article's title and the author's username."""
        return f'{self.title} - {self.author.username}'


class Newsletter(models.Model):
    """Bundle of articles assembled by a journalist or editor."""

    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    author = models.ForeignKey(
        CustomUser,
        on_delete=models.CASCADE,
        related_name='newsletters',
        help_text='Journalist or editor who put the newsletter together.',
    )
    articles = models.ManyToManyField(
        Article,
        related_name='newsletters',
        blank=True,
        help_text='Articles in this newsletter.',
    )

    class Meta:
        """Show newest newsletters first by default."""

        ordering = ['-created_at']

    def __str__(self):
        """Return the newsletter title and author's username."""
        return f'{self.title} - {self.author.username}'
