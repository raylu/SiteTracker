import pygal
import os
from os import listdir
from os.path import join, isfile

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
                data = [data[0], 'celeo_servasse']
            data[1] = data[1].lower().replace(' ', '_')
            if data[1] == '':
                data[1] = 'celeo_servasse'
            if data[1] == ' ':
                data[1] = 'celeo_servasse'
            if data[1] == 'root':
                data[1] = 'celeo_servasse'
            if data[1] == 'dirtee_ore' or data[1] == 'lord_voldemore':
                data[1] = 'elroy_skimms'
            if data[1] in edits:
                edits[data[1]] += int(data[0])
            else:
                edits[data[1]] = int(data[0])
    f.close()

chart = pygal.Bar()
chart.title = 'Number of edits per user'

for a, b in edits.iteritems():
    if b > 50:
        chart.add(a, [b])

chart.render_to_file('chart.svg')

print 'Done'