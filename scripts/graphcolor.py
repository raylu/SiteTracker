import re
from sitemngr.models import Wormhole
from eve_db.models import MapSolarSystem
from pygraphviz import *
import urllib2
from time import sleep
from datetime import datetime
import os
import shutil

cmap = {}
cmap['HS'] = 'gold'
cmap['LS'] = 'purple'
cmap['NS'] = 'brown'
cmap['0'] = 'black'
cmap['1'] = 'blue'
cmap['2'] = 'green'
cmap['3'] = 'yellow'
cmap['4'] = 'orange'
cmap['5'] = 'red'
cmap['6'] = 'black'

start = os.path.join(os.getcwd() + '/graph.png')
destination = os.path.join(os.getcwd() + '/sitemngr/static/pictures/graph.png')

def get_color(system_name):
    system = None
    if re.match(r'J\d{6}', system_name):
        return get_color_wh(system_name)
    try:
        system = MapSolarSystem.objects.get(name=system_name)
    except MapSolarSystem.DoesNotExist:
        return 'black'
    status = system.security_level
    if status > 0.5:
        return cmap['HS']
    elif status > 0.1:
        return cmap['LS']
    else:
        return cmap['NS']
    
def get_color_wh(system_name):
    level = 1
    try:
        url = 'http://www.ellatha.com/eve/WormholeSystemview.asp?key={}'.format(system_name.replace('J', ''))
        contents = urllib2.urlopen(url).read().split('\n')
        level = 0
        for line in contents:
            if line.startswith('<td bgcolor="#F5F5F5">'):
                if re.match(r'^\d$', line.split('>')[1][0]):
                    level = line.split('>')[1][0]
                    break
        return cmap[level]
    except:
        pass
    return 'black'

def graph():
    g = AGraph(label='Overview')
    wormholes = Wormhole.objects.filter(opened=True, closed=False)
    nodes = []
    nodes.append('J132814')
    for w in wormholes:
        if w.destination.lower() in ['', ' ', 'unopened', 'closed'] or w.start.lower() in ['', ' ', 'unopened', 'closed']:
            continue
        if not w.start in nodes:
            nodes.append(w.start)
        if not w.destination in nodes:
            nodes.append(w.destination)
    for n in nodes:
        g.add_node(n, color=get_color(n))
    for w in wormholes:
        if w.destination.lower() in ['', ' ', 'unopened', 'closed'] or w.start.lower() in ['', ' ', 'unopened', 'closed']:
            continue
        g.add_edge(w.start, w.destination)
    g.layout()
    g.draw('graph.png')

def should_update():
    return True

def move():
    shutil.move(start, destination)

def repeat():
    while 1:
        if should_update():
            graph()
            sleep(5)
            move()
            print 'Graphed and moved', datetime.now().strftime('%m/%d/%Y %H:%M:%S')
            sleep(60 * 2)

def run():
    repeat()
