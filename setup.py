from setuptools import setup, find_packages


setup(
    name='pyclics',
    version='0.1',
    author='Johann-Mattis List',
    packages=find_packages(),
    url='https://github.com/lingpy/clics-data',
    install_requires=[
        'lingpy',
        'clldutils',
        'pylexibank',
        'geojson',
        'python-igraph',
    ],
    tests_require=['nose', 'coverage', 'mock'],
    entry_points={
        'console_scripts': ['clics=pyclics.cli:main'],
    },
)
