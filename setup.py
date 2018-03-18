"""Python package description."""
from setuptools import setup, find_packages

from bimmer_connected.const import __version__ as version


def readme():
    """Load the readme file."""
    with open('README.rst') as readme_file:
        return readme_file.read()


setup(
    name='bimmer_connected',
    version=version,
    description='Library to read data from the BMW Connected Drive portal',
    long_description=readme(),
    url='https://github.com/ChristianKuehnel/bimmer_connected',
    author='Christian Kühnel',
    author_email='christian.kuehnel@gmail.com',
    license='Apache 2.0',
    classifiers=[
        'Development Status :: 3 - Alpha',
        'Intended Audience :: Developers',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.4',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3.6',
    ],
    packages=find_packages(),
    install_requires=['requests', 'typing>=3,<4'],
    keywords='BMW Connected Drive home automation',
    zip_safe=False,
    extras_require={'testing': ['pytest']},
    scripts=['bimmerconnected'],
)
