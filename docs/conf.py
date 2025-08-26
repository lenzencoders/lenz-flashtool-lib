# Configuration file for the Sphinx documentation builder.
#
# For the full list of built-in configuration values, see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

# -- Project information -----------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#project-information

project = 'lenz-flashtool'
copyright = '2025, LENZ Encoders'
author = 'LENZ Encoders'
release = '0.1.4'

# -- General configuration ---------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#general-configuration

extensions = [
    'sphinx.ext.autodoc',
]

templates_path = ['_templates']
exclude_patterns = ['_build', 'Thumbs.db', '.DS_Store']

language = 'en'

# -- Options for HTML output -------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#options-for-html-output

html_theme = 'alabaster'
html_static_path = ['_static']


# Add the parent directory to sys.path for autodoc
import os
import sys
sys.path.insert(0, os.path.abspath('..'))

# Increase recursion limit to avoid theme errors
sys.setrecursionlimit(2000)
# Enable extensions
extensions = [
    'sphinx.ext.autodoc',
    'sphinx.ext.napoleon',
    'sphinx_autodoc_typehints',
    "sphinx_design",
]

# Set PyData Sphinx Theme
html_theme = 'pydata_sphinx_theme'
html_static_path = ['_static']
html_css_files = ['custom.css']
html_favicon = '_static/favicon.ico'

# Set Pygments style for code highlighting
pygments_style = 'monokai'
pygments_dark_style = 'monokai'

# Theme customization
html_theme_options = {
    "logo": {
        "text": "lenz-flashtool",
        "alt_text": "lenz-flashtool"
    },
    "navbar_start": ["navbar-logo"],
    "navbar_center": ["navbar-nav"],
    "navbar_end": ["theme-switcher", "navbar-icon-links"],
    "show_nav_level": 3,  # Increased to show methods in sidebar
    "use_edit_page_button": False,
    "icon_links": [],
}

# Sidebar configuration
html_sidebars = {
    #"**": ["sidebar-nav-bs", "globaltoc.html", "localtoc.html"]
    "**": ["sidebar-nav-bs", "globaltoc.html"]
}
