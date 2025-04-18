from setuptools import setup, find_packages

setup(
    name="aios_transformers",
    version="0.1.0",
    author="Prasanna HN",
    author_email="prasanna@opencyberspacee.org",
    description="AIOps utilities and metrics integration for Hugging Face Transformers",
    long_description=open("README.md").read(),
    long_description_content_type="text/markdown",
    url="",  # optional
    packages=find_packages(),
    install_requires=[
        "transformers==4.46.3",
        "torch==2.4.1",  # or higher depending on features used
        "prometheus-client==0.14.0",
        "redis==3.2.1",
        "accelerate==1.0.1"
    ],
    python_requires='>=3.8',
    classifiers=[
        "Programming Language :: Python :: 3",
        "Operating System :: OS Independent",
        "License :: OSI Approved :: MIT License",
        "Intended Audience :: Developers",
        "Topic :: Scientific/Engineering :: Artificial Intelligence"
    ],
    include_package_data=True,
    zip_safe=False
)
