"""Python package description."""
from setuptools import setup, find_packages

from bimmer_connected.version import __version__ as version

def readme():
    """Load the readme file."""
    with open('README.rst') as readme_file:
        return readme_file.read()

setup(
    name="bimmer_connected",
    version=version,
    author="gerard33",
    author_email="bietenbak@yahoo.com",
    description="Library to read data from the BMW Connected Drive portal",
    long_description=readme(),
    long_description_content_type="text/x-rst",
    url="https://github.com/bimmerconnected/bimmer_connected",
    packages=['bimmer_connected'],
    install_requires=[
        'requests', 'typing>=3,<4;python_version<"3.5"'
    ],
    keywords='BMW Connected Drive home automation',
    zip_safe=False,
    extras_require={
        'testing': ['pytest']
    },
    entry_points={
        'console_scripts': [
            'bimmerconnected=bimmer_connected.cli:main'
        ],
    },
    license='Apache 2.0',
    classifiers=[
        'Development Status :: 4 - Beta',
        'Intended Audience :: Developers',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: 3.8',
    ],
)
