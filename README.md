# Clics-Data
This is a data-directory for CLICS where we store and edit and exchange new data and ideas to be produced in the future.

## Command Line Interface

In order to make use of all the options that we offer in clics-data, you should install the pyclics-package shipped along with clics-data in develop mode in Python:

```shell
$ sudo python setup.py develop
```

This guarantees that all actual changes made to the data will directly take actioin.

The command-line interface will define a new command on your computer, the command "clics", which you can use to calculate certain aspects of the clics data.

In the following we list some major commands.

### Create the Data

```shell
$ clics [-v] load ids wold
```

This command loads all data in clics. It requires that the [pylexibank app](https://github.com/glottobank/lexibank-data) is installed, and that the resources IDS and WOLD have been downloaded. Use or omit `-v` depending on whether you prefer verbose or silent output.

### Get the Languages

```shell
$ clics [-v] get languages
```

Calculates basic statistics about the languages in the sample and stores them in `stats/languages.csv`. This also creates a geographical plot of the languages which is then placed in the folder `geo/`. 

### Calculate Coverage of Concepts

```shell
$ clics [-v] get coverage
```

Calculate coverage of concepts (how many languages reflect them, etc.) and write results to `stats/concepts.csv`.

### Calculate Colexification Network

```shell
$ clics [-v] get colexification [-t 1] [-f families|languages|words]
```

Calculate the colexification network. Use `-t` to handle the threshold (if `-t 3` and `-f families` this means only colexifications reflected in 3 families are considered. Data is written to a file in the folder `graph/`. You need to run the following commands before:

```shell
$ clics load ids wold
$ clics get languages
$ clics get coverage
```

### Calculate Community Analysis

```shell
$ clics [-v] get community [-t 1] [-f families] [-n] [-g network]
```

Note that `-t` and `-f` are only needed ot identify the graph you have calculated with the get-colexification routine above. The `-g` flag indicates the name of the network you want to load, that is, the name of the data stored in `graphs/`. Colexification analyses are named by three components as `g-t-f.gml`, with g pointing to the base name, t to the threshold, and f to the filter. Use the flag `-n` to normalize the weights before calculation.


### Calculate Articulation Points

```shell
$ clics [-v] get articulationpoint [-t 1] [-f families] [-g infomap]
```

You need to have calculated an infomap cluster analysis before. If done so, this command calculates the articulation points in the graph and writes them to an annotated graph which is placed in the folder `graphs/`.



