"""Python package description."""
from setuptools import setup

setup(
    setup_requires=["pbr"],
    pbr=True,
    install_requires=[
        "httpx",
        "pycryptodome>=3.4",
        "pyjwt>=2.1.0",
    ],
)
