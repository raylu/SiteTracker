import pygal
import os
from os import listdir
from os.path import join, isfile
import re

dir = join(os.getcwd(), 'stats\\')
print 'Starting dir:', dir

files = [f for f in listdir(dir) if isfile(join(dir, f)) ]

edits = {}

for start in files:
    try:
        f = open(join(dir, start), 'r')
    except TypeError:
        print 'Could not load start', start
    lines = [l.strip() for l in f]
    for line in lines:
        if not line:
            continue
        if not 'Deleted' in line and not ':' in line:
            data = line.split(' ', 1)
            if len(data) == 1:
                data = [data[0], 'Celeo Servasse']
            if data[1] == '':
                data[1] = 'Celeo Servasse'
            if data[1] == ' ':
                data[1] = 'Celeo Servasse'
            if data[1] == 'Celeo':
                data[1] = 'Celeo Servasse'
            if data[1] == 'DirTee Ore' or data[1] == 'Lord VoldemOre':
                data[1] = 'Elroy Skimms'
            if data[1] in edits:
                edits[data[1]] += int(data[0])
            else:
                edits[data[1]] = int(data[0])
    f.close()

chart = pygal.Bar()
chart.title = 'All time edits over 30'

for a, b in edits.iteritems():
    if b > 30:
        chart.add(a, [b])

chart.render_to_file('chart.svg')

print 'Done'