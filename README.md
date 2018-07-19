# clics2

This repository contains the python package `pyclics` which can be used to compute colexification networks like
the ones presented on http://clics.clld.org from lexical datasets published in CLDF. In particular, this package
implements the methods described in the paper

> J.-M. List et al. (forthcoming): CLICS 2: An improved database of cross-linguistic colexifications assembling lexical data with the help of cross-linguistic data formats. Linguistic Typology. [DOI: 10.1515/lingty-2018-0010](https://doi.org/10.1515/lingty-2018-0010).

Note: `pyclics` requires python >=3.5

[![PyPI version](https://badge.fury.io/py/pyclics.svg)](https://pypi.org/project/pyclics)
[![Build Status](https://travis-ci.org/clics/clics2.svg?branch=master)](https://travis-ci.org/clics/clics2)
[![codecov](https://codecov.io/gh/clics/clics2/branch/master/graph/badge.svg)](https://codecov.io/gh/clics/clics2)


## Command Line Interface

To use `pyclics`, install the package - preferably in a fresh 
[virtual environemt](http://docs.python-guide.org/en/latest/dev/virtualenvs/) running

```shell
$ pip install pyclics
```

Or if you want to hack on `pyclics`, fork the repository, clone your fork and install in development mode:

```shell
$ git clone https://github.com/<your-github-user>/clics2
$ cd clics2
$ pip install -e .
```

Installing `pyclics` will also install a command `clics` on your computer, which provides the command-line interface to 
CLICS functionality.

To get help on using `clics`, run
```shell
$ clics --help
```

In the following we list the major sub-commands of `clics`. Most of these commands create some output,
which by default will be written to files and directories in the current working directory. This can be
changed by passing a different directory to each command using the `--output=path/to/output` option.


### Loading the Data

CLICS data can be loaded from lexibank datasets, i.e. from lexical datasets following the 
[conventions of the lexibank project](https://github.com/lexibank/lexibank/wiki). In particular,
lexibank datasets can be installed similar to python packages, using a command like

```shell
$ pip install -e git+https://github.com/lexibank/allenbai.git#egg=lexibank_allenbai
```

for the [allenbai dataset](https://github.com/lexibank/allenbai).

The datasets used in the paper are listed in
[datasets.txt](datasets.txt) - specifying exact versions - and
can be installed wholesale via

```shell
$ pip install -r datasets.txt
```

Note that these datasets are also available from (and archived at) the [CLICS community at ZENODO](https://zenodo.org/communities/clics).

Once installed, all datasets can be loaded into the CLICS sqlite database, running the `load` subcommand.
This subcommand must have access to clones or exports of the following data repositories:
- [clld/concepticon-data](https://github.com/clld/concepticon-data) >= v1.2.0 (to fetch concept metadata)
- [clld/glottolog](https://github.com/clld/glottolog) >= 9701cb0 (to fetch language metadata)

The locations of these repositories must be passed as arguments to the `load` subcommand:
```shell
$ clics load path/to/concepticon-data path/to/glottolog
```

An overview of the installed and loaded datasets is available via the `clics datasets` command.
Running this command prints a table to the screen, using the same format as the one on page 11 of
the paper:

```shell
$ clics datasets
#    Dataset            Glosses    Concepticon    Varieties    Glottocodes    Families
---  ---------------  ---------  -------------  -----------  -------------  ----------
1    allenbai               498            499            9              3           1
2    bantubvd               430            415           10             10           1
3    beidasinitic           905            700           18             18           1
4    bowernpny              338            338          170            168           1
5    hubercolumbian         361            343           69             65          16
6    ids                   1310           1305          321            276          60
7    kraftchadic            428            428           67             60           3
8    northeuralex          1015            940          107            107          21
9    robinsonap             398            393           13             13           1
10   satterthwaitetb        422            418           18             18           1
11   suntb                  996            905           48             48           1
12   tls                   1523            808          120             97           1
13   tryonsolomon           323            311          111             96           5
14   wold                  1814           1457           41             41          24
15   zgraggenmadang         306            306           98             98           1
     TOTAL                    0           2487         1220           1028          90
```

The remaining commands compute networks and various derived data formats from the CLICS sqlite database.
These commands are given here "in order", i.e. subsequent commands require previous ones to have been
run (with the same parameters).


### Calculate Colexification Network

```shell
$ clics [-v] [-t 1] [-f families|languages|words] colexification
```

Calculates the colexification network. Use `-t` to handle the threshold (if `-t 3` and `-f families` this means only 
colexifications reflected in 3 families are considered. Data is written to a file in the folder `graph/`. 

The colexifications in the paper have been calculated with the following parameters

```shell
$ clics -t 3 -f families colexification
```

In addition to computing the network, the command also outputs the 10 most often colexified pairs of concepts,
as given on page 12 of the paper:

```bash
  ID A  Concept A                     ID B  Concept B                   Families    Languages    Words
------  --------------------------  ------  ------------------------  ----------  -----------  -------
  1370  MONTH                         1313  MOON                              56          289      294
   906  TREE                          1803  WOOD                              55          211      310
    72  CLAW                          1258  FINGERNAIL                        50          209      216
  2266  SON-IN-LAW (OF WOMAN)         2267  SON-IN-LAW (OF MAN)               49          262      285
  2264  DAUGHTER-IN-LAW (OF WOMAN)    2265  DAUGHTER-IN-LAW (OF MAN)          47          235      262
  1608  LISTEN                        1408  HEAR                              47          102      105
   629  LEATHER                        763  SKIN                              46          233      255
  2259  FLESH                          634  MEAT                              46          222      232
  1307  LANGUAGE                      1599  WORD                              45           94       98
  1228  EARTH (SOIL)                   626  LAND                              43          158      181
```


### Calculate Community Analysis

```shell
$ clics [-v] [-t 1] [-f families] [-n] [-g network] communities
```

Clusters the concepts in the network using the infomap algorithm.

Note that `-t` and `-f` are only needed to identify the graph you have calculated with the `colexification` command above.
The `-g` flag indicates the name of the network you want to load, that is, the name of the data stored in `graphs/`. 
Colexification analyses are named by three components as `g-t-f.gml`, with g pointing to the base name, t to the threshold,
and f to the filter. Use the flag `-n` to normalize the weights before calculation.

The communities in the paper have been calculated with the following parameters:

```shell
$ clics -t 3 -f families communities
```

Summary statistics of the resulting clustered network are available via the `graph-stats` subcommand:

```shell
$ clics -t 3 -g infomap -f families graph-stats   
-----------  ----
nodes        1534
edges        2638
components     96
communities   248
-----------  ----
```


### Calculate Subgraph Output

```shell
$ clics -t 3 subgraph
```

Breaks down the complete network into display-friendly subgraphs.


### Inspecting the networks

Now you can open `app/index.html` in your browser to inspect the colexification networks detected in the
datasets.

If you loaded the datasets used for the CLICS2 paper, you could
- inspect the `SAY` cluster from page 16
  of the paper by choosing `Infomap` as graph type, typing `SAY` in the concept selection box and clicking `OK`
- or investigate the curious colexifications between `FOOT` and `WHEEL` (too few for the concepts to get clustered
  by infomap) by choosing `SubGraph` as graph type, typing `WHEEL` in the concept selection box and clicking `OK`.
