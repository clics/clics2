from setuptools import setup, find_packages


setup(
    name='pyclics',
    version='0.1',
    author='Johann-Mattis List and Robert Forkel',
    packages=find_packages(),
    url='https://github.com/lingpy/clics-data',
    install_requires=[
        'lingpy',
        'pycldf~=1.0',
        'clldutils~=2.0',
        'geojson',
        'python-igraph',
        'unidecode'
    ],
    extras_require={
        'dev': [
            'tox',
            'flake8',
            'wheel',
            'twine',
        ],
        'test': [
            'mock',
            'pytest>=3.1',
            'pytest-mock',
            'pytest-cov',
            'coverage>=4.2',
        ],
    },
    entry_points={
        'console_scripts': ['clics=pyclics.cli:main'],
    },
)
