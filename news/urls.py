"""URLs for the news app."""

from django.urls import path

from news import api_views, views


urlpatterns = [
    # Browser views
    path('', views.home, name='home'),
    path('register/', views.register, name='register'),
    path('articles/', views.article_list, name='article_list'),
    path(
        'articles/new/',
        views.article_create,
        name='article_create',
    ),
    path(
        'articles/<int:pk>/',
        views.article_detail,
        name='article_detail',
    ),
    path(
        'articles/<int:pk>/edit/',
        views.article_edit,
        name='article_edit',
    ),
    path(
        'articles/<int:pk>/delete/',
        views.article_delete,
        name='article_delete',
    ),
    path('approvals/', views.approval_queue, name='approval_queue'),
    path(
        'approvals/<int:pk>/',
        views.article_approve,
        name='article_approve',
    ),
    path('newsletters/', views.newsletter_list, name='newsletter_list'),
    path(
        'newsletters/new/',
        views.newsletter_create,
        name='newsletter_create',
    ),
    path(
        'newsletters/<int:pk>/',
        views.newsletter_detail,
        name='newsletter_detail',
    ),
    path(
        'newsletters/<int:pk>/edit/',
        views.newsletter_edit,
        name='newsletter_edit',
    ),
    path(
        'newsletters/<int:pk>/delete/',
        views.newsletter_delete,
        name='newsletter_delete',
    ),
    path(
        'dashboard/',
        views.journalist_dashboard,
        name='journalist_dashboard',
    ),
    path('publishers/', views.publisher_list, name='publisher_list'),
    path(
        'publishers/new/',
        views.publisher_create,
        name='publisher_create',
    ),
    path(
        'publishers/<int:pk>/subscribe/',
        views.publisher_subscribe_toggle,
        name='publisher_subscribe_toggle',
    ),
    path(
        'subscriptions/',
        views.manage_subscriptions,
        name='manage_subscriptions',
    ),

    # DRF API
    path('api/login/', api_views.obtain_token, name='api_login'),
    path('api/token/', api_views.obtain_token, name='api_token'),
    path(
        'api/articles/',
        api_views.articles_collection,
        name='api_articles',
    ),
    path(
        'api/articles/subscribed/',
        api_views.subscribed_articles,
        name='api_articles_subscribed',
    ),
    path(
        'api/articles/<int:pk>/',
        api_views.article_detail,
        name='api_article_detail',
    ),
    path(
        'api/articles/<int:pk>/approve/',
        api_views.approve_article,
        name='api_article_approve',
    ),
    path(
        'api/newsletters/',
        api_views.newsletters_collection,
        name='api_newsletters',
    ),
    path(
        'api/approved/',
        api_views.approved_webhook,
        name='api_approved_webhook',
    ),
]
