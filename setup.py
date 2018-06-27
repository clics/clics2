from setuptools import setup, find_packages


setup(
    name='pyclics',
    version='0.1',
    author='Johann-Mattis List and Robert Forkel',
    url='https://github.com/clics/clics2',
    classifiers=[
        'Development Status :: 4 - Beta',
        'Intended Audience :: Science/Research',
        'Operating System :: OS Independent',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.4',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3.6',
    ],
    packages=find_packages(where='src'),
    package_dir={'': 'src'},
    install_requires=[
        'lingpy',
        'pycldf~=1.0',
        'pylexibank>=0.7',
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
        'console_scripts': ['clics=pyclics.__main__:main'],
    },
)
