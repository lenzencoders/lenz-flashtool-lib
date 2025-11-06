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
pygments_style = 'monokai'
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
/* Add gradient to headers */
h1, h2, h3 {
    background-clip: text;
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-image: linear-gradient(90deg, #6c034e, #3f90c9); /* Purple to blue gradient */
    display: inline-block; /* Needed for gradient to work properly */
}

/* Dark mode gradient */
html[data-theme="dark"] h1,
html[data-theme="dark"] h2,
html[data-theme="dark"] h3 {
    # background-image: linear-gradient(90deg, #4cb5ff, #912583); /* Blue to purple gradient */
    # background-image: linear-gradient(102deg, #e5b6ff -1%, #8e9fef 99%);
    background-image: linear-gradient(98deg, #2aa2c1, #aebcff);

}

/* Fallback for browsers that don't support gradient text */
@supports not (-webkit-background-clip: text) {
    h1, h2, h3 {
        color: #6c034e; /* Fallback to primary color */
    }
    html[data-theme="dark"] h1,
    html[data-theme="dark"] h2,
    html[data-theme="dark"] h3 {
        color: #4cb5ff; /* Fallback for dark mode */
    }
}

html[data-theme="light"] {
    --pst-color-primary: #6c034e;
}

html[data-theme="dark"] {
    --pst-color-primary: #4cb5ff;
}

/* Style for code blocks to make them stand out */
.highlight {
    background: #f8f8f8; /* Light gray background */
    padding: 10px;
    margin: 10px 0;
    font-family: 'Fira Code', 'Consolas', monospace; /* Modern monospace font */
}

.sig-name {
    color: #912583;
}

html[data-theme="dark"] dt:target, span.highlighted {
    background-color: #2d2337;
}

html[data-theme="dark"] .highlight {
    background: #14181e; /* Dark background for dark mode */
}

/* Ensure code text is readable */
.highlight pre {
    color: #333333; /* Dark text for light mode */
    line-height: 1.5;
}

html[data-theme="dark"] .highlight pre {
    color: #f8f8f8; /* Light text for dark mode */
}

/* Accent specific Pygments classes for keywords, strings, etc. */
.highlight .k { color: #D81B60; font-weight: bold; } /* Keywords (e.g., def, class) */
.highlight .s { color: #43A047; } /* Strings */
.highlight .c { color: #757575; font-style: italic; } /* Comments */
.highlight .n { color: #0277BD; } /* Names (e.g., variables) */

html[data-theme="dark"] .highlight .k { color: #F06292; } /* Keywords in dark mode */
html[data-theme="dark"] .highlight .s { color: #66BB6A; } /* Strings in dark mode */
html[data-theme="dark"] .highlight .c { color: #B0BEC5; } /* Comments in dark mode */
html[data-theme="dark"] .highlight .n { color: #4FC3F7; } /* Names in dark mode */

a {
    transition: color 0.3s ease;
    color: #3f90c9;
}
a>code {
    color: #3f90c9;
}
a:hover {
    color: #FFA726; /* Warm orange on hover */
    text-decoration: underline; /* Standard underline */
}

/* Sidebar link styles */
.bd-sidebar .nav-depth-0 .nav-item .nav-link {
    font-weight: bold;
    color: #37474F; /* Dark slate gray for light mode */
    border-left: 4px solid #00b0ff; /* Blue sidebar highlight */
}

html[data-theme="dark"] .bd-sidebar .nav-depth-0 .nav-item .nav-link {
    color: #CFD8DC; /* Soft off-white for dark mode */
    border-left: 4px solid #4fc3f7; /* Light blue for dark mode */
}

.bd-sidebar .nav-depth-0 .nav-item .nav-link:hover {
    color: #FFA726; /* Warm orange on hover */
}

/* Ensure sidebar visibility */
.bd-sidebar {
    display: block !important;
    visibility: visible !important;
}

/* Hide 'Table of Contents' heading in sidebar */
.bd-sidebar .nav > li > a.nav-link.toc-heading {
    display: none;
}
.bd-sidebar-primary h3 {
    display: none;
}
nav.bd-links p.bd-links__title, nav.bd-links p.caption {
    display: none;
}

a.current.reference.internal {
    background-color: transparent;
    //box-shadow: inset max(3px, .1875rem, .12em) 0 0 var(--pst-color-primary);
    color: var(--pst-color-primary);
    font-weight: 600;
}
html[data-theme="light"] .highlight .c1 {
    color: #268510;
}
em {
    font-style: normal;
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
        version="0.1.5",
        module_name="lenz_flashtool",
        submodules=["flashtool", "biss", "encproc", "utils", "testing", "cli"]
    )
