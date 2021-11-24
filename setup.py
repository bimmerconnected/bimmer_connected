"""Python package description."""
from setuptools import setup

setup(
    setup_requires=['pbr'],
    pbr=True,
    install_requires=[
        "requests",
        "pycryptodome",
        "pyjwt",
    ]
)
