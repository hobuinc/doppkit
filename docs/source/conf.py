import os

# Configuration file for the Sphinx documentation builder.
#
# For the full list of built-in configuration values, see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

# -- Project information -----------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#project-information

project = 'doppkit'
copyright = '2024, Hobu Inc.'
author = 'Ognyan Moore'

# The full version, including alpha/beta/rc tags
import pathlib
import ast

# get version info without installing first
file_path = (
         pathlib.Path(__file__).parent / ".." / ".." / "src" / "doppkit" / "__init__.py"
).resolve()
node = ast.parse(file_path.read_text())
for subnode in node.body:
    if isinstance(subnode, ast.Assign) and subnode.targets[0].id == "__version__":
        release = subnode.value.value
        break
else: # if unable to determine, check to see if it is installed...
    try:
        import doppkit
    except ImportError as e:
        raise ImportError("Unable to determine doppkit version information") from e
    else:
        release = doppkit.__version__

from packaging.version import parse
version = parse(release).public

# -- General configuration ---------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#general-configuration

extensions = [
    "myst_parser"
]

templates_path = ['_templates']
exclude_patterns = ['_build', 'Thumbs.db', '.DS_Store']



# -- Options for HTML output -------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#options-for-html-output

html_baseurl = os.environ.get("READTHEDOCS_CANONICAL_URL", "")


html_theme = 'alabaster'
html_static_path = [
    # '_static'  # not actually used, but causes a warning in RTD since empty
]

html_context = {}
if os.environ.get("READTHEDOCS", "") == "True":
    html_context["READTHEDOCS"] = True

# -- Options for LATEX output ------------------------------------------------

latex_elements = {
    'extraclassoptions': ',oneany,oneside',
    'papersize': 'letterpaper',
}

pygments_style = "staroffice"