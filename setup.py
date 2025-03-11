from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="statement-python",
    version="0.1.0",
    author="Derek Willis",
    author_email="dwillis@gmail.com",
    description="Parse RSS feeds and HTML pages containing press releases from members of Congress",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/dwillis/statement-python",
    packages=find_packages(),
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires=">=3.6",
    install_requires=[
        "requests>=2.25.0",
        "beautifulsoup4>=4.9.3",
        "lxml>=4.6.0",
        "python-dateutil>=2.8.1",
        "pyyaml>=5.4.1",
    ],
)