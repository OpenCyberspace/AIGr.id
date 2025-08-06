from setuptools import setup, find_packages

setup(
    name="aios_llama_cpp",
    version="0.1.0",
    author="Your Name",
    author_email="your.email@example.com",
    description="AIOps utility library for interacting with LLaMA.cpp models and tracking LLM metrics",
    long_description=open("README.md").read(),
    long_description_content_type="text/markdown",
    url="",  # optional
    packages=find_packages(),
    install_requires=[
        "prometheus-client",
        "redis",
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
