from setuptools import setup, find_packages

setup(
    name='init_container',
    version='0.1.0',
    description='AIOS init container library',
    author='Prasanna HN',
    author_email='prasanna@opencyberspace.org',
    url='',
    packages=find_packages(),
    install_requires=[
        "redis",
        "requests",
        "prometheus_client",
        "websocket_server",
        "kubernetes",
        "pyhelm"
    ],
    classifiers=[
        'Programming Language :: Python :: 3',
        'License :: OSI Approved :: MIT License',
        'Operating System :: OS Independent',
    ],
    python_requires='>=3.6',
)
