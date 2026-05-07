"""DRF serializers for Article, User, Newsletter, Publisher."""

from rest_framework import serializers

from news.models import Article, CustomUser, Newsletter, Publisher


class PublisherSerializer(serializers.ModelSerializer):
    """Public publisher payload."""

    class Meta:
        """Bind the serializer to :class:`news.models.Publisher`."""

        model = Publisher
        fields = ['id', 'name', 'description', 'created_at']
        read_only_fields = ['id', 'created_at']


class UserSerializer(serializers.ModelSerializer):
    """Slim user representation safe for public API responses."""

    role = serializers.CharField(read_only=True)

    class Meta:
        """Bind the serializer to :class:`news.models.CustomUser`."""

        model = CustomUser
        fields = ['id', 'username', 'email', 'role']
        read_only_fields = ['id', 'username', 'email', 'role']


class ArticleSerializer(serializers.ModelSerializer):
    """Article payload for the article endpoints.

    author is read-only (set from request.user on write).
    approved is read-only (flipped via the /approve/ endpoint).
    """

    author = serializers.PrimaryKeyRelatedField(read_only=True)
    author_username = serializers.CharField(
        source='author.username',
        read_only=True,
    )
    publisher_name = serializers.CharField(
        source='publisher.name',
        read_only=True,
        default=None,
    )

    class Meta:
        """Bind the serializer to :class:`news.models.Article`."""

        model = Article
        fields = [
            'id',
            'title',
            'content',
            'author',
            'author_username',
            'publisher',
            'publisher_name',
            'approved',
            'created_at',
        ]
        read_only_fields = [
            'id',
            'author',
            'author_username',
            'publisher_name',
            'approved',
            'created_at',
        ]


class NewsletterSerializer(serializers.ModelSerializer):
    """Newsletter payload, including the IDs of the bundled articles."""

    author = serializers.PrimaryKeyRelatedField(read_only=True)
    author_username = serializers.CharField(
        source='author.username',
        read_only=True,
    )
    articles = serializers.PrimaryKeyRelatedField(
        many=True,
        queryset=Article.objects.all(),
        required=False,
    )

    class Meta:
        """Bind the serializer to :class:`news.models.Newsletter`."""

        model = Newsletter
        fields = [
            'id',
            'title',
            'description',
            'created_at',
            'author',
            'author_username',
            'articles',
        ]
        read_only_fields = [
            'id',
            'author',
            'author_username',
            'created_at',
        ]
