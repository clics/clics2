import argparse
import sqlite3


def pk(table=None):
    return 'dataset_ID || {0}'.format('{0}_ID'.format(table) if table else 'ID')


def select(table, where):
    return "SELECT {0} FROM {1} WHERE {2}".format(pk(), table, where)


def main(cu, macroareas, families):
    famwhere = ''
    for col, excluded in [('macroarea', macroareas), ('family', families)]:
        for c in excluded:
            if famwhere:
                famwhere += ' OR '
            famwhere += "{0} = '{1}'".format(col, c) if c else "{0} IS NULL".format(col)

    lwhere = "{0} IN ({1})".format(pk('Language'), select('LanguageTable', famwhere))
    fwhere = "{0} IN ({1})".format(pk('Form'), select('FormTable', lwhere))

    # run:
    for table, where in [
        ('CognateSource', '{0} IN ({1})'.format(pk('Cognate'), select('CognateTable', fwhere))),
        ('CognateTable', fwhere),
        ('FormSource', fwhere),
        ('FormTable', lwhere),
        ('LanguageTable', famwhere),
    ]:
        print(table + '...')
        cu.execute("DELETE FROM {0} WHERE {1}".format(table, where))
        print('...{0} rows deleted'.format(cu.rowcount))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Prune forms in a CLICS database.')
    parser.add_argument('db', help="CLICS SQLite database file")
    parser.add_argument('--listm', default=False, action='store_true', help='list macroareas')
    parser.add_argument('--listf', default=False, action='store_true', help='list families')
    parser.add_argument('--exclude-macroarea', default=[], action='append', help='exclude macroarea')
    parser.add_argument('--exclude-family', default=[], action='append', help='exclude family')

    args = parser.parse_args()
    db = sqlite3.connect(args.db)
    cu = db.cursor()
    if args.listm:
        for row in cu.execute("SELECT DISTINCT macroarea FROM LanguageTable"):
            print(row[0] or '')
    elif args.listf:
        for row in cu.execute("SELECT DISTINCT family FROM LanguageTable"):
            print(row[0] or '')
    else:
        main(cu, args.exclude_macroarea, args.exclude_family)
    db.commit()
