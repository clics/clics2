# coding: utf8
import sys
import argparse
import random
from pathlib import Path

import numpy
from clldutils.clilib import ArgumentParserWithLogging

import pyclics
from pyclics.api import Clics
import pyclics.commands

assert pyclics.commands

random.seed(123456)
numpy.random.seed(123456)


def main():  # pragma: no cover
    parser = ArgumentParserWithLogging(pyclics.__name__)
    parser.add_argument('-t', '--threshold', type=int, default=None)
    parser.add_argument('-f', '--edgefilter', default='families')
    parser.add_argument('-n', '--normalize', action='store_true')
    parser.add_argument('-g', '--graphname', default=None)
    parser.add_argument('-w', '--weight', default='FamilyWeight')
    parser.add_argument('--unloaded', action='store_true', default=False)
    parser.add_argument('-v', '--verbose', default=False, action='store_true')
    parser.add_argument('-o', '--output', default=None, help='output directory')
    parser.add_argument('--api', help=argparse.SUPPRESS, default=Clics(Path('.')))
    args = parser.parse_args()
    if args.output:
        args.api.repos = Path(args.output)
    sys.exit(parser.main(parsed_args=args))
