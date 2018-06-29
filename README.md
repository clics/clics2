# clics2

This repository contains the python package `pyclics` which can be used to compute colexification networks like
the ones presented on http://clics.clld.org/graphs from lexical datasets published in CLDF.

Note: `pyclics` require python >=3.4


## Command Line Interface

To use `pyclics`, install the package - preferably in a fresh 
[virtual environemt](http://docs.python-guide.org/en/latest/dev/virtualenvs/):

```shell
$ git clone https://github.com/clics/clics2
$ cd clics2
$ pip install -e .
```

Installing `pyclics` will also install a command `clics` on your computer, which provides the command-line interface to 
CLICS functionality.

To get help on using `clics`, run
```shell
$ clics --help
```

In order for the `pyclics` package to work, it must have access to clones or exports of the following data repositories:
- [clld/glottolog](https://github.com/clld/glottolog)
- [clld/concepticon-data](https://github.com/clld/concepticon-data)

The `clics` sub-command `load` requires access to the data repositories listed above,
thus must be invoked passing in the options `--glottolog-repos` and `--concepticon-repos`.
By default, these repositories are expected to reside in directories
`glottolog` and `concepticon-data`, alongside `clics2`.

In the following we list the major sub-commands of `clics`.


### Loading the Data

CLICS data can be loaded from lexibank datasets, i.e. from lexical datasets following the 
[conventions of the lexibank project](https://github.com/lexibank/lexibank/wiki). In particular,
lexibank datasets can be installed similar to python packages, using a command like

```shell
$ pip install -e git+https://github.com/lexibank/allenbai.git#egg=lexibank_allenbai
```

for the [allenbai dataset](https://github.com/lexibank/allenbai).

The datasets used for the CLICS application at http://clics.clld.org are listed in [datasets.txt](datasets.txt) and
can be installed wholesale via

```shell
$ pip install -r datasets.txt
```

Once installed, all datasets can be loaded into the CLICS sqlite database running

```shell
$ clics --concepticon-repos=path/to/concepticon-data --glottolog-repos=path/to/glottolog load
```

The remaining commands compute networks and various derived data formats from the CLICS sqlite database.
These commands are given here "in order", i.e. subsequent commands require previous ones to have been
run (with the same parameters).


### Calculate Colexification Network

```shell
$ clics [-v] [-t 1] [-f families|languages|words] colexification
```

Calculate the colexification network. Use `-t` to handle the threshold (if `-t 3` and `-f families` this means only 
colexifications reflected in 3 families are considered. Data is written to a file in the folder `graph/`. 

The colexifications in http://clics.clld.org have been calculated with the following parameters:

```shell
$ clics -t 3 -f families colexification
```


### Calculate Community Analysis

```shell
$ clics [-v] [-t 1] [-f families] [-n] [-g network] communities
```

Note that `-t` and `-f` are only needed to identify the graph you have calculated with the `colexification` command above.
The `-g` flag indicates the name of the network you want to load, that is, the name of the data stored in `graphs/`. 
Colexification analyses are named by three components as `g-t-f.gml`, with g pointing to the base name, t to the threshold, and f to the filter. Use the flag `-n` to normalize the weights before calculation.

The communities in http://clics.clld.org have been calculated with the following parameters:

```shell
$ clics -t 3 -f families -n communities
```


### Calculate Subgraph Output

```shell
$ clics -t 3 subgraph
```

This will populate the folder `app` with json-files which contain the network information needed to browse the data. 


### Inspecting the networks

Now you can open `app/index.html` in your browser to inspect the colexification networks detected in the
datasets.
