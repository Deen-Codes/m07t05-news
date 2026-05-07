"""Unit tests for the news app."""

from unittest.mock import patch

from django.contrib.auth.models import Group
from django.core import mail
from django.core.management import call_command
from django.test import TestCase
from rest_framework import status
from rest_framework.authtoken.models import Token
from rest_framework.test import APIClient

from news.api_views import APPROVED_WEBHOOK_LOG
from news.models import Article, CustomUser, Newsletter, Publisher


def _make_user(username, role, email=None):
    """Create a user with ``role``; the signal assigns the group."""
    return CustomUser.objects.create_user(
        username=username,
        password='pass1234!',
        email=email or f'{username}@example.com',
        role=role,
    )


class BaseAPITestCase(TestCase):
    """Shared fixture: groups seeded plus one user of each role."""

    @classmethod
    def setUpTestData(cls):
        """Seed the auth groups exactly once per test class."""
        call_command('seed_groups', verbosity=0)

    def setUp(self):
        """Create one user of each role plus a publisher for FK convenience."""
        self.reader = _make_user('reader1', CustomUser.ROLE_READER)
        self.journalist = _make_user(
            'journo1', CustomUser.ROLE_JOURNALIST,
        )
        self.editor = _make_user('editor1', CustomUser.ROLE_EDITOR)
        self.publisher = Publisher.objects.create(name='Daily Planet')
        self.publisher.editors.add(self.editor)
        self.publisher.journalists.add(self.journalist)
        APPROVED_WEBHOOK_LOG.clear()
        mail.outbox = []
        self.client = APIClient()

    def login_as(self, user):
        """Authenticate the test client as ``user`` via DRF token auth."""
        token, _ = Token.objects.get_or_create(user=user)
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {token.key}')


# ---------------------------------------------------------------------------
# Group sync signal
# ---------------------------------------------------------------------------


class GroupSyncSignalTests(BaseAPITestCase):
    """The post-save signal puts users in the matching auth group."""

    def test_reader_lands_in_reader_group(self):
        """A user created with the Reader role is in the Reader group."""
        self.assertTrue(
            self.reader.groups.filter(name='Reader').exists()
        )
        self.assertFalse(
            self.reader.groups.filter(name='Editor').exists()
        )

    def test_role_change_moves_groups(self):
        """Changing role from Journalist to Editor swaps the group."""
        self.journalist.role = CustomUser.ROLE_EDITOR
        self.journalist.save()
        self.assertTrue(
            self.journalist.groups.filter(name='Editor').exists()
        )
        self.assertFalse(
            self.journalist.groups.filter(name='Journalist').exists()
        )


# ---------------------------------------------------------------------------
# Token authentication
# ---------------------------------------------------------------------------


class AuthEndpointTests(BaseAPITestCase):
    """``/api/login/`` exchanges credentials for a DRF token."""

    def test_login_with_correct_credentials_returns_token(self):
        """Valid credentials return 200 + a token + the user payload."""
        response = self.client.post(
            '/api/login/',
            {'username': 'reader1', 'password': 'pass1234!'},
            format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('token', response.data)
        self.assertEqual(response.data['user']['username'], 'reader1')

    def test_login_with_bad_password_is_401(self):
        """Wrong password is rejected with 401, not 200."""
        response = self.client.post(
            '/api/login/',
            {'username': 'reader1', 'password': 'wrong'},
            format='json',
        )
        self.assertEqual(
            response.status_code, status.HTTP_401_UNAUTHORIZED
        )

    def test_login_missing_fields_is_400(self):
        """Missing username/password returns 400."""
        response = self.client.post('/api/login/', {}, format='json')
        self.assertEqual(
            response.status_code, status.HTTP_400_BAD_REQUEST
        )


# ---------------------------------------------------------------------------
# Article list / create
# ---------------------------------------------------------------------------


class ArticleCreateTests(BaseAPITestCase):
    """Only journalists can POST a new article."""

    def _payload(self):
        """Return a minimal valid article payload."""
        return {
            'title': 'Hello World',
            'content': 'Body of the article.',
            'publisher': self.publisher.id,
        }

    def test_journalist_can_create(self):
        """A journalist's POST returns 201 with author auto-attached."""
        self.login_as(self.journalist)
        response = self.client.post(
            '/api/articles/', self._payload(), format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['author'], self.journalist.id)
        self.assertFalse(response.data['approved'])

    def test_reader_cannot_create_article(self):
        """A reader's POST is forbidden (403)."""
        self.login_as(self.reader)
        response = self.client.post(
            '/api/articles/', self._payload(), format='json',
        )
        self.assertEqual(
            response.status_code, status.HTTP_403_FORBIDDEN
        )

    def test_unauthenticated_post_is_401(self):
        """Anonymous POSTs are rejected with 401."""
        response = self.client.post(
            '/api/articles/', self._payload(), format='json',
        )
        self.assertEqual(
            response.status_code, status.HTTP_401_UNAUTHORIZED
        )

    def test_list_returns_only_approved(self):
        """Unapproved articles do not appear in the public list."""
        Article.objects.create(
            title='Pending', content='-', author=self.journalist,
            approved=False,
        )
        Article.objects.create(
            title='Approved', content='-', author=self.journalist,
            approved=True,
        )
        response = self.client.get('/api/articles/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        titles = [a['title'] for a in response.data]
        self.assertIn('Approved', titles)
        self.assertNotIn('Pending', titles)


# ---------------------------------------------------------------------------
# Article detail / update / delete
# ---------------------------------------------------------------------------


class ArticleEditDeleteTests(BaseAPITestCase):
    """PUT and DELETE behaviour by role."""

    def setUp(self):
        """Seed one approved article authored by ``self.journalist``."""
        super().setUp()
        self.article = Article.objects.create(
            title='Original',
            content='Body.',
            author=self.journalist,
            publisher=self.publisher,
            approved=True,
        )

    def test_editor_can_update_any_article(self):
        """An editor can PUT any article and get 200 back."""
        self.login_as(self.editor)
        response = self.client.put(
            f'/api/articles/{self.article.id}/',
            {'title': 'Edited', 'content': 'Body.'},
            format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.article.refresh_from_db()
        self.assertEqual(self.article.title, 'Edited')

    def test_editor_can_delete(self):
        """An editor's DELETE returns 204 and removes the row."""
        self.login_as(self.editor)
        response = self.client.delete(
            f'/api/articles/{self.article.id}/',
        )
        self.assertEqual(
            response.status_code, status.HTTP_204_NO_CONTENT
        )
        self.assertFalse(
            Article.objects.filter(id=self.article.id).exists()
        )

    def test_reader_cannot_delete(self):
        """A reader's DELETE is forbidden (403)."""
        self.login_as(self.reader)
        response = self.client.delete(
            f'/api/articles/{self.article.id}/',
        )
        self.assertEqual(
            response.status_code, status.HTTP_403_FORBIDDEN
        )

    def test_journalist_cannot_modify_other_journalists_work(self):
        """Journalist B cannot edit Journalist A's article (403)."""
        other = _make_user('journo2', CustomUser.ROLE_JOURNALIST)
        self.login_as(other)
        response = self.client.put(
            f'/api/articles/{self.article.id}/',
            {'title': 'Hijack', 'content': 'Body.'},
            format='json',
        )
        self.assertEqual(
            response.status_code, status.HTTP_403_FORBIDDEN
        )

    def test_missing_article_returns_404(self):
        """A GET on a non-existent ID returns 404."""
        response = self.client.get('/api/articles/9999/')
        self.assertEqual(
            response.status_code, status.HTTP_404_NOT_FOUND
        )


# ---------------------------------------------------------------------------
# Subscriptions
# ---------------------------------------------------------------------------


class SubscribedArticlesTests(BaseAPITestCase):
    """``/api/articles/subscribed/`` filters by the caller's subscriptions."""

    def setUp(self):
        """Create one publisher article and one independent article."""
        super().setUp()
        self.indep_journalist = _make_user(
            'solo', CustomUser.ROLE_JOURNALIST,
        )
        self.publisher_article = Article.objects.create(
            title='Publisher article',
            content='-',
            author=self.journalist,
            publisher=self.publisher,
            approved=True,
        )
        self.independent_article = Article.objects.create(
            title='Independent article',
            content='-',
            author=self.indep_journalist,
            approved=True,
        )

    def test_reader_with_no_subscriptions_gets_empty_list(self):
        """An empty subscription set yields an empty response."""
        self.login_as(self.reader)
        response = self.client.get('/api/articles/subscribed/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, [])

    def test_reader_only_sees_subscribed_publisher(self):
        """Subscribing to the publisher returns only that publisher's work."""
        self.reader.subscriptions_publishers.add(self.publisher)
        self.login_as(self.reader)
        response = self.client.get('/api/articles/subscribed/')
        titles = [a['title'] for a in response.data]
        self.assertIn('Publisher article', titles)
        self.assertNotIn('Independent article', titles)

    def test_reader_can_combine_publisher_and_journalist_subs(self):
        """Subscribing to both a publisher and a journalist unions results."""
        self.reader.subscriptions_publishers.add(self.publisher)
        self.reader.subscriptions_journalists.add(self.indep_journalist)
        self.login_as(self.reader)
        response = self.client.get('/api/articles/subscribed/')
        titles = sorted(a['title'] for a in response.data)
        self.assertEqual(
            titles, ['Independent article', 'Publisher article'],
        )

    def test_unauthenticated_subscribed_call_is_401(self):
        """Anonymous calls to /subscribed/ are rejected with 401."""
        response = self.client.get('/api/articles/subscribed/')
        self.assertEqual(
            response.status_code, status.HTTP_401_UNAUTHORIZED
        )


# ---------------------------------------------------------------------------
# Approval + signal logic (with mocking)
# ---------------------------------------------------------------------------


class ApprovalSignalTests(BaseAPITestCase):
    """Approving an article fires the e-mail and webhook side effects."""

    def setUp(self):
        """Subscribe ``self.reader`` to ``self.journalist``."""
        super().setUp()
        self.reader.subscriptions_journalists.add(self.journalist)
        self.article = Article.objects.create(
            title='Pending',
            content='Body.',
            author=self.journalist,
            publisher=self.publisher,
            approved=False,
        )

    def test_only_editor_can_approve(self):
        """Non-editors hit /approve/ and get 403."""
        self.login_as(self.journalist)
        response = self.client.post(
            f'/api/articles/{self.article.id}/approve/',
        )
        self.assertEqual(
            response.status_code, status.HTTP_403_FORBIDDEN
        )

    @patch('news.signals.requests.post')
    def test_editor_approval_triggers_email_and_webhook(self, mock_post):
        """Editor approval emails subscribers and posts to webhook."""
        mock_post.return_value.status_code = 201
        self.login_as(self.editor)
        response = self.client.post(
            f'/api/articles/{self.article.id}/approve/',
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.article.refresh_from_db()
        self.assertTrue(self.article.approved)

        # E-mail outbox should contain exactly one notification.
        self.assertEqual(len(mail.outbox), 1)
        email = mail.outbox[0]
        self.assertIn('Pending', email.subject)
        self.assertIn(self.reader.email, email.to)

        # The webhook helper called requests.post exactly once.
        self.assertEqual(mock_post.call_count, 1)
        called_url = mock_post.call_args[0][0]
        self.assertIn('/api/approved/', called_url)

    @patch('news.signals.requests.post')
    def test_second_save_does_not_refire_signal(self, mock_post):
        """Re-saving an approved article must not re-trigger the signal."""
        self.login_as(self.editor)
        self.client.post(
            f'/api/articles/{self.article.id}/approve/',
        )
        mail.outbox = []
        mock_post.reset_mock()

        # Save again with no transition; nothing should fire.
        self.article.refresh_from_db()
        self.article.save()
        self.assertEqual(len(mail.outbox), 0)
        self.assertEqual(mock_post.call_count, 0)

    def test_loopback_webhook_records_payload(self):
        """The /api/approved/ endpoint stores whatever it receives."""
        APPROVED_WEBHOOK_LOG.clear()
        response = self.client.post(
            '/api/approved/',
            {'id': 99, 'title': 'External post'},
            format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(len(APPROVED_WEBHOOK_LOG), 1)
        self.assertEqual(APPROVED_WEBHOOK_LOG[0]['title'], 'External post')


# ---------------------------------------------------------------------------
# Newsletters
# ---------------------------------------------------------------------------


class NewsletterTests(BaseAPITestCase):
    """Listing and creating newsletters per role."""

    def test_journalist_can_create_newsletter(self):
        """A journalist's POST creates a newsletter (201)."""
        self.login_as(self.journalist)
        response = self.client.post(
            '/api/newsletters/',
            {'title': 'Weekly', 'description': 'Top stories'},
            format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['author'], self.journalist.id)

    def test_reader_cannot_create_newsletter(self):
        """A reader's POST is forbidden (403)."""
        self.login_as(self.reader)
        response = self.client.post(
            '/api/newsletters/',
            {'title': 'Bad', 'description': '-'},
            format='json',
        )
        self.assertEqual(
            response.status_code, status.HTTP_403_FORBIDDEN
        )

    def test_anyone_can_list_newsletters(self):
        """GET on the newsletter collection is public."""
        Newsletter.objects.create(
            title='Public', description='-', author=self.journalist,
        )
        response = self.client.get('/api/newsletters/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertGreaterEqual(len(response.data), 1)


# ---------------------------------------------------------------------------
# Reader / journalist field contract
# ---------------------------------------------------------------------------


class CustomUserFieldContractTests(BaseAPITestCase):
    """reader_fields() / journalist_fields() return None correctly."""

    def test_reader_journalist_fields_is_none(self):
        """A reader's ``journalist_fields`` accessor returns None."""
        self.assertIsNone(self.reader.journalist_fields())
        self.assertIsNotNone(self.reader.reader_fields())

    def test_journalist_reader_fields_is_none(self):
        """A journalist's ``reader_fields`` accessor returns None."""
        self.assertIsNone(self.journalist.reader_fields())
        self.assertIsNotNone(self.journalist.journalist_fields())
