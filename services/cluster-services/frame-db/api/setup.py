from setuptools import setup, find_packages

setup(
    name="framedb_api",
    version="",
    author="",
    author_email="",
    description="",
    long_description="",
    long_description_content_type="text/markdown",
    url="",
    project_urls={
        "Bug Tracker": "",
    },
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved ::",
        "Operating System :: OS Independent",
    ],
    package_dir={"": "src"},
    packages=find_packages(where="src"),
    python_requires=">=3.7",
    install_requires=[
        "redis",
        "requests"
    ],
)
