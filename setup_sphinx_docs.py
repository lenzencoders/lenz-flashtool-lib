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
/* LENZ Encoders — strict, Apple/Kimi-inspired documentation styling */

@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=JetBrains+Mono:wght@400;500;600;700&display=swap');

/* --------------------------------------------------------------------------
 * Design tokens
 * -------------------------------------------------------------------------- */

:root {
    /* Surfaces */
    --lenz-bg: #ffffff;
    --lenz-surface: #fafbfc;
    --lenz-surface-hover: #f4f5f7;
    --lenz-code-bg: #f6f7f9;
    --lenz-inline-bg: #f1f2f5;

    /* Text */
    --lenz-text: #1a1d21;
    --lenz-text-soft: #3a3f47;
    --lenz-text-muted: #6b7280;
    --lenz-text-faint: #9ca3af;

    /* Accent — quieter tech blue */
    --lenz-accent: #0066cc;
    --lenz-accent-dim: #004999;
    --lenz-accent-soft: #e7f0fb;

    /* Borders — barely visible */
    --lenz-border: #ececef;
    --lenz-border-strong: #d8dadd;

    /* Semantic */
    --lenz-good: #16a34a;
    --lenz-good-soft: #e9f7ee;
    --lenz-bad: #dc2626;
    --lenz-bad-soft: #fdecec;
    --lenz-warn: #d97706;
    --lenz-warn-soft: #fdf3e3;
    --lenz-info: #0284c7;
    --lenz-info-soft: #e6f3fa;
}

html[data-theme="dark"] {
    --lenz-bg: #0d0f12;
    --lenz-surface: #14171c;
    --lenz-surface-hover: #1b1f25;
    --lenz-code-bg: #14171c;
    --lenz-inline-bg: #1b1f25;

    --lenz-text: #e7e9ed;
    --lenz-text-soft: #c5c9d0;
    --lenz-text-muted: #8a919c;
    --lenz-text-faint: #5a6068;

    --lenz-accent: #4f9eff;
    --lenz-accent-dim: #80b8ff;
    --lenz-accent-soft: #11233a;

    --lenz-border: #1f2126;
    --lenz-border-strong: #2a2d33;

    --lenz-good: #34d399;
    --lenz-good-soft: #0e2418;
    --lenz-bad: #f87171;
    --lenz-bad-soft: #2a1212;
    --lenz-warn: #fbbf24;
    --lenz-warn-soft: #2a1f0c;
    --lenz-info: #38bdf8;
    --lenz-info-soft: #0c2433;
}

/* --------------------------------------------------------------------------
 * Typography
 * -------------------------------------------------------------------------- */

body {
    font-family: 'Inter', -apple-system, BlinkMacSystemFont, "SF Pro Text", "Segoe UI", Roboto, sans-serif;
    font-feature-settings: 'liga' 1, 'calt' 1, 'ss01' 1;
    -webkit-font-smoothing: antialiased;
    -moz-osx-font-smoothing: grayscale;
    line-height: 1.7;
    font-size: 16px;
    color: var(--lenz-text);
    background-color: var(--lenz-bg);
}

h1, h2, h3, h4, h5, h6 {
    font-family: 'Inter', -apple-system, BlinkMacSystemFont, "SF Pro Display", "Segoe UI", Roboto, sans-serif;
    color: var(--lenz-text);
    line-height: 1.25;
    background: none;
    -webkit-background-clip: unset;
    -webkit-text-fill-color: unset;
}

h1 {
    font-size: 2.25rem;
    font-weight: 600;
    letter-spacing: -0.022em;
    margin: 0 0 1.5rem 0;
}

h2 {
    font-size: 1.625rem;
    font-weight: 600;
    letter-spacing: -0.018em;
    margin: 3rem 0 1rem 0;
    padding: 0;
    border: 0;
}

h3 {
    font-size: 1.25rem;
    font-weight: 600;
    letter-spacing: -0.015em;
    margin: 2rem 0 0.75rem 0;
}

h4 {
    font-size: 1rem;
    font-weight: 600;
    letter-spacing: -0.01em;
    margin: 1.5rem 0 0.5rem 0;
}

h5, h6 {
    font-size: 0.8125rem;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.06em;
    color: var(--lenz-text-muted);
    margin: 1.25rem 0 0.5rem 0;
}

p {
    color: var(--lenz-text);
    margin: 0 0 1rem 0;
}

p strong, li strong {
    color: var(--lenz-text);
    font-weight: 600;
}

ul, ol {
    color: var(--lenz-text);
    padding-left: 1.5rem;
    margin: 0 0 1rem 0;
}

li {
    margin: 0.25rem 0;
}

em {
    font-style: italic;
}

/* --------------------------------------------------------------------------
 * Links — Apple signature: always underlined, offset, subtle
 * -------------------------------------------------------------------------- */

a {
    color: var(--lenz-accent);
    text-decoration: underline;
    text-decoration-thickness: 1px;
    text-underline-offset: 3px;
    text-decoration-color: rgba(0, 102, 204, 0.4);
    transition: color 0.15s ease, text-decoration-color 0.15s ease;
}

html[data-theme="dark"] a {
    text-decoration-color: rgba(79, 158, 255, 0.45);
}

a:hover {
    color: var(--lenz-accent-dim);
    text-decoration-color: var(--lenz-accent);
}

a > code,
a > .pre {
    color: inherit;
    text-decoration: inherit;
}

h1 a, h2 a, h3 a, h4 a, h5 a, h6 a {
    text-decoration: none;
    color: inherit;
}

/* --------------------------------------------------------------------------
 * Code
 * -------------------------------------------------------------------------- */

code, pre, kbd, samp, tt,
.highlight {
    font-family: 'JetBrains Mono', ui-monospace, 'SF Mono', Menlo, Consolas, monospace;
    font-feature-settings: 'liga' 0;
}

/* Inline code — no border, soft chip */
code.literal,
:not(pre) > code {
    font-size: 0.875em;
    font-weight: 500;
    background-color: var(--lenz-inline-bg);
    color: var(--lenz-text);
    border: 0;
    border-radius: 5px;
    padding: 0.1em 0.4em;
    letter-spacing: -0.005em;
}

/* Code blocks — borderless, slightly off-bg */
.highlight {
    background: var(--lenz-code-bg);
    border: 0;
    border-radius: 10px;
    padding: 1rem 1rem;
    margin: 1rem 0;
    overflow-x: auto;
    overflow-y: hidden;
}

/* Override pygments.css's auto-generated `html[data-theme] .highlight`
   background rules (specificity match required). */
html[data-theme="light"] .highlight,
html[data-theme="dark"] .highlight {
    background: var(--lenz-code-bg);
}

.highlight pre {
    color: var(--lenz-text);
    line-height: 1.6;
    font-size: 0.875rem;
    background: transparent;
    border: 0;
    padding: 0;
    margin: 0;
    overflow: visible;
}

/* --------------------------------------------------------------------------
 * Syntax highlighting — light mode (GitHub-light inspired)
 * -------------------------------------------------------------------------- */

.highlight .k, .highlight .kc, .highlight .kd, .highlight .kn,
.highlight .kp, .highlight .kr, .highlight .kt { color: #cf222e; font-weight: 500; }

.highlight .s, .highlight .s1, .highlight .s2, .highlight .sb,
.highlight .sc, .highlight .sd, .highlight .se, .highlight .sh,
.highlight .si, .highlight .sr, .highlight .sx, .highlight .ss { color: #0a3069; }

.highlight .c, .highlight .c1, .highlight .cm,
.highlight .cp, .highlight .cs { color: #6e7781; font-style: italic; }

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
.highlight .vc, .highlight .vg, .highlight .vi { color: #1f2328; }

.highlight .m, .highlight .mb, .highlight .mf,
.highlight .mh, .highlight .mi, .highlight .mo { color: #0550ae; }

.highlight .o, .highlight .p  { color: #59636e; }

/* --------------------------------------------------------------------------
 * Syntax highlighting — dark mode (GitHub-dark inspired)
 * -------------------------------------------------------------------------- */

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
html[data-theme="dark"] .highlight .vc,
html[data-theme="dark"] .highlight .vg,
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
 * API signatures — monospaced, left-rule, quiet
 * -------------------------------------------------------------------------- */

dl.py > dt,
dl.c > dt,
dl.cpp > dt,
dl.js > dt,
dt.sig {
    font-family: 'JetBrains Mono', ui-monospace, 'SF Mono', Menlo, Consolas, monospace;
    font-size: 0.9rem;
    background: transparent;
    border: 0;
    border-left: 2px solid var(--lenz-border-strong);
    padding: 0.45rem 0 0.45rem 1rem;
    margin: 1.75rem 0 0.5rem 0;
    color: var(--lenz-text);
    border-radius: 0;
}

.sig-prename, .sig-prename .pre {
    color: var(--lenz-text-muted);
    font-weight: 400;
}

.sig-name, .sig-name .pre {
    color: var(--lenz-text);
    font-weight: 600;
}

.sig-param,
.sig-param .n {
    color: var(--lenz-text-soft);
    font-style: normal;
}

.sig-param .default_value,
.sig-param .o,
.sig-return,
.sig-return .pre {
    color: var(--lenz-text-muted);
    font-weight: 400;
}

.sig-return-icon {
    color: var(--lenz-text-faint);
}

dl.py dd, dl.c dd, dl.cpp dd, dl.js dd {
    margin-left: 0;
    padding: 0 0 0 1rem;
    border: 0;
}

/* --------------------------------------------------------------------------
 * Field lists (Returns, Raises, Parameters in autodoc)
 * -------------------------------------------------------------------------- */

dl.field-list {
    margin: 1rem 0;
}

dl.field-list > dt {
    font-weight: 600;
    color: var(--lenz-text);
    background: transparent;
    padding: 0.25rem 0.5rem 0.25rem 0;
    text-transform: none;
    font-size: 0.875rem;
    border-radius: 0;
}

dl.field-list > dd {
    padding-left: 1rem;
    border-left: 0;
    margin-bottom: 0.5rem;
}

/* --------------------------------------------------------------------------
 * Layout — narrower reading column
 * -------------------------------------------------------------------------- */

.bd-main .bd-content .bd-article-container {
    max-width: 820px;
}

article.bd-article {
    padding: 1rem 0 4rem 0;
}

/* --------------------------------------------------------------------------
 * Header / navbar
 * -------------------------------------------------------------------------- */

.bd-header {
    background: var(--lenz-bg) !important;
    border-bottom: 1px solid var(--lenz-border);
    box-shadow: none !important;
}

.bd-header .navbar-nav .nav-link {
    color: var(--lenz-text-soft);
    font-weight: 500;
    font-size: 0.875rem;
}

.bd-header .navbar-nav .nav-link:hover {
    color: var(--lenz-text);
}

.bd-header .navbar-brand {
    font-weight: 600;
    color: var(--lenz-text);
    font-size: 0.95rem;
    letter-spacing: -0.01em;
}

/* --------------------------------------------------------------------------
 * Sidebar — borderless, quiet, 2px accent rule on active
 * -------------------------------------------------------------------------- */

.bd-sidebar {
    display: block !important;
    visibility: visible !important;
    border-right: 1px solid var(--lenz-border) !important;
    background: var(--lenz-bg);
}

.bd-sidebar-primary {
    padding-top: 1.5rem;
}

.bd-sidebar .nav-link {
    color: var(--lenz-text-soft);
    border-left: 2px solid transparent;
    border-radius: 0;
    padding: 0.35rem 0.75rem;
    font-weight: 400;
    font-size: 0.875rem;
    line-height: 1.5;
    background: transparent;
    transition: color 0.15s ease, border-color 0.15s ease;
}

.bd-sidebar .nav-link:hover {
    color: var(--lenz-text);
    background-color: transparent;
    border-left-color: var(--lenz-border-strong);
}

.bd-sidebar .nav-link.active {
    color: var(--lenz-accent);
    background-color: transparent;
    border-left-color: var(--lenz-accent);
    font-weight: 500;
}

.bd-sidebar .nav > li > a.reference {
    color: var(--lenz-text);
    font-weight: 500;
}

/* Hide noisy TOC headings */
.bd-sidebar .nav > li > a.nav-link.toc-heading,
.bd-sidebar-primary h3,
nav.bd-links p.bd-links__title,
nav.bd-links p.caption {
    display: none;
}

/* Secondary (right) sidebar — page TOC */
.bd-sidebar-secondary {
    font-size: 0.8125rem;
}

.bd-sidebar-secondary .toc-h2 a,
.bd-sidebar-secondary .toc-h3 a,
.bd-sidebar-secondary .toc-h4 a,
.bd-sidebar-secondary .nav-link,
.toc-entry a.nav-link {
    color: var(--lenz-text-muted);
    text-decoration: none;
    padding: 0.25rem 0 0.25rem 0.75rem;
}

.bd-sidebar-secondary a:hover {
    color: var(--lenz-text);
}

.bd-sidebar-secondary .active > a,
.toc-entry a.nav-link.active,
.toc-entry a.nav-link[aria-current="true"] {
    color: var(--lenz-accent);
}

/* --------------------------------------------------------------------------
 * Admonitions — left-border only, no fill
 * -------------------------------------------------------------------------- */

.admonition,
div.admonition {
    margin: 1.5rem 0;
    padding: 0.875rem 1.125rem;
    border-radius: 0;
    border: 0;
    border-left: 3px solid var(--lenz-border-strong);
    background-color: transparent;
    box-shadow: none;
    color: var(--lenz-text);
}

.admonition > .admonition-title,
div.admonition > .admonition-title {
    margin: 0 0 0.5rem 0;
    padding: 0;
    font-size: 0.75rem;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.06em;
    color: var(--lenz-text-muted);
    background: transparent;
    border: 0;
}

.admonition > .admonition-title::before,
.admonition > .admonition-title::after,
div.admonition > .admonition-title::before,
div.admonition > .admonition-title::after {
    display: none !important;
}

.admonition > p:not(.admonition-title),
div.admonition > p:not(.admonition-title) {
    margin: 0 0 0.5rem 0;
    color: var(--lenz-text);
}

.admonition > p:not(.admonition-title):last-child,
div.admonition > p:not(.admonition-title):last-child {
    margin-bottom: 0;
}

.admonition.note, .admonition.tip, .admonition.hint,
.admonition.seealso, .admonition.important,
div.admonition.note, div.admonition.tip, div.admonition.hint,
div.admonition.seealso, div.admonition.important {
    border-left-color: var(--lenz-accent);
}
.admonition.note > .admonition-title,
.admonition.tip > .admonition-title,
.admonition.hint > .admonition-title,
.admonition.seealso > .admonition-title,
.admonition.important > .admonition-title,
div.admonition.note > .admonition-title,
div.admonition.tip > .admonition-title,
div.admonition.hint > .admonition-title,
div.admonition.seealso > .admonition-title,
div.admonition.important > .admonition-title {
    color: var(--lenz-accent);
}

.admonition.warning, .admonition.attention, .admonition.caution,
div.admonition.warning, div.admonition.attention, div.admonition.caution {
    border-left-color: var(--lenz-warn);
}
.admonition.warning > .admonition-title,
.admonition.attention > .admonition-title,
.admonition.caution > .admonition-title,
div.admonition.warning > .admonition-title,
div.admonition.attention > .admonition-title,
div.admonition.caution > .admonition-title {
    color: var(--lenz-warn);
}

.admonition.danger, .admonition.error,
div.admonition.danger, div.admonition.error {
    border-left-color: var(--lenz-bad);
}
.admonition.danger > .admonition-title,
.admonition.error > .admonition-title,
div.admonition.danger > .admonition-title,
div.admonition.error > .admonition-title {
    color: var(--lenz-bad);
}

/* --------------------------------------------------------------------------
 * Tables — clean, sentence-case headers
 * -------------------------------------------------------------------------- */

table.docutils,
table.table,
table {
    border-collapse: collapse;
    width: 100%;
    margin: 1.5rem 0;
    font-size: 0.9rem;
    border: 0;
}

table.docutils th, table.table th, table th {
    text-align: left;
    padding: 0.75rem 1rem;
    border-bottom: 1px solid var(--lenz-border-strong);
    color: var(--lenz-text);
    font-weight: 600;
    text-transform: none;
    letter-spacing: 0;
    font-size: 0.875rem;
    background: transparent;
}

table.docutils td, table.table td, table td {
    text-align: left;
    padding: 0.75rem 1rem;
    border-bottom: 1px solid var(--lenz-border);
    color: var(--lenz-text);
}

table.docutils tr:last-child td, table.table tr:last-child td {
    border-bottom: 0;
}

/* --------------------------------------------------------------------------
 * Blockquotes, hr
 * -------------------------------------------------------------------------- */

blockquote {
    margin: 1.5rem 0;
    padding: 0.25rem 0 0.25rem 1rem;
    border-left: 3px solid var(--lenz-border-strong);
    color: var(--lenz-text-soft);
    font-style: normal;
}

hr {
    border: 0;
    border-top: 1px solid var(--lenz-border);
    margin: 3rem 0;
}

/* --------------------------------------------------------------------------
 * Target / highlight (anchored items)
 * -------------------------------------------------------------------------- */

dt:target,
span.highlighted,
.viewcode-block:target,
:target > :is(h1, h2, h3, h4, h5, h6) {
    background-color: var(--lenz-accent-soft);
    border-radius: 4px;
}

/* --------------------------------------------------------------------------
 * Headerlinks (¶) — invisible until hover
 * -------------------------------------------------------------------------- */

a.headerlink {
    color: var(--lenz-text-faint);
    text-decoration: none;
    padding: 0 0.25rem;
    opacity: 0;
    transition: opacity 0.15s ease;
    font-weight: 400;
}

h1:hover .headerlink,
h2:hover .headerlink,
h3:hover .headerlink,
h4:hover .headerlink,
dt:hover .headerlink {
    opacity: 1;
}

a.headerlink:hover {
    color: var(--lenz-accent);
    background: transparent;
    text-decoration: none;
}

/* --------------------------------------------------------------------------
 * Selection
 * -------------------------------------------------------------------------- */

::selection {
    background: var(--lenz-accent-soft);
    color: var(--lenz-text);
}

/* --------------------------------------------------------------------------
 * PyData theme variable overrides
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
    --pst-color-shadow: rgba(0, 0, 0, 0.04);
    --pst-color-border: var(--lenz-border);
    --pst-color-border-muted: var(--lenz-border);
    --pst-color-inline-code: var(--lenz-text);
    --pst-color-target: var(--lenz-accent-soft);
    --pst-color-table: var(--lenz-text);
    --pst-color-table-row-hover-bg: var(--lenz-surface);
    --pst-color-table-inner-border: var(--lenz-border);
    --pst-color-background: var(--lenz-bg);
    --pst-color-on-background: var(--lenz-bg);
    --pst-color-surface: var(--lenz-surface);
    --pst-color-on-surface: var(--lenz-text);
    --pst-color-heading: var(--lenz-text);
    --pst-color-link: var(--lenz-accent);
    --pst-color-link-hover: var(--lenz-accent-dim);
    --pst-color-table-outer-border: var(--lenz-border);
    --pst-color-table-heading-bg: transparent;
    --pst-color-table-row-zebra-high-bg: var(--lenz-bg);
    --pst-color-table-row-zebra-low-bg: var(--lenz-bg);
}

html[data-theme="dark"] {
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
    --pst-color-shadow: rgba(0, 0, 0, 0.5);
    --pst-color-border: var(--lenz-border);
    --pst-color-border-muted: var(--lenz-border);
    --pst-color-inline-code: var(--lenz-text);
    --pst-color-target: var(--lenz-accent-soft);
    --pst-color-table: var(--lenz-text);
    --pst-color-table-row-hover-bg: var(--lenz-surface);
    --pst-color-table-inner-border: var(--lenz-border);
    --pst-color-background: var(--lenz-bg);
    --pst-color-on-background: var(--lenz-surface);
    --pst-color-surface: var(--lenz-surface);
    --pst-color-on-surface: var(--lenz-text);
    --pst-color-heading: var(--lenz-text);
    --pst-color-link: var(--lenz-accent);
    --pst-color-link-hover: var(--lenz-accent-dim);
    --pst-color-table-outer-border: var(--lenz-border);
    --pst-color-table-heading-bg: transparent;
    --pst-color-table-row-zebra-high-bg: var(--lenz-bg);
    --pst-color-table-row-zebra-low-bg: var(--lenz-bg);
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
