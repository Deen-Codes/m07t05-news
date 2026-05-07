"""Initial migration for the news app."""

import django.contrib.auth.models
import django.contrib.auth.validators
import django.db.models.deletion
import django.utils.timezone
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    """Create CustomUser, Publisher, Article, Newsletter."""

    initial = True

    dependencies = [
        ('auth', '0012_alter_user_first_name_max_length'),
    ]

    operations = [
        migrations.CreateModel(
            name='CustomUser',
            fields=[
                ('id', models.BigAutoField(
                    auto_created=True, primary_key=True,
                    serialize=False, verbose_name='ID',
                )),
                ('password', models.CharField(
                    max_length=128, verbose_name='password',
                )),
                ('last_login', models.DateTimeField(
                    blank=True, null=True, verbose_name='last login',
                )),
                ('is_superuser', models.BooleanField(
                    default=False,
                    help_text=(
                        'Designates that this user has all permissions '
                        'without explicitly assigning them.'
                    ),
                    verbose_name='superuser status',
                )),
                ('username', models.CharField(
                    error_messages={
                        'unique': 'A user with that username already exists.',
                    },
                    help_text=(
                        'Required. 150 characters or fewer. Letters, '
                        'digits and @/./+/-/_ only.'
                    ),
                    max_length=150,
                    unique=True,
                    validators=[
                        django.contrib.auth.validators.
                        UnicodeUsernameValidator(),
                    ],
                    verbose_name='username',
                )),
                ('first_name', models.CharField(
                    blank=True, max_length=150,
                    verbose_name='first name',
                )),
                ('last_name', models.CharField(
                    blank=True, max_length=150,
                    verbose_name='last name',
                )),
                ('email', models.EmailField(
                    blank=True, max_length=254,
                    verbose_name='email address',
                )),
                ('is_staff', models.BooleanField(
                    default=False,
                    help_text=(
                        'Designates whether the user can log into '
                        'this admin site.'
                    ),
                    verbose_name='staff status',
                )),
                ('is_active', models.BooleanField(
                    default=True,
                    help_text=(
                        'Designates whether this user should be treated '
                        'as active. Unselect this instead of deleting '
                        'accounts.'
                    ),
                    verbose_name='active',
                )),
                ('date_joined', models.DateTimeField(
                    default=django.utils.timezone.now,
                    verbose_name='date joined',
                )),
                ('role', models.CharField(
                    choices=[
                        ('reader', 'Reader'),
                        ('editor', 'Editor'),
                        ('journalist', 'Journalist'),
                    ],
                    default='reader',
                    help_text=(
                        'Determines which auth.Group the user belongs to.'
                    ),
                    max_length=16,
                )),
                ('groups', models.ManyToManyField(
                    blank=True,
                    help_text=(
                        'The groups this user belongs to.'
                    ),
                    related_name='user_set',
                    related_query_name='user',
                    to='auth.group',
                    verbose_name='groups',
                )),
                ('user_permissions', models.ManyToManyField(
                    blank=True,
                    help_text='Specific permissions for this user.',
                    related_name='user_set',
                    related_query_name='user',
                    to='auth.permission',
                    verbose_name='user permissions',
                )),
            ],
            options={
                'ordering': ['username'],
            },
            managers=[
                ('objects', django.contrib.auth.models.UserManager()),
            ],
        ),
        migrations.CreateModel(
            name='Publisher',
            fields=[
                ('id', models.BigAutoField(
                    auto_created=True, primary_key=True,
                    serialize=False, verbose_name='ID',
                )),
                ('name', models.CharField(max_length=200, unique=True)),
                ('description', models.TextField(blank=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('editors', models.ManyToManyField(
                    blank=True,
                    help_text=(
                        'Editor accounts that work for this publisher.'
                    ),
                    limit_choices_to={'role': 'editor'},
                    related_name='editor_at',
                    to=settings.AUTH_USER_MODEL,
                )),
                ('journalists', models.ManyToManyField(
                    blank=True,
                    help_text=(
                        'Journalist accounts that write for this publisher.'
                    ),
                    limit_choices_to={'role': 'journalist'},
                    related_name='journalist_at',
                    to=settings.AUTH_USER_MODEL,
                )),
            ],
            options={
                'ordering': ['name'],
            },
        ),
        migrations.AddField(
            model_name='customuser',
            name='subscriptions_publishers',
            field=models.ManyToManyField(
                blank=True,
                help_text='Publishers this Reader is subscribed to.',
                related_name='reader_subscribers',
                to='news.publisher',
            ),
        ),
        migrations.AddField(
            model_name='customuser',
            name='subscriptions_journalists',
            field=models.ManyToManyField(
                blank=True,
                help_text='Journalist accounts this Reader is subscribed to.',
                related_name='reader_followers',
                to=settings.AUTH_USER_MODEL,
            ),
        ),
        migrations.CreateModel(
            name='Article',
            fields=[
                ('id', models.BigAutoField(
                    auto_created=True, primary_key=True,
                    serialize=False, verbose_name='ID',
                )),
                ('title', models.CharField(max_length=200)),
                ('content', models.TextField()),
                ('approved', models.BooleanField(
                    default=False,
                    help_text=(
                        'True once an editor has approved the article.'
                    ),
                )),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('author', models.ForeignKey(
                    help_text='Journalist who wrote the article.',
                    limit_choices_to={'role': 'journalist'},
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='articles',
                    to=settings.AUTH_USER_MODEL,
                )),
                ('publisher', models.ForeignKey(
                    blank=True,
                    help_text=(
                        'Publisher that owns the article '
                        '(blank for independent).'
                    ),
                    null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    related_name='articles',
                    to='news.publisher',
                )),
            ],
            options={
                'ordering': ['-created_at'],
            },
        ),
        migrations.CreateModel(
            name='Newsletter',
            fields=[
                ('id', models.BigAutoField(
                    auto_created=True, primary_key=True,
                    serialize=False, verbose_name='ID',
                )),
                ('title', models.CharField(max_length=200)),
                ('description', models.TextField(blank=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('articles', models.ManyToManyField(
                    blank=True,
                    help_text='Articles in this newsletter.',
                    related_name='newsletters',
                    to='news.article',
                )),
                ('author', models.ForeignKey(
                    help_text=(
                        'Journalist or editor who put the newsletter together.'
                    ),
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='newsletters',
                    to=settings.AUTH_USER_MODEL,
                )),
            ],
            options={
                'ordering': ['-created_at'],
            },
        ),
    ]
