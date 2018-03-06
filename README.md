# Clics-Data
This is a data-directory for CLICS where we store and edit and exchange new data and ideas to be produced in the future.

## Command Line Interface

In order to make use of all the options that we offer in clics-data, you should install the pyclics-package shipped along with clics-data in develop mode in Python:

```shell
$ sudo python setup.py develop
```

Installing `pyclics` will also install a command `clics` on your computer, which provides the command-line interface to CLICS functionality, i.e. lets you calculate certain aspects of the clics data.

To get help on using `clics`, run
```shell
$ clics --help
```

In order for the `pyclics` package to work, it must have access to clones or exports of the following data repositories:
- [clld/glottolog](https://github.com/clld/glottolog)
- [clld/concepticon-data](https://github.com/clld/concepticon-data)

Some `clics` sub-commands require access to the data repositories listed above.
If this is the case, the local location of these repositories can be passed
using the options `--glottolog-repos`, `--concepticon-repos` and `--lexibank-repos`.
By default, these repositories are expected to reside in directories
`glottolog`, `concepticon-data` and `lexibank-data`, alongside `clics-data`.

If you can't remember which sub-command requires
which data repos, simply pass all three options to all sub-commands,
possibly even by aliasing a properly configured `clics` command. Using
the bash shell this would look as follows:
```shell
$ alias myclics="clics --glottolog-repos=... --concepticon-repos=... "
```

In the following we list the major sub-commands of `clics`. For readability, we omit the `--*-repos` options, i.e. the commands as
given below will only work on your system if you have the data repositories available at the default locations.


### Create the Data

```shell
$ clics load ids wold
```

This command loads data in clics which you is located in the `cldf`-folder in your clics installation. It converts data into an intermediate format which is then placed in the folder `datasets`. As this folder is already populated, you won't need this command to get started, unless you plan to use your own data.

### Get the Languages

```shell
$ clics languages
```

Calculates basic statistics about the languages in the sample and stores them in `stats/languages.csv`. This also creates a geographical plot of the languages which is then placed in the folder `geo/`. 

### Calculate Coverage of Concepts

```shell
$ clics concepts
```

Calculate coverage of concepts (how many languages reflect them, etc.) and write results to `stats/concepts.csv`.

### Calculate Colexification Network

```shell
$ clics [-v] colexification [-t 1] [-f families|languages|words]
```

Calculate the colexification network. Use `-t` to handle the threshold (if `-t 3` and `-f families` this means only colexifications reflected in 3 families are considered. Data is written to a file in the folder `graph/`. You need to run the following commands before:

```shell
$ clics load ids wold
$ clics languages
$ clics coverage
```

### Calculate Community Analysis

```shell
$ clics [-v] communities [-t 1] [-f families] [-n] [-g network]
```

Note that `-t` and `-f` are only needed to identify the graph you have calculated with the get-colexification routine above. The `-g` flag indicates the name of the network you want to load, that is, the name of the data stored in `graphs/`. Colexification analyses are named by three components as `g-t-f.gml`, with g pointing to the base name, t to the threshold, and f to the filter. Use the flag `-n` to normalize the weights before calculation.


### Calculate Subgraph Output

```shell
$ clics -t 3 subgraph
```

This will populate the folder `app` with json-files which contain the network information needed to browse the data. 




