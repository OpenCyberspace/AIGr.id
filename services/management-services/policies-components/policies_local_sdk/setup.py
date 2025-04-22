from setuptools import setup, find_packages

# Read requirements from requirements.txt
with open("requirements.txt", "r") as req_file:
    install_requires = req_file.read().splitlines()

# Read long description from README.md if available
try:
    with open("README.md", "r", encoding="utf-8") as fh:
        long_description = fh.read()
except FileNotFoundError:
    long_description = ""

setup(
    name="aios_policy_sandbox",
    version="0.1.0",
    author="openvision.ai",
    author_email="prasanna@openvision.ai",
    description="Policies SDK",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="",  
    packages=find_packages(),
    install_requires=install_requires,
    classifiers=[
        "Programming Language :: Python :: 3",
        "Operating System :: OS Independent",
    ],
    python_requires='>=3.7',
)
