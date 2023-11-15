# Configuration file for the Sphinx documentation builder.
#
# For the full list of built-in configuration values, see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

# -- Project information -----------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#project-information

project = 'doppkit'
copyright = '2023, Hobu Inc.'
author = 'Ognyan Moore'

# The full version, including alpha/beta/rc tags
# get version info without installing
import importlib.util
import sys
import pathlib
spec = importlib.util.spec_from_file_location(
	"doppkit_version",
	(
        pathlib.Path(__file__).parent / ".." / ".." / "src" / "doppkit" / "__version__.py"
	).resolve()
)
doppkit_version = importlib.util.module_from_spec(spec)
sys.modules["doppkit"] = doppkit_version
spec.loader.exec_module(doppkit_version)
release = doppkit_version.__version__

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

html_theme = 'alabaster'
html_static_path = ['_static']

# -- Options for LATEX output ------------------------------------------------

latex_elements = {
	'extraclassoptions': ',oneany,oneside',
	'papersize': 'letterpaper',
}

pygments_style = "staroffice"