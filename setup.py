"""Python package description."""
import setuptools

with open("README.rst") as fp:
    long_description = fp.read()

version = {}
with open("bimmer_connected/version.py") as fp:
    exec(fp.read(), version)

setuptools.setup(
    name="bimmer_connected",
    version=version['__version__'],
    author="m1n3rva, gerard33",
    author_email="bietenbak@yahoo.com",
    description="Library to read data from the BMW Connected Drive portal",
    long_description=long_description,
    long_description_content_type="text/x-rst",
    url="https://github.com/bimmerconnected/bimmer_connected",
    packages=setuptools.find_packages(),
    install_requires=[
        "requests",
    ],
    license='Apache 2.0',
    classifiers=[
        "Programming Language :: Python :: 3",
    ],
)