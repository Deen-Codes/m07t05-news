"""DRF API views for the news app."""

from rest_framework import status
from rest_framework.authentication import (
    BasicAuthentication,
    SessionAuthentication,
    TokenAuthentication,
)
from rest_framework.authtoken.models import Token
from rest_framework.decorators import (
    api_view,
    authentication_classes,
    permission_classes,
)
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response

from news.models import Article, CustomUser, Newsletter
from news.permissions import (
    IsEditor,
    IsEditorOrJournalistForWrites,
    IsJournalistOrReadOnly,
)
from news.serializers import (
    ArticleSerializer,
    NewsletterSerializer,
    UserSerializer,
)


# In-memory log of approval webhook payloads (used by tests).
APPROVED_WEBHOOK_LOG = []


# ---------------------------------------------------------------------------
# Authentication
# ---------------------------------------------------------------------------


@api_view(['POST'])
@authentication_classes([])
@permission_classes([AllowAny])
def obtain_token(request):
    """Username + password -> DRF token."""
    username = request.data.get('username')
    password = request.data.get('password')
    if not username or not password:
        return Response(
            {'detail': 'username and password are required.'},
            status=status.HTTP_400_BAD_REQUEST,
        )

    user = CustomUser.objects.filter(username=username).first()
    if user is None or not user.check_password(password) or not user.is_active:
        return Response(
            {'detail': 'Invalid credentials.'},
            status=status.HTTP_401_UNAUTHORIZED,
        )

    token, _ = Token.objects.get_or_create(user=user)
    return Response(
        {
            'token': token.key,
            'user': UserSerializer(user).data,
        },
        status=status.HTTP_200_OK,
    )


# ---------------------------------------------------------------------------
# Articles
# ---------------------------------------------------------------------------


@api_view(['GET', 'POST'])
@authentication_classes([
    TokenAuthentication,
    SessionAuthentication,
    BasicAuthentication,
])
@permission_classes([IsJournalistOrReadOnly])
def articles_collection(request):
    """GET approved articles, POST a new one.

    POSTed articles save with approved=False. Author always comes
    from request.user, never the request body.
    """
    if request.method == 'GET':
        approved_articles = Article.objects.filter(approved=True)
        serializer = ArticleSerializer(approved_articles, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    serializer = ArticleSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    serializer.save(author=request.user, approved=False)
    return Response(serializer.data, status=status.HTTP_201_CREATED)


@api_view(['GET'])
@authentication_classes([
    TokenAuthentication,
    SessionAuthentication,
    BasicAuthentication,
])
@permission_classes([IsAuthenticated])
def subscribed_articles(request):
    """Approved articles matching the caller's subs.

    Union of (followed journalists' articles, subscribed publishers'
    articles). Auth required, non-readers get an empty list.
    """
    user = request.user
    journalist_ids = list(
        user.subscriptions_journalists.values_list('id', flat=True)
    )
    publisher_ids = list(
        user.subscriptions_publishers.values_list('id', flat=True)
    )
    queryset = Article.objects.filter(approved=True).filter(
        models_q(journalist_ids, publisher_ids)
    )
    serializer = ArticleSerializer(queryset.distinct(), many=True)
    return Response(serializer.data, status=status.HTTP_200_OK)


def models_q(journalist_ids, publisher_ids):
    """Build the Q filter for subscribed_articles."""
    from django.db.models import Q

    if not journalist_ids and not publisher_ids:
        # empty Q would match everything, so force an empty result
        return Q(pk__in=[])
    query = Q()
    if journalist_ids:
        query |= Q(author_id__in=journalist_ids)
    if publisher_ids:
        query |= Q(publisher_id__in=publisher_ids)
    return query


@api_view(['GET', 'PUT', 'DELETE'])
@authentication_classes([
    TokenAuthentication,
    SessionAuthentication,
    BasicAuthentication,
])
@permission_classes([IsEditorOrJournalistForWrites])
def article_detail(request, pk):
    """GET/PUT/DELETE one article.

    GET: open to anyone.
    PUT/DELETE: editors any, journalists only on their own.
    """
    try:
        article = Article.objects.get(pk=pk)
    except Article.DoesNotExist:
        return Response(
            {'detail': 'Article not found.'},
            status=status.HTTP_404_NOT_FOUND,
        )

    if request.method == 'GET':
        serializer = ArticleSerializer(article)
        return Response(serializer.data, status=status.HTTP_200_OK)

    user = request.user
    is_editor = user.groups.filter(name='Editor').exists()
    is_journalist = user.groups.filter(name='Journalist').exists()
    if is_journalist and not is_editor and article.author_id != user.id:
        return Response(
            {'detail': 'Journalists may only modify their own articles.'},
            status=status.HTTP_403_FORBIDDEN,
        )

    if request.method == 'PUT':
        serializer = ArticleSerializer(
            article, data=request.data, partial=True
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data, status=status.HTTP_200_OK)

    article.delete()
    return Response(status=status.HTTP_204_NO_CONTENT)


@api_view(['POST'])
@authentication_classes([
    TokenAuthentication,
    SessionAuthentication,
    BasicAuthentication,
])
@permission_classes([IsEditor])
def approve_article(request, pk):
    """Set approved=True (editor only). Triggers the post_save signal."""
    try:
        article = Article.objects.get(pk=pk)
    except Article.DoesNotExist:
        return Response(
            {'detail': 'Article not found.'},
            status=status.HTTP_404_NOT_FOUND,
        )
    article.approved = True
    article.save()
    return Response(
        ArticleSerializer(article).data,
        status=status.HTTP_200_OK,
    )


# ---------------------------------------------------------------------------
# Newsletters
# ---------------------------------------------------------------------------


@api_view(['GET', 'POST'])
@authentication_classes([
    TokenAuthentication,
    SessionAuthentication,
    BasicAuthentication,
])
@permission_classes([IsJournalistOrReadOnly])
def newsletters_collection(request):
    """GET all newsletters, POST a new one (journalist only)."""
    if request.method == 'GET':
        serializer = NewsletterSerializer(
            Newsletter.objects.all(), many=True
        )
        return Response(serializer.data, status=status.HTTP_200_OK)

    serializer = NewsletterSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    serializer.save(author=request.user)
    return Response(serializer.data, status=status.HTTP_201_CREATED)


# --- /api/approved/ webhook ---


@api_view(['POST'])
@authentication_classes([])
@permission_classes([AllowAny])
def approved_webhook(request):
    """Catch the approval webhook POST and stash the payload in memory.

    Tests read APPROVED_WEBHOOK_LOG to confirm the signal called us.
    """
    APPROVED_WEBHOOK_LOG.append(dict(request.data))
    return Response(
        {'received': True, 'count': len(APPROVED_WEBHOOK_LOG)},
        status=status.HTTP_201_CREATED,
    )
