# Cooking with CLICS

This "cookbook" contains recipes for solving re-current issues encountered when
trying to attack research questions with CLICS.


## The CLICS SQLite Database

Many of the recipes given here rely on `pyclics` loading all data into a single
[SQLite](https://www.sqlite.org/) database. The functionality to do so is largely
implemented in the `pylexibank` package; thus the CLICS database is based on a generic
database to store multiple Lexibank datasets. Due to this, the database contains
some tables which are irrelevant for CLICS (and often empty). The important tables
for CLICS are

### **dataset**

The **dataset** table stores core metadata about each loaded lexibank dataset in one row.
Rows in all other tables are loaded in relation to one dataset (they one they came with);
thus all tables except for **dataset** have *composite primary keys*, where 
`dataset.ID` is one component.

```sql
CREATE TABLE dataset (
    ID TEXT PRIMARY KEY NOT NULL,
    name TEXT,
    version TEXT,
    metadata_json TEXT
);
```

### **LanguageTable**

Metadata about languages is stored in the **LanguageTable**. Note that each variety
or doculect in each source dataset gets an individual row in this table.

```sql
CREATE TABLE LanguageTable (
    `ID` TEXT,
    `Name` TEXT,
    `Glottocode` TEXT,
    `Glottolog_Name` TEXT,
    `ISO639P3code` TEXT,
    `Macroarea` TEXT,
    `Family` TEXT,
    `dataset_ID` TEXT NOT NULL, `Latitude` REAL, `Longitude` REAL, `author` TEXT, `url` TEXT, `typedby` TEXT, `checkedby` TEXT, `notes` TEXT,
    PRIMARY KEY(`dataset_ID`, `ID`),
    FOREIGN KEY(`dataset_ID`) REFERENCES dataset(`ID`)
);
```

### **ParameterTable**

Rows in the **ParameterTable** in CLICS correspond to elicitation glosses used in the
source datasets. These are linked to Concepticon Concept Sets and enriched with
Concepticon metadata.

```sql
CREATE TABLE ParameterTable (
    `ID` TEXT,
    `Name` TEXT,
    `Concepticon_ID` TEXT,
    `Concepticon_Gloss` TEXT,
    `Chinese_Gloss` TEXT,
    `dataset_ID` TEXT NOT NULL, `Ontological_Category` TEXT, `Semantic_Field` TEXT, `Spanish_Gloss` TEXT, `Swahili_gloss` TEXT,
    PRIMARY KEY(`dataset_ID`, `ID`),
    FOREIGN KEY(`dataset_ID`) REFERENCES dataset(`ID`)
);
```

### **FormTable**

The actual forms (or words) in CLICS are stored in the **FormTable**, each 
- linked to its source dataset
- linked to its language/variety/doculect
- linked to its gloss
- enriched with the CLICS value - i.e. the representation which is used in CLICS
  to detect colexifications.

```sql
CREATE TABLE FormTable (
    `ID` TEXT,
    `Local_ID` TEXT,
    `Language_ID` TEXT,
    `Parameter_ID` TEXT,
    `Value` TEXT,
    `Form` TEXT,
    `Segments` TEXT,
    `Comment` TEXT,
    `Cognacy` TEXT,
    `Loan` INTEGER,
    `dataset_ID` TEXT NOT NULL, `clics_form` TEXT, `Transcription` TEXT, `AlternativeValue` TEXT, `AlternativeTranscription` TEXT, `Orthography` TEXT, `Word_ID` TEXT, `word_source` TEXT, `Borrowed` TEXT, `Borrowed_score` TEXT, `comment_on_borrowed` TEXT, `Analyzability` TEXT, `Simplicity_score` TEXT, `reference` TEXT, `numeric_frequency` TEXT, `age_label` TEXT, `gloss` TEXT, `integration` TEXT, `salience` TEXT, `effect` TEXT, `contact_situation` TEXT,
    PRIMARY KEY(`dataset_ID`, `ID`),
    FOREIGN KEY(`dataset_ID`) REFERENCES dataset(`ID`),
    FOREIGN KEY(`dataset_ID`,`Language_ID`) REFERENCES LanguageTable(`dataset_ID`,`ID`),
    FOREIGN KEY(`dataset_ID`,`Parameter_ID`) REFERENCES ParameterTable(`dataset_ID`,`ID`)
);
```

### Notes

- **Warning:** When joining metadata from language or parameter table to forms, care
must be taken to join on each component of the primary key - otherwise aggregates
my be grossly incorrect.
- SQLite is *not* case-sensitive; thus, in recipes we will often write *languagetable* rather than *LanguageTable*


## Exporting CLICS data to CSV

Despite efforts like [CLDF](https://cldf.clld.org), linguists still rely on tools which require 
customized data input - often in the form of semi-specified CSV (comma-separated values).

Fortunately, exporting CLICS data to such formats is simple. Since all CLICS data is
loaded into an SQLite database, such exports are only one SQL query away:

SQLite provides a [command-line interface](https://www.sqlite.org/cli.html), called `sqlite3` or `sqlite3.exe`,
which we will use in the following to export results of custom SQL queries run on a
CLICS database to CSV. `sqlite3` can be used interactively, so after connecting to
a database (i.e. passing the path of a database file as parameter to `sqlite3`),
you are presented with a prompt, accepting SQL and some [special commands](https://www.sqlite.org/cli.html#special_commands_to_sqlite3_dot_commands_).

```bash
$ sqlite3 clics.sqlite 
SQLite version 3.11.0 2016-02-15 17:29:24
Enter ".help" for usage hints.
sqlite> 
```

We use three special commands (a.k.a. *dot-commands*) to switch the output mode to CSV:

```bash
sqlite> .headers on
sqlite> .mode csv
sqlite> .output clics.csv
```

The results of the next query will be written to `clics.csv`:

```bash
sqlite> select * from languagetable;
sqlite> .quit
```

```bash
$ head -n5 clics.csv 
ID,Name,Glottocode,Glottolog_Name,ISO639P3code,Macroarea,Family,dataset_ID,Latitude,Longitude,author,url,typedby,checkedby,notes
Jianchuan,Jianchuan,cent2004,,,Eurasia,Sino-Tibetan,lexibank-allenbai,26.1666,99.7052,,,,,
Eryuan,Eryuan,cent2004,,,Eurasia,Sino-Tibetan,lexibank-allenbai,26.1666,99.7052,,,,,
Heqing,Heqing,cent2004,,,Eurasia,Sino-Tibetan,lexibank-allenbai,26.1666,99.7052,,,,,
Lanping,Lanping,cent2004,,,Eurasia,Sino-Tibetan,lexibank-allenbai,26.1666,99.7052,,,,,
```

A somewhat more comprehensive export of most of the CLICS data to one CSV file 
could be done using the following SQL:
```sql
SELECT
    f.dataset_ID, f.ID as Form_ID, f.Form, f.clics_form,
    p.name as gloss_in_source, p.Concepticon_ID, p.Concepticon_Gloss,
    l.Name as variety, l.Glottocode, l.ISO639P3code, l.Macroarea, l.Family, l.Latitude, l.Longitude
FROM
    formtable as f, parametertable as p, languagetable as l 
WHERE
    f.dataset_ID = p.dataset_ID AND f.parameter_ID = p.ID 
    AND f.dataset_ID = l.dataset_ID AND f.language_ID = l.ID
ORDER BY
    f.dataset_ID, p.ID, l.ID;
```

Your favorite programming language will also provide a standardised API for accessing the SQLite database directly:

### Python:

```python
import sqlite3
conn = sqlite3.connect('PATH/TO/DB.sqlite')
cursor = conn.cursor()
cursor.execute('select * from languagetable;')
```

### R:

```r
library(DBI)
db <- dbConnect(RSQLite::SQLite(), "PATH/TO/DB.sqlite")
dbGetQuery(db, 'select * from languagetable;')
```


**Notes:** 
- For the datasets being part of the CLICS 2 release this results
  in a 125MB CSV file with 1.062.196 rows starting with
  ```bash
  $ head -n 5 clics.csv | csvformat -T
  dataset_ID	Form_ID	Form	clics_form	gloss_in_source	Concepticon_ID	Concepticon_Gloss	variety	Glottocode	ISO639P3code	Macroarea	Family	Latitude	Longitude
  lexibank-allenbai	1235	ɕi⁵⁵	ci55	firewood	10	FIREWOOD	Eryuan	cent2004		Eurasia	Sino-Tibetan	26.1666	99.7052
  lexibank-allenbai	1236	ɕʰĩ⁵⁵	chi55	firewood	10	FIREWOOD	Heqing	cent2004		Eurasia	Sino-Tibetan	26.1666	99.7052
  lexibank-allenbai	1234	ɕĩ⁵⁵	ci55	firewood	10	FIREWOOD	Jianchuan	cent2004		Eurasia	Sino-Tibetan	26.1666	99.7052
  lexibank-allenbai	1237	ɕĩ⁵⁵	ci55	firewood	10	FIREWOOD	Lanping	cent2004		Eurasia	Sino-Tibetan	26.1666	99.7052
  ```
- The interactive commands can be condensed into a single command by converting
  dot-commands into command options and using redirection to send the output to a file:
  ```bash
  $ sqlite3 -header -csv PATH/TO/DB.sqlite "SELECT ID, name, version FROM dataset" > clics.csv
  ```


## Pruning languages in a CLICS database

If you are only interested in colexifications in a certain subset of languages in a CLICS
database, you could filter the edges of the colexification graph. But it would 