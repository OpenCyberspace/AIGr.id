import setuptools

with open('README.md', 'r') as reader :
    long_description = reader.read()


requirements = []
with open('requirements.txt', 'r') as packages :
    for package in packages :
        requirements.append(package)

setuptools.setup(
    name = "redis_router",
    version = "0.0.1",
    author = "cognitifai",
    description = "A package that implementes routing functionalities over Redis client (Part of AiOS FrameDB)",
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