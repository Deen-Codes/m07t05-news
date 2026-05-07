"""Forms for the news app."""

from django import forms
from django.contrib.auth.forms import UserCreationForm

from news.models import (
    Article,
    CustomUser,
    Newsletter,
    Publisher,
)


class RegistrationForm(UserCreationForm):
    """Account-creation form that also captures the user's role."""

    email = forms.EmailField(required=True)
    role = forms.ChoiceField(
        choices=CustomUser.ROLE_CHOICES,
        widget=forms.RadioSelect,
        initial=CustomUser.ROLE_READER,
        help_text=(
            "Pick a role. Readers read and subscribe, journalists "
            "write, editors approve and edit."
        ),
    )

    class Meta:
        """Bind the form to the project's custom user model."""

        model = CustomUser
        fields = ['username', 'email', 'role', 'password1', 'password2']


class ArticleForm(forms.ModelForm):
    """Form journalists use to write or edit an article."""

    class Meta:
        """Expose the writable article fields."""

        model = Article
        fields = ['title', 'content', 'publisher']
        widgets = {
            'content': forms.Textarea(attrs={'rows': 12}),
        }


class NewsletterForm(forms.ModelForm):
    """Newsletter form. Article picker uses checkboxes."""

    articles = forms.ModelMultipleChoiceField(
        queryset=Article.objects.filter(approved=True).order_by(
            '-created_at'
        ),
        required=False,
        widget=forms.CheckboxSelectMultiple,
        help_text=(
            "Tick every article you want to bundle into this issue. "
            "Only approved articles can be included."
        ),
    )

    class Meta:
        """Expose the writable newsletter fields."""

        model = Newsletter
        fields = ['title', 'description', 'articles']
        widgets = {
            'description': forms.Textarea(attrs={'rows': 4}),
        }


class PublisherForm(forms.ModelForm):
    """Form editors use to create or edit a publisher."""

    class Meta:
        """Expose the writable publisher fields."""

        model = Publisher
        fields = ['name', 'description']
        widgets = {
            'description': forms.Textarea(attrs={'rows': 3}),
        }


class SubscriptionForm(forms.ModelForm):
    """Form readers use to manage subscriptions.

    Multi-select replaced with checkboxes so each pick is one click.
    Journalist choices are filtered to users with the Journalist role.
    """

    class Meta:
        """Bind the form to the user model's subscription fields."""

        model = CustomUser
        fields = [
            'subscriptions_publishers',
            'subscriptions_journalists',
        ]
        widgets = {
            'subscriptions_publishers':
                forms.CheckboxSelectMultiple,
            'subscriptions_journalists':
                forms.CheckboxSelectMultiple,
        }

    def __init__(self, *args, **kwargs):
        """Restrict the journalist choices to journalist accounts."""
        super().__init__(*args, **kwargs)
        self.fields['subscriptions_journalists'].queryset = (
            CustomUser.objects.filter(
                role=CustomUser.ROLE_JOURNALIST
            ).order_by('username')
        )
        self.fields['subscriptions_publishers'].queryset = (
            Publisher.objects.all().order_by('name')
        )
