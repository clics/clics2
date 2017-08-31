from setuptools import setup, find_packages


setup(
    name='pyclics',
    version='0.1',
    author='Johann-Mattis List and Robert Forkel',
    packages=find_packages(),
    url='https://github.com/lingpy/clics-data',
    install_requires=[
        'lingpy',
        'pycldf>=1.0rc1'
        'clldutils>=1.13.5',
        'geojson',
        'python-igraph',
        'unidecode'
    ],
    tests_require=['nose', 'coverage', 'mock'],
    entry_points={
        'console_scripts': ['clics=pyclics.cli:main'],
    },
)
