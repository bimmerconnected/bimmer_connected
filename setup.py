"""Python package description."""
from setuptools import setup

setup(
    setup_requires=['pbr'],
    pbr=True,
    install_requires=[
        "requests>=2.24.0",
        "pycryptodome>=3.4",
        "pyjwt>=2.1.0",
    ]
)
