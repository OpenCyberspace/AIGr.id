from setuptools import setup, find_packages

setup(
    name="aios_model_splitter",
    version="0.1.0",
    packages=find_packages(),
    install_requires=[
        "requests",
    ],
    author="Prasanna HN",
    author_email="prasabba@opencyberspace.org",
    description="AIOS container lifecycle and model splitting utilities",
    python_requires=">=3.8",
)
