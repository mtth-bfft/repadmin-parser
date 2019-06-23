#!/usr/bin/env python3

import argparse
import csv
import datetime
import json
import re
import sys

# Global constant settings

HIGHLIGHTED_ATTR_NAMES = ('unicodePwd',)
DN_COLOR = '\033[1;36;40m'
STANDARD_ATTR_NAME_COLOR = '\033[0;37;40m'
HIGHLIGHTED_ATTR_NAME_COLOR = '\033[1;31;40m'
ACTION_COLORS = {
    'add': '\033[1;37;40m',
    'modify': '\033[1;35;40m',
    'delete': '\033[1;32;40m',
}

# Formatting functions

def format_attr(name, val):
    if name in HIGHLIGHTED_ATTR_NAMES:
        return '{}{}\033[0;37;40m'.format(HIGHLIGHTED_ATTR_NAME_COLOR, name)
    else:
        return '{}{}\033[0;37;40m'.format(STANDARD_ATTR_NAME_COLOR, name)

def format_datetime(s):
    if len(s) == 0:
        return ''
    s = s.replace('Romance Daylight Time', '+0100')
    s = datetime.datetime.strptime(s, '%m/%d/%Y %I:%M:%S %p %z')
    s = s.strftime('%Y-%m-%d %H:%m:%S UTC')
    return s

def strip_lines(line_iter):
    for line in line_iter:
        line = line.strip()
        if line.startswith('New cookie written') or \
                line.startswith('Repadmin: running command') or \
                line.startswith('Using cookie from') or \
                line.startswith('==== SOURCE DSA') or \
                line.startswith('Objects returned:'):
            yield ''
        else:
            yield line

# Pipeline step 1: strip and merge lines (some DNs contain a \n, which is
# sometimes escaped but sometimes not, which results in a line being
# split in two. This function merges these two lines back together)

def escape_linefeeds_in_values(line_iter):
    prev_line = None
    obj_start = re.compile(r'^\(\d+\) [a-z]+')
    obj_attr  = re.compile(r'^\d+> ')
    for line in strip_lines(line_iter):
        # Line is empty, skip it
        if len(line) == 0:
            continue
        # Line is the start of a new object
        if obj_start.match(line):
            if prev_line is not None:
                yield prev_line
            prev_line = line
        # Line is an edited attribute of an already started object
        elif obj_attr.match(line):
            if prev_line is not None:
                yield prev_line
            prev_line = line
        # Line is the rest of the previous line, merge them back together
        else:
            prev_line += '\\0A' + line
    # Final flush of our buffer
    if prev_line is not None:
        yield prev_line

# Pipeline step 2: for each object, for each attribute, save that
# attribute into that object

def split_objects(line_iter):
    line_iter = escape_linefeeds_in_values(line_iter)
    line = next(line_iter, None)
    if line is None:
        return
    while True:
        if len(line) == 0:
            line = next(line_iter, None)
            if line is None:
                break
            continue
        if not line.startswith('('):
            print('Error: log does not start with an object definition')
            print('Expected parenthesis, got "{}"'.format(line))
            quit()
        obj = {'attributes': {}}
        objnum, obj['action'], obj['dn'] = line.split(' ', 2)
        objnum = int(objnum.strip('()'))
        while True:
            line = next(line_iter, None)
            if line is None:
                yield obj
                return
            if len(line) == 0:
                continue
            if line.startswith('('):
                break
            attr_count, attrnamevalues = line.split('>', 1)
            attr_count = int(attr_count)
            attr_name, attr_values = attrnamevalues.split(':', 1)
            attr_name = attr_name.strip()
            attr_values = [val.strip() for val in attr_values.strip().split(';')]
            obj['attributes'][attr_name] = attr_values
        yield obj

# Output formats, one function per format

def output_colored(obj):
    action = obj['action']
    if action in ACTION_COLORS:
        action = '{}{}\033[0;37;40m'.format(ACTION_COLORS[action], action)
    print('[{}] {}{}\033[0;37;40m {}'.format(action, DN_COLOR, obj['dn'], ', '.join(format_attr(name, val) for name, val in obj['attributes'].items())))

def output_tsv(obj, tsvwriter):
    if len(obj['attributes']) == 0:
        tsvwriter.writerow((obj['dn'], obj['action'], '', ''))
    for arg_name, arg_val in obj['attributes'].items():
        tsvwriter.writerow((obj['dn'], obj['action'], arg_name, ';'.join(arg_val)))

def output_passwords(obj, tsvwriter):
    if obj['action'] == 'modify' and \
            'unicodePwd' in obj['attributes'] and \
            'pwdLastSet' in obj['attributes']:
        # Don't output deleted objects getting recycled: their unicodePwd
        # gets changed (to an empty value), but we don't care. These objects
        # were already deleted.
        if 'isRecycled' in obj['attributes'] and \
                obj['attributes']['isRecycled'] == ['TRUE']:
            return
        pwdlastset = obj['attributes']['pwdLastSet'][0]
        pwdlastset = format_datetime(pwdlastset)
        tsvwriter.writerow((pwdlastset, obj['dn']))

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('inlog', default=sys.stdin, type=argparse.FileType('r', encoding='utf-8', errors='backslashreplace'), nargs='?')
    parser.add_argument('--outfile', '-o', default=sys.stdout, type=argparse.FileType('w'), nargs='?')
    parser.add_argument('--format', choices=('tsv', 'color', 'passwords'), default='color', nargs='?')
    args = parser.parse_args()

    full_log = args.inlog.read()
    full_log = full_log.replace('\r\n', '\n')
    full_log = full_log.split('\n')
    line_iter = iter(full_log)

    if args.format == 'tsv':
        writer = csv.writer(args.outfile, delimiter='\t')
        for obj in split_objects(line_iter):
            output_tsv(obj, writer)
    elif args.format == 'color':
        for obj in split_objects(line_iter):
            output_colored(obj)
    elif args.format == 'passwords':
        writer = csv.writer(args.outfile, delimiter='\t')
        for obj in split_objects(line_iter):
            output_passwords(obj, writer)

