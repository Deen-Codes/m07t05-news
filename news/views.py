"""Browser views for the news app."""

from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect, render

from news.forms import (
    ArticleForm,
    NewsletterForm,
    PublisherForm,
    RegistrationForm,
    SubscriptionForm,
)
from news.models import Article, Newsletter, Publisher


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _in_group(user, name):
    """Return ``True`` if ``user`` is authenticated and in group ``name``."""
    return (
        user.is_authenticated
        and user.groups.filter(name=name).exists()
    )


# ---------------------------------------------------------------------------
# Public pages
# ---------------------------------------------------------------------------


def home(request):
    """Landing page - latest 10 approved articles."""
    articles = Article.objects.filter(approved=True)[:10]
    return render(request, 'news/home.html', {'articles': articles})


def article_list(request):
    """All approved articles."""
    articles = Article.objects.filter(approved=True)
    return render(
        request,
        'news/article_list.html',
        {'articles': articles},
    )


def article_detail(request, pk):
    """One article. Drafts visible only to the author or an editor."""
    article = get_object_or_404(Article, pk=pk)
    if not article.approved and not (
        _in_group(request.user, 'Editor')
        or article.author_id == getattr(request.user, 'id', None)
    ):
        return HttpResponseForbidden(
            'This article has not been approved yet.'
        )
    return render(
        request,
        'news/article_detail.html',
        {'article': article},
    )


def newsletter_list(request):
    """All newsletters."""
    newsletters = Newsletter.objects.all()
    return render(
        request,
        'news/newsletter_list.html',
        {'newsletters': newsletters},
    )


def newsletter_detail(request, pk):
    """One newsletter + its articles."""
    newsletter = get_object_or_404(Newsletter, pk=pk)
    return render(
        request,
        'news/newsletter_detail.html',
        {'newsletter': newsletter},
    )


def publisher_list(request):
    """Publishers index, with the reader's subscription state."""
    publishers = Publisher.objects.all().order_by('name')
    subscribed_ids = set()
    if request.user.is_authenticated and request.user.is_reader:
        subscribed_ids = set(
            request.user.subscriptions_publishers
            .values_list('id', flat=True)
        )
    return render(
        request,
        'news/publisher_list.html',
        {
            'publishers': publishers,
            'subscribed_ids': subscribed_ids,
        },
    )


@login_required
def publisher_create(request):
    """Create a new publisher (editor only). Creator is added as editor."""
    if not _in_group(request.user, 'Editor'):
        return HttpResponseForbidden(
            'Only editors can create publishers.'
        )
    if request.method == 'POST':
        form = PublisherForm(request.POST)
        if form.is_valid():
            publisher = form.save()
            publisher.editors.add(request.user)
            messages.success(
                request,
                f'Publisher "{publisher.name}" created. '
                'You are now listed as an editor.',
            )
            return redirect('publisher_list')
    else:
        form = PublisherForm()
    return render(
        request,
        'news/publisher_form.html',
        {'form': form},
    )


@login_required
def publisher_subscribe_toggle(request, pk):
    """Toggle a reader's subscription to a publisher (POST only)."""
    if request.method != 'POST':
        return redirect('publisher_list')
    if not _in_group(request.user, 'Reader'):
        return HttpResponseForbidden(
            'Only readers can subscribe to publishers.'
        )
    publisher = get_object_or_404(Publisher, pk=pk)
    if request.user.subscriptions_publishers.filter(
        pk=publisher.pk
    ).exists():
        request.user.subscriptions_publishers.remove(publisher)
        messages.info(
            request,
            f'Unsubscribed from {publisher.name}.',
        )
    else:
        request.user.subscriptions_publishers.add(publisher)
        messages.success(
            request,
            f'Subscribed to {publisher.name}. You will be e-mailed '
            'whenever an article from this publisher is approved.',
        )
    return redirect('publisher_list')


# ---------------------------------------------------------------------------
# Auth (login uses Django's built-in view, register is custom)
# ---------------------------------------------------------------------------


def register(request):
    """Sign up + auto-login."""
    if request.method == 'POST':
        form = RegistrationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(
                request,
                f'Welcome {user.username}! You are signed in as a '
                f'{user.get_role_display()}.',
            )
            return redirect('home')
    else:
        form = RegistrationForm()
    return render(request, 'news/register.html', {'form': form})


# ---------------------------------------------------------------------------
# Journalist-only article authoring
# ---------------------------------------------------------------------------


@login_required
def article_create(request):
    """Journalist draft form. New articles start with approved=False."""
    if not _in_group(request.user, 'Journalist'):
        return HttpResponseForbidden('Only journalists may write articles.')
    if request.method == 'POST':
        form = ArticleForm(request.POST)
        if form.is_valid():
            article = form.save(commit=False)
            article.author = request.user
            article.approved = False
            article.save()
            messages.success(request, 'Article submitted for approval.')
            return redirect('article_detail', pk=article.pk)
    else:
        form = ArticleForm()
    return render(
        request,
        'news/article_form.html',
        {'form': form, 'mode': 'create'},
    )


@login_required
def article_edit(request, pk):
    """Edit an article. Journalists only on their own; editors on any."""
    article = get_object_or_404(Article, pk=pk)
    is_editor = _in_group(request.user, 'Editor')
    is_owner = (
        _in_group(request.user, 'Journalist')
        and article.author_id == request.user.id
    )
    if not (is_editor or is_owner):
        return HttpResponseForbidden(
            'You do not have permission to edit this article.'
        )
    if request.method == 'POST':
        form = ArticleForm(request.POST, instance=article)
        if form.is_valid():
            form.save()
            messages.success(request, 'Article updated.')
            return redirect('article_detail', pk=article.pk)
    else:
        form = ArticleForm(instance=article)
    return render(
        request,
        'news/article_form.html',
        {'form': form, 'mode': 'edit'},
    )


@login_required
def article_delete(request, pk):
    """Delete an article. Same role rules as article_edit."""
    article = get_object_or_404(Article, pk=pk)
    is_editor = _in_group(request.user, 'Editor')
    is_owner = (
        _in_group(request.user, 'Journalist')
        and article.author_id == request.user.id
    )
    if not (is_editor or is_owner):
        return HttpResponseForbidden(
            'You do not have permission to delete this article.'
        )
    if request.method == 'POST':
        article.delete()
        messages.success(request, 'Article deleted.')
        return redirect('article_list')
    return render(
        request,
        'news/article_confirm_delete.html',
        {'article': article},
    )


# ---------------------------------------------------------------------------
# Editor-only approval queue
# ---------------------------------------------------------------------------


@login_required
def approval_queue(request):
    """Pending articles (editor only)."""
    if not _in_group(request.user, 'Editor'):
        return HttpResponseForbidden('Only editors may approve articles.')
    pending = Article.objects.filter(approved=False)
    return render(
        request,
        'news/approval_queue.html',
        {'articles': pending},
    )


@login_required
def article_approve(request, pk):
    """Set approved=True. The post_save signal sends the emails + webhook."""
    if not _in_group(request.user, 'Editor'):
        return HttpResponseForbidden('Only editors may approve articles.')
    article = get_object_or_404(Article, pk=pk)
    if request.method == 'POST':
        article.approved = True
        article.save()
        messages.success(
            request,
            'Article approved. Subscribers have been notified.',
        )
        return redirect('approval_queue')
    return render(
        request,
        'news/article_approve.html',
        {'article': article},
    )


# ---------------------------------------------------------------------------
# Newsletter authoring (journalists and editors)
# ---------------------------------------------------------------------------


@login_required
def newsletter_create(request):
    """Build a newsletter from approved articles (journalist or editor)."""
    if not (
        _in_group(request.user, 'Journalist')
        or _in_group(request.user, 'Editor')
    ):
        return HttpResponseForbidden(
            'Only journalists or editors may create newsletters.'
        )
    if request.method == 'POST':
        form = NewsletterForm(request.POST)
        if form.is_valid():
            newsletter = form.save(commit=False)
            newsletter.author = request.user
            newsletter.save()
            form.save_m2m()
            messages.success(request, 'Newsletter created.')
            return redirect('newsletter_detail', pk=newsletter.pk)
    else:
        form = NewsletterForm()
    return render(
        request,
        'news/newsletter_form.html',
        {'form': form, 'mode': 'create'},
    )


# ---------------------------------------------------------------------------
# Reader subscriptions
# ---------------------------------------------------------------------------


@login_required
def manage_subscriptions(request):
    """Reader's subscription form (publishers + journalists)."""
    if not _in_group(request.user, 'Reader'):
        return HttpResponseForbidden(
            'Only readers can manage subscriptions.'
        )
    if request.method == 'POST':
        form = SubscriptionForm(request.POST, instance=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, 'Subscriptions updated.')
            return redirect('manage_subscriptions')
    else:
        form = SubscriptionForm(instance=request.user)
    return render(
        request,
        'news/subscriptions.html',
        {'form': form},
    )
