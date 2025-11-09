from setuptools import setup, find_packages
with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()
setup(
    name="MainyDB",
    version="1.0.1",
    author="devid",
    author_email="devidrru@gmail.com",
    description="A lightweight, embedded MongoDB-like database in a single file",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/dddevid/MainyDB",
    packages=find_packages(),
    classifiers=[
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.10",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Topic :: Database",
        "Topic :: Software Development :: Libraries",
    ],
    python_requires=">=3.10",
    install_requires=[
        "Pillow>=9.0.0",
    ],
)