import setuptools

with open('README.md', 'r') as reader :
    long_description = reader.read()


requirements = []
with open('requirements.txt', 'r') as packages :
    for package in packages :
        requirements.append(package)

setuptools.setup(
    name = "algo_outputs",
    version = "0.0.1",
    author = "cognitifai",
    description = "Algorithm outputs saving and query APIs (Part of AiOS FrameDB)",
    long_description = long_description,
    long_description_content_type = "text/markdown",
    packages = setuptools.find_packages(),
    classifiers = [
        "Programming Language :: Python :: 3",
        "License :: None :: Closed License",
        "Operating System :: OS Independent"
    ],
    python_requires = '>=3.5',
    install_requires = requirements
)