# coding: utf-8
from setuptools import setup, find_packages

import doppkit
NAME = "doppkit"
VERSION = doppkit.__version__

REQUIRES = [
    "httpx",
    "rich",
    "requests",
    "click"
]

setup(
    name=NAME,
    version=VERSION,
    description="GRiD API v3",
    author_email="",
    url="",
    install_requires=REQUIRES,
    packages=find_packages(),
    include_package_data=True,
    zip_safe = False,
    entry_points = {
        'console_scripts': ['doppkit=doppkit.__main__:main'],
    },
    long_description="""\
    GRiD Synchronization client
    """
)
