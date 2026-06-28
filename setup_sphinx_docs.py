import os
import subprocess
import shutil


def setup_sphinx_project(project_name, author, version, docs_dir="docs", module_name=None, submodules=None):
    """
    Sets up or updates a Sphinx documentation project for lenz-flashtool library.

    Args:
        project_name (str): Name of the project/library.
        author (str): Author name for the documentation.
        version (str): Version of the library (e.g., '0.1.0').
        docs_dir (str): Directory where documentation will be created/updated (default: 'docs').
        module_name (str, optional): Name of the module to document (default: project_name.lower()).
        submodules (list, optional): List of submodule names to document (e.g., ['utils', 'biss']).

    Returns:
        None
    """
    if module_name is None:
        module_name = project_name.lower().replace("-", "_")
    if submodules is None:
        submodules = []

    # Create docs directory if it doesn't exist
    if not os.path.exists(docs_dir):
        os.makedirs(docs_dir)
        sphinx_init_needed = True
    else:
        sphinx_init_needed = False
        print(f"Directory '{docs_dir}' already exists. Skipping sphinx-quickstart.")

    # Clean up old .rst files to avoid conflicts, excluding static pages
    for rst_file in os.listdir(docs_dir):
        if rst_file.endswith(".rst") and rst_file not in ["index.rst", "api.rst", "getting_started.rst", "installation.rst", "usage.rst"]:
            os.remove(os.path.join(docs_dir, rst_file))
            print(f"Removed old {rst_file} to avoid conflicts")

    # Run sphinx-quickstart if needed
    if sphinx_init_needed:
        try:
            subprocess.run([
                "sphinx-quickstart",
                "--quiet",
                "--project", project_name,
                "--author", author,
                "--release", version,
                "--language", "en",
                "--ext-autodoc",
                "--makefile",
                "--no-batchfile",
                docs_dir
            ], check=True)
            print(f"Sphinx project initialized in {docs_dir}")
        except subprocess.CalledProcessError as e:
            print(f"Error initializing Sphinx: {e}")
            return

    # Check if the module is importable
    try:
        __import__(module_name)
        print(f"Module '{module_name}' is importable")
    except ImportError as e:
        print(f"Warning: Cannot import '{module_name}': {e}")
        print("Ensure the module is in the parent directory and has an __init__.py if it's a package.")

    # Update conf.py to include the source directory, extensions, PyData theme, and Pygments style
    conf_path = os.path.join(docs_dir, "conf.py")
    conf_content = ""
    if os.path.exists(conf_path):
        with open(conf_path, "r") as f:
            conf_content = f.read()

    # Ensure necessary extensions, sys.path, theme, Pygments style, and sidebar settings are in conf.py
    conf_snippet = """
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
pygments_style = 'default'
pygments_dark_style = 'monokai'

# Theme customization
html_theme_options = {{
    "logo": {{
        "text": "{0}",
        "alt_text": "{0}"
    }},
    "navbar_start": ["navbar-logo"],
    "navbar_center": ["navbar-nav"],
    "navbar_end": ["theme-switcher", "navbar-icon-links"],
    "show_nav_level": 3,  # Increased to show methods in sidebar
    "use_edit_page_button": False,
    "icon_links": [],
}}

# Sidebar configuration
html_sidebars = {{
    #"**": ["sidebar-nav-bs", "globaltoc.html", "localtoc.html"]
    "**": ["sidebar-nav-bs", "globaltoc.html"]
}}
""".format(project_name)
    if "html_theme = 'pydata_sphinx_theme'" not in conf_content:
        with open(conf_path, "a") as f:
            f.write(f"\n{conf_snippet}")
        print("Updated conf.py with PyData Sphinx Theme, Pygments style, sidebar settings, and customizations")
    else:
        print("conf.py already configured with PyData Sphinx Theme")

    # Create _static directory and custom.css
    static_dir = os.path.join(docs_dir, "_static")
    if not os.path.exists(static_dir):
        os.makedirs(static_dir)

    custom_css = """
/* docs/_static/custom.css */
/* LENZ Encoders — strict, modern tech documentation palette */

@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=JetBrains+Mono:wght@400;500;600;700&display=swap');

@font-face {
    font-family: 'Inconsolata LGC';
    src: local('Inconsolata LGC'), local('InconsolataLGC');
    font-weight: 400;
    font-style: normal;
    font-display: swap;
}

@font-face {
    font-family: 'Inconsolata LGC';
    src: local('Inconsolata LGC Bold'), local('InconsolataLGC-Bold');
    font-weight: 700;
    font-style: normal;
    font-display: swap;
}

@font-face {
    font-family: 'Inconsolata LGC';
    src: local('Inconsolata LGC Italic'), local('InconsolataLGC-Italic');
    font-weight: 400;
    font-style: italic;
    font-display: swap;
}

/* --------------------------------------------------------------------------
 * LENZ design tokens
 * -------------------------------------------------------------------------- */

:root {
    --lenz-bg: #ffffff;
    --lenz-surface: #f7f8fa;
    --lenz-surface-hover: #eff1f4;
    --lenz-text: #111418;
    --lenz-text-muted: #5c6370;
    --lenz-accent: #2563eb;
    --lenz-accent-dim: #1d4ed8;
    --lenz-accent-soft: #dbeafe;
    --lenz-border: #e1e4e8;
    --lenz-border-muted: #f0f1f4;
    --lenz-good: #16a34a;
    --lenz-good-soft: #dcfce7;
    --lenz-bad: #dc2626;
    --lenz-bad-soft: #fee2e2;
    --lenz-warn: #d97706;
    --lenz-warn-soft: #fef3c7;
    --lenz-info: #0284c7;
    --lenz-info-soft: #e0f2fe;
    --lenz-code-bg: #f6f8fa;
}

html[data-theme="dark"] {
    --lenz-bg: #0a0b0d;
    --lenz-surface: #13151a;
    --lenz-surface-hover: #1a1c23;
    --lenz-text: #f0f1f4;
    --lenz-text-muted: #8a919c;
    --lenz-accent: #60a5fa;
    --lenz-accent-dim: #3b82f6;
    --lenz-accent-soft: #1e3a8a;
    --lenz-border: #252a33;
    --lenz-border-muted: #1a1c23;
    --lenz-good: #34d399;
    --lenz-good-soft: #064e3b;
    --lenz-bad: #f87171;
    --lenz-bad-soft: #450a0a;
    --lenz-warn: #fbbf24;
    --lenz-warn-soft: #451a03;
    --lenz-info: #38bdf8;
    --lenz-info-soft: #0c4a6e;
    --lenz-code-bg: #0d0d0f;
}

/* --------------------------------------------------------------------------
 * Typography
 * -------------------------------------------------------------------------- */

body {
    font-family: 'Inter', -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Oxygen, Ubuntu, Cantarell, sans-serif;
    font-feature-settings: 'liga' 1, 'calt' 1;
    -webkit-font-smoothing: antialiased;
    -moz-osx-font-smoothing: grayscale;
    line-height: 1.65;
    font-size: 16px;
    color: var(--lenz-text);
    background-color: var(--lenz-bg);
}

h1, h2, h3, h4, h5, h6 {
    font-family: 'Inter', -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Oxygen, Ubuntu, Cantarell, sans-serif;
    font-weight: 600;
    letter-spacing: -0.02em;
    color: var(--lenz-text);
    background: none;
    -webkit-background-clip: unset;
    -webkit-text-fill-color: unset;
    display: block;
}

h1 {
    font-size: 2rem;
    margin-bottom: 0.5rem;
}

h2 {
    font-size: 1.4rem;
    margin-top: 2.5rem;
    margin-bottom: 1rem;
    padding-bottom: 0.5rem;
    border-bottom: 1px solid var(--lenz-border);
}

h3 {
    font-size: 1.1rem;
    margin-top: 1.75rem;
    margin-bottom: 0.75rem;
    color: var(--lenz-text);
}

p {
    color: var(--lenz-text-muted);
    margin-bottom: 1rem;
}

p strong {
    color: var(--lenz-text);
}

a {
    color: var(--lenz-accent);
    text-decoration: none;
    transition: color 0.15s ease;
}

a:hover {
    color: var(--lenz-accent-dim);
    text-decoration: underline;
}

a > code {
    color: inherit;
}

/* --------------------------------------------------------------------------
 * Code
 * -------------------------------------------------------------------------- */

code, pre, .highlight {
    font-family: 'JetBrains Mono', 'Inconsolata LGC', 'Inconsolata', 'Fira Code', 'Consolas', monospace;
    font-size: 14px;
}

code {
    color: var(--lenz-text);
    background-color: var(--lenz-code-bg);
    border: 1px solid var(--lenz-border);
    border-radius: 4px;
    padding: 0.15em 0.35em;
}

.highlight {
    background: var(--lenz-code-bg);
    border: 1px solid var(--lenz-border);
    border-radius: 8px;
    padding: 1rem;
    margin: 1rem 0;
}

.highlight pre {
    color: var(--lenz-text);
    line-height: 1.65;
    background: transparent;
    padding: 0;
    margin: 0;
}

/* --------------------------------------------------------------------------
 * Syntax highlighting — Kimi / GitHub-style palette
 * -------------------------------------------------------------------------- */

/* Light mode (GitHub-light inspired) */
.highlight .k,
.highlight .kc,
.highlight .kd,
.highlight .kn,
.highlight .kp,
.highlight .kr,
.highlight .kt { color: #cf222e; font-weight: 500; }

.highlight .s,
.highlight .s1,
.highlight .s2,
.highlight .sb,
.highlight .sc,
.highlight .sd,
.highlight .se,
.highlight .sh,
.highlight .si,
.highlight .sr,
.highlight .sx,
.highlight .ss { color: #0a3069; }

.highlight .c,
.highlight .c1,
.highlight .cm,
.highlight .cp,
.highlight .cs { color: #6e7781; font-style: italic; }

.highlight .n  { color: var(--lenz-text); }
.highlight .na { color: #1f2328; }
.highlight .nb { color: #cf222e; }
.highlight .nc { color: #953800; }
.highlight .nd { color: #8250df; }
.highlight .ne { color: #953800; }
.highlight .nf { color: #8250df; }
.highlight .ni { color: #1f2328; }
.highlight .nn { color: #953800; }
.highlight .no { color: #953800; }
.highlight .nt { color: #0550ae; }
.highlight .nv { color: #1f2328; }
.highlight .ow { color: #cf222e; }
.highlight .bp { color: #cf222e; }
.highlight .fm { color: #8250df; }
.highlight .vc { color: #1f2328; }
.highlight .vg { color: #1f2328; }
.highlight .vi { color: #1f2328; }

.highlight .m,
.highlight .mb,
.highlight .mf,
.highlight .mh,
.highlight .mi,
.highlight .mo { color: #0550ae; }

.highlight .o,
.highlight .p  { color: #59636e; }

/* Dark mode (Kimi / GitHub-dark inspired) */
html[data-theme="dark"] .highlight .k,
html[data-theme="dark"] .highlight .kc,
html[data-theme="dark"] .highlight .kd,
html[data-theme="dark"] .highlight .kn,
html[data-theme="dark"] .highlight .kp,
html[data-theme="dark"] .highlight .kr,
html[data-theme="dark"] .highlight .kt { color: #7dd3fc; font-weight: 500; }

html[data-theme="dark"] .highlight .s,
html[data-theme="dark"] .highlight .s1,
html[data-theme="dark"] .highlight .s2,
html[data-theme="dark"] .highlight .sb,
html[data-theme="dark"] .highlight .sc,
html[data-theme="dark"] .highlight .sd,
html[data-theme="dark"] .highlight .se,
html[data-theme="dark"] .highlight .sh,
html[data-theme="dark"] .highlight .si,
html[data-theme="dark"] .highlight .sr,
html[data-theme="dark"] .highlight .sx,
html[data-theme="dark"] .highlight .ss { color: #7ee787; }

html[data-theme="dark"] .highlight .c,
html[data-theme="dark"] .highlight .c1,
html[data-theme="dark"] .highlight .cm,
html[data-theme="dark"] .highlight .cp,
html[data-theme="dark"] .highlight .cs { color: #6e7681; font-style: italic; }

html[data-theme="dark"] .highlight .n  { color: #e6edf3; }
html[data-theme="dark"] .highlight .na { color: #e6edf3; }
html[data-theme="dark"] .highlight .nb { color: #ff7b72; }
html[data-theme="dark"] .highlight .nc { color: #ffa657; }
html[data-theme="dark"] .highlight .nd { color: #d2a8ff; }
html[data-theme="dark"] .highlight .ne { color: #ffa657; }
html[data-theme="dark"] .highlight .nf { color: #d2a8ff; }
html[data-theme="dark"] .highlight .ni { color: #e6edf3; }
html[data-theme="dark"] .highlight .nn { color: #ffa657; }
html[data-theme="dark"] .highlight .no { color: #ffa657; }
html[data-theme="dark"] .highlight .nt { color: #79c0ff; }
html[data-theme="dark"] .highlight .nv { color: #e6edf3; }
html[data-theme="dark"] .highlight .ow { color: #ff7b72; }
html[data-theme="dark"] .highlight .bp { color: #ff7b72; }
html[data-theme="dark"] .highlight .fm { color: #d2a8ff; }
html[data-theme="dark"] .highlight .vc { color: #e6edf3; }
html[data-theme="dark"] .highlight .vg { color: #e6edf3; }
html[data-theme="dark"] .highlight .vi { color: #e6edf3; }

html[data-theme="dark"] .highlight .m,
html[data-theme="dark"] .highlight .mb,
html[data-theme="dark"] .highlight .mf,
html[data-theme="dark"] .highlight .mh,
html[data-theme="dark"] .highlight .mi,
html[data-theme="dark"] .highlight .mo { color: #79c0ff; }

html[data-theme="dark"] .highlight .o,
html[data-theme="dark"] .highlight .p  { color: #8b949e; }

/* --------------------------------------------------------------------------
 * API / signatures
 * -------------------------------------------------------------------------- */

.sig-name {
    color: var(--lenz-accent);
    font-weight: 600;
}

.sig-param .o,
.sig-param .default_value {
    color: var(--lenz-text-muted);
}

/* --------------------------------------------------------------------------
 * Sidebar
 * -------------------------------------------------------------------------- */

.bd-sidebar .nav-link {
    color: var(--lenz-text-muted);
    border-left: 2px solid transparent;
    border-radius: 0 4px 4px 0;
    padding-left: 0.75rem;
    font-weight: 400;
    transition: all 0.15s ease;
}

.bd-sidebar .nav-link:hover {
    color: var(--lenz-text);
    background-color: var(--lenz-surface-hover);
    border-left-color: var(--lenz-border);
}

.bd-sidebar .nav-link.active {
    color: var(--lenz-accent);
    background-color: var(--lenz-surface);
    border-left-color: var(--lenz-accent);
    font-weight: 500;
}

/* --------------------------------------------------------------------------
 * Target / highlight states — override the ugly PyData default
 * -------------------------------------------------------------------------- */

dt:target,
span.highlighted,
.viewcode-block:target,
:target > :is(h1, h2, h3, h4, h5, h6) {
    background-color: var(--lenz-surface-hover);
}

/* --------------------------------------------------------------------------
 * PyData theme semantic color overrides — strict, modern tech palette
 * -------------------------------------------------------------------------- */

html[data-theme="light"] {
    --pst-color-primary: var(--lenz-accent);
    --pst-color-primary-bg: var(--lenz-accent-soft);
    --pst-color-secondary: var(--lenz-text-muted);
    --pst-color-secondary-bg: var(--lenz-surface);
    --pst-color-accent: var(--lenz-accent);
    --pst-color-accent-bg: var(--lenz-accent-soft);
    --pst-color-info: var(--lenz-info);
    --pst-color-info-bg: var(--lenz-info-soft);
    --pst-color-warning: var(--lenz-warn);
    --pst-color-warning-bg: var(--lenz-warn-soft);
    --pst-color-success: var(--lenz-good);
    --pst-color-success-bg: var(--lenz-good-soft);
    --pst-color-attention: var(--lenz-warn);
    --pst-color-attention-bg: var(--lenz-warn-soft);
    --pst-color-danger: var(--lenz-bad);
    --pst-color-danger-bg: var(--lenz-bad-soft);
    --pst-color-text-base: var(--lenz-text);
    --pst-color-text-muted: var(--lenz-text-muted);
    --pst-color-shadow: rgba(0, 0, 0, 0.08);
    --pst-color-border: var(--lenz-border);
    --pst-color-border-muted: var(--lenz-border-muted);
    --pst-color-blockquote-notch: var(--lenz-border);
    --pst-color-inline-code: var(--lenz-text);
    --pst-color-link-higher-contrast: var(--lenz-accent-dim);
    --pst-color-target: var(--lenz-surface-hover);
    --pst-color-table: var(--lenz-text);
    --pst-color-table-row-hover-bg: var(--lenz-surface-hover);
    --pst-color-table-inner-border: var(--lenz-border);
    --pst-color-background: var(--lenz-bg);
    --pst-color-on-background: var(--lenz-bg);
    --pst-color-surface: var(--lenz-surface);
    --pst-color-on-surface: var(--lenz-text);
    --pst-color-heading: var(--lenz-text);
    --pst-color-link: var(--lenz-accent);
    --pst-color-link-hover: var(--lenz-accent-dim);
    --pst-color-table-outer-border: var(--lenz-border);
    --pst-color-table-heading-bg: var(--lenz-surface);
    --pst-color-table-row-zebra-high-bg: var(--lenz-bg);
    --pst-color-table-row-zebra-low-bg: var(--lenz-surface);
}

html[data-theme="dark"] {
    --pst-color-primary: var(--lenz-accent);
    --pst-color-primary-bg: var(--lenz-accent-soft);
    --pst-color-secondary: var(--lenz-text-muted);
    --pst-color-secondary-bg: var(--lenz-surface-hover);
    --pst-color-accent: var(--lenz-accent);
    --pst-color-accent-bg: var(--lenz-accent-soft);
    --pst-color-info: var(--lenz-info);
    --pst-color-info-bg: var(--lenz-info-soft);
    --pst-color-warning: var(--lenz-warn);
    --pst-color-warning-bg: var(--lenz-warn-soft);
    --pst-color-success: var(--lenz-good);
    --pst-color-success-bg: var(--lenz-good-soft);
    --pst-color-attention: var(--lenz-warn);
    --pst-color-attention-bg: var(--lenz-warn-soft);
    --pst-color-danger: var(--lenz-bad);
    --pst-color-danger-bg: var(--lenz-bad-soft);
    --pst-color-text-base: var(--lenz-text);
    --pst-color-text-muted: var(--lenz-text-muted);
    --pst-color-shadow: rgba(0, 0, 0, 0.35);
    --pst-color-border: var(--lenz-border);
    --pst-color-border-muted: var(--lenz-border-muted);
    --pst-color-blockquote-notch: var(--lenz-border);
    --pst-color-inline-code: var(--lenz-text);
    --pst-color-link-higher-contrast: var(--lenz-accent);
    --pst-color-target: var(--lenz-surface-hover);
    --pst-color-table: var(--lenz-text);
    --pst-color-table-row-hover-bg: var(--lenz-surface-hover);
    --pst-color-table-inner-border: var(--lenz-border);
    --pst-color-background: var(--lenz-bg);
    --pst-color-on-background: var(--lenz-surface);
    --pst-color-surface: var(--lenz-surface);
    --pst-color-on-surface: var(--lenz-text);
    --pst-color-heading: var(--lenz-text);
    --pst-color-link: var(--lenz-accent);
    --pst-color-link-hover: var(--lenz-accent-dim);
    --pst-color-table-outer-border: var(--lenz-border);
    --pst-color-table-heading-bg: var(--lenz-surface);
    --pst-color-table-row-zebra-high-bg: var(--lenz-surface-hover);
    --pst-color-table-row-zebra-low-bg: var(--lenz-surface);
}

/* --------------------------------------------------------------------------
 * Hide noisy TOC headings
 * -------------------------------------------------------------------------- */

.bd-sidebar .nav > li > a.nav-link.toc-heading,
.bd-sidebar-primary h3,
nav.bd-links p.bd-links__title,
nav.bd-links p.caption {
    display: none;
}

/* --------------------------------------------------------------------------
 * Tables
 * -------------------------------------------------------------------------- */

table {
    border-collapse: collapse;
    width: 100%;
    margin: 1.25rem 0;
    font-size: 0.9rem;
}

th, td {
    text-align: left;
    padding: 0.75rem 0.5rem;
    border-bottom: 1px solid var(--lenz-border);
}

th {
    color: var(--lenz-text-muted);
    font-weight: 500;
    text-transform: uppercase;
    font-size: 0.8rem;
    letter-spacing: 0.03em;
}

td {
    color: var(--lenz-text);
}

/* --------------------------------------------------------------------------
 * Misc
 * -------------------------------------------------------------------------- */

em {
    font-style: italic;
}

.bd-sidebar {
    display: block !important;
    visibility: visible !important;
}

/* --------------------------------------------------------------------------
 * Admonitions — clean, minimal, no icons
 * -------------------------------------------------------------------------- */

.admonition {
    margin: 1.25rem 0;
    padding: 0.75rem 1rem;
    border-radius: 6px;
    border-left: 3px solid;
    background-color: var(--lenz-surface);
    border-color: var(--lenz-border);
    box-shadow: none;
}

.admonition > .admonition-title {
    margin: -0.75rem -1rem 0.5rem -1rem;
    padding: 0.5rem 1rem;
    font-size: 0.8rem;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.04em;
    color: var(--lenz-text-muted);
    background: transparent;
    position: relative;
}

.admonition > .admonition-title::after {
    display: none !important;
}

.admonition > p:not(.admonition-title) {
    margin: 0;
    color: var(--lenz-text);
}

.admonition.note,
.admonition.tip,
.admonition.hint {
    background-color: var(--lenz-info-soft);
    border-color: var(--lenz-info);
}

.admonition.note > .admonition-title,
.admonition.tip > .admonition-title,
.admonition.hint > .admonition-title {
    color: var(--lenz-info);
}

.admonition.warning,
.admonition.attention,
.admonition.caution {
    background-color: var(--lenz-warn-soft);
    border-color: var(--lenz-warn);
}

.admonition.warning > .admonition-title,
.admonition.attention > .admonition-title,
.admonition.caution > .admonition-title {
    color: var(--lenz-warn);
}

.admonition.danger,
.admonition.error {
    background-color: var(--lenz-bad-soft);
    border-color: var(--lenz-bad);
}

.admonition.danger > .admonition-title,
.admonition.error > .admonition-title {
    color: var(--lenz-bad);
}

.admonition.important,
.admonition.seealso {
    background-color: var(--lenz-accent-soft);
    border-color: var(--lenz-accent);
}

.admonition.important > .admonition-title,
.admonition.seealso > .admonition-title {
    color: var(--lenz-accent);
}
"""
    with open(os.path.join(static_dir, "custom.css"), "w") as f:
        f.write(custom_css)
    print("Created/updated custom.css with PyData Sphinx Theme styles")

    # Copy favicon.ico to _static directory
    favicon_file = ["favicon.ico"]
    for file in favicon_file:
        source_path = os.path.join("source_docs", file)
        dest_path = os.path.join(static_dir, file)
        if os.path.exists(source_path):
            shutil.copy2(source_path, dest_path)
            print(f"Copied {file} from source_docs to {static_dir}")
        else:
            print(f"Warning: {file} not found in source_docs. Skipping copy.")

    # Create source_docs directory for static .rst files
    source_dir = "source_docs"
    if not os.path.exists(source_dir):
        os.makedirs(source_dir)

    # Define default content for static pages if source files are missing
    default_static_pages = {
        "getting_started.rst": """
Getting Started
===============

Welcome to **lenz-flashtool**, a Python library for BiSS C firmware updates and calibration of LENZ Encoders. This guide introduces the library and provides a quick start for new users.

What is lenz-flashtool?
-----------------------

``lenz-flashtool`` is designed to facilitate firmware updates and calibration for BiSS C compatible encoder devices. It provides a modular structure with tools for flashing firmware, processing encoder data, and interacting via a command-line interface.

Key features:
- Firmware flashing with :mod:`lenz_flashtool.flashtool`
- BiSS C protocol support via :mod:`lenz_flashtool.biss`
- Command-line interface with :mod:`lenz_flashtool.biss.cli`
- Utilities for encoder processing and testing

Quick Start
-----------

To get started, install the library and try a simple firmware update command:

.. code-block:: python

   from lenz_flashtool.flashtool import FlashTool
   flasher = FlashTool(device_id="ENC123")
   flasher.update_firmware("firmware.bin")

For CLI usage:

.. code-block:: bash

   lenz-flashtool-cli update --device ENC123 --firmware firmware.bin

See :doc:`installation` for setup instructions and :doc:`usage` for more examples.

Next Steps
----------

- Follow the :doc:`installation` guide to set up the library.
- Explore the :doc:`usage` section for detailed examples.
- Refer to :doc:`api` for complete API documentation.
""",
        "installation.rst": """
Installation
============

This guide explains how to install the **lenz-flashtool** library and its dependencies.

Prerequisites
-------------

- Python 3.8 or higher
- pip (Python package manager)
- A BiSS C compatible encoder device (e.g., LENZ Encoders)

Installation Steps
------------------

1. **Install lenz-flashtool**:

   Use pip to install the library from PyPI:

   .. code-block:: bash

      pip install lenz-flashtool

2. **Verify Installation**:

   Check that the library is installed:

   .. code-block:: python

      import lenz_flashtool
      print(lenz_flashtool.__version__)

   This should display the version (e.g., ``0.1.0``).

3. **Install CLI (Optional)**:

   The command-line interface is included with the library. Test it:

   .. code-block:: bash

      lenz-flashtool-cli --version

Troubleshooting
---------------

- **ModuleNotFoundError**: Ensure pip installs to the correct Python environment. Use ``pip --version`` to check.
- **Device Not Found**: Verify your BiSS C device is connected and drivers are installed.

See :doc:`getting_started` for an introduction or :doc:`usage` for usage examples.
""",
        "usage.rst": """
Usage
=====

This section provides examples of using **lenz-flashtool** for firmware updates, calibration, and CLI operations.

Firmware Update
---------------

Update firmware on a BiSS C encoder device:

.. code-block:: python

   from lenz_flashtool.flashtool import FlashTool

   # Initialize flasher
   flasher = FlashTool(device_id="ENC123")

   # Update firmware
   flasher.update_firmware("firmware.bin")

Using the CLI:

.. code-block:: bash

   lenz-flashtool-cli update --device ENC123 --firmware firmware.bin

Calibration
-----------

Calibrate an encoder using :mod:`lenz_flashtool.encproc`:

.. code-block:: python

   from lenz_flashtool.encproc import EncoderProcessor

   # Initialize processor
   processor = EncoderProcessor(device_id="ENC123")

   # Perform calibration
   processor.calibrate()

See :mod:`lenz_flashtool.encproc` for more details.

Testing
-------

Run tests with :mod:`lenz_flashtool.testing`:

.. code-block:: python

   from lenz_flashtool.testing import run_tests

   run_tests(device_id="ENC123")

For more examples, explore :doc:`api` or refer to :doc:`getting_started`.
"""
    }

    # Copy static .rst files from source_docs/ to docs/, or create defaults
    static_pages = ["getting_started.rst", "installation.rst", "usage.rst"]
    for page in static_pages:
        source_path = os.path.join(source_dir, page)
        dest_path = os.path.join(docs_dir, page)
        if os.path.exists(source_path):
            shutil.copy2(source_path, dest_path)
            print(f"Copied {page} from {source_dir} to {docs_dir}")
        else:
            with open(dest_path, "w") as f:
                f.write(default_static_pages[page])
            print(f"Created default {page} in {docs_dir}")

    # Define renaming map for submodules in documentation
    doc_name_map = {
        "flashtool": "FlashTool",
        "biss": "BiSS",
        "encproc": "EncProc",
        "utils": "utils",
        "testing": "testing",
        "cli": "BiSS CLI"
    }

    # Create an index.rst file with toctree for static pages and submodules
    toctree_entries = [
        # "   getting_started",
        # "   installation",
        # "   usage",
        "",
        "   api"
    ] + [f"   {doc_name_map[mod]}" for mod in submodules]
    toctree = "\n".join(toctree_entries)
    index_rst = f"""
{project_name} Documentation
=================================

Welcome to **{project_name}**, a Python library for BiSS C firmware updates and calibration of LENZ Encoders. This guide introduces the library and provides a quick start for new users.


.. toctree::
   :maxdepth: 2
   :caption: User Guide

   getting_started
   installation
   usage

.. toctree::
   :maxdepth: 2
   :caption: API Reference

{toctree}

Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
"""
    with open(os.path.join(docs_dir, "index.rst"), "w") as f:
        f.write(index_rst)
    print("Updated index.rst with toctree: getting_started, installation, usage, api, " + ", ".join(doc_name_map[mod] for mod in submodules))

    # Create an api.rst file for the main module
    api_rst = f"""
lenz-flashtool Library API Reference
====================================

.. currentmodule:: {module_name}

.. automodule:: {module_name}
   :members:
   :undoc-members:
   :show-inheritance:
"""
#    :no-index:
# """
    with open(os.path.join(docs_dir, "api.rst"), "w") as f:
        f.write(api_rst)
    print("Created/updated api.rst")

    # Create .rst files for each submodule with renamed documentation titles
    for submodule in submodules:
        doc_name = doc_name_map[submodule]
        # Handle cli as a module in the biss package
        module_path = f"{module_name}.biss.{submodule}" if submodule == "cli" else f"{module_name}.{submodule}"
        # Special handling for encproc to include LenzEncoderProcessor class. TODO doesnt work, remove
        if submodule == "_encproc":
            submodule_rst = f"""
{doc_name} Module
=============================

.. currentmodule:: {module_path}


.. automodule:: {module_path}
    :members:
    :undoc-members:
    :show-inheritance:
    :inherited-members:
..
    .. autoclass:: LenzEncoderProcessor
        :members:
        :undoc-members:
        :show-inheritance:
        :inherited-members:

.. toctree::
   :hidden:
   :maxdepth: 4

"""
        else:
            submodule_rst = f"""
{doc_name} Module
=============================

.. currentmodule:: {module_path}

.. automodule:: {module_path}
   :members:
   :undoc-members:
   :show-inheritance:
"""
        with open(os.path.join(docs_dir, f"{doc_name}.rst"), "w") as f:
            f.write(submodule_rst)
        print(f"Created/updated {doc_name}.rst")

    # Build the HTML documentation
    try:
        subprocess.run([
            "sphinx-build",
            "-b", "html",
            ".", "_build/html"
        ], cwd=docs_dir, check=True)
        print(f"HTML documentation built in {docs_dir}/_build/html")
    except subprocess.CalledProcessError as e:
        print(f"Error building HTML: {e}")


if __name__ == "__main__":
    setup_sphinx_project(
        project_name="lenz-flashtool",
        author="LENZ Encoders",
        version="0.1.9",
        module_name="lenz_flashtool",
        submodules=["flashtool", "biss", "encproc", "utils", "testing", "cli"]
    )
