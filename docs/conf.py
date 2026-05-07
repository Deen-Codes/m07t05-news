"""Sphinx configuration for the news application docs."""

import os
import sys

import django

sys.path.insert(0, os.path.abspath('..'))

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'news_project.settings')
django.setup()


project = 'News Application'
author = 'Deen Ali'
copyright = '2026, Deen Ali'
release = '1.0.0'


extensions = [
    'sphinx.ext.autodoc',
    'sphinx.ext.napoleon',
    'sphinx.ext.viewcode',
]

templates_path = ['_templates']
exclude_patterns = ['_build', 'Thumbs.db', '.DS_Store']

language = 'en'


autodoc_default_options = {
    'members': True,
    'undoc-members': False,
    'show-inheritance': True,
}
autodoc_member_order = 'bysource'


html_theme = 'alabaster'
html_static_path = ['_static']
