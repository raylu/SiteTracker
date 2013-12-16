import re
from sitemngr.models import Wormhole
from eve_db.models import MapSolarSystem
from pygraphviz import *
import urllib2
from time import sleep
from datetime import datetime
import pytz
import os

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

emap = {}
emap['Fresh'] = 'bold'
emap['< 50% mass'] = 'dashed'
emap['< 50% mass'] = 'dashed'
emap['< 50% time'] = 'dashes'
emap['VoC'] = 'dotted'
emap['EoL'] = 'dotted'
emap['Unknown'] = 'solid'

def get_edge_type(start, destination):
    wormhole = Wormhole.objects.get(start=start, destination=destination)
    return emap[wormhole.status]

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
    g = AGraph(label='Overview', landscape='false', directed=False, ranksep='0.2')
    g.edge_attr.update(len='1.5', color='black')
    wormholes = Wormhole.objects.filter(opened=True, closed=False)
    now = datetime.now(pytz.utc)
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
        if n == 'J132814':
            g.add_node(n, color='red', fontcolor='red')
            continue
        g.add_node(n, color=get_color(n))
    for w in wormholes:
        if w.destination.lower() in ['', ' ', 'unopened', 'closed'] or w.start.lower() in ['', ' ', 'unopened', 'closed']:
            continue
        if w.status in ['Fresh', 'Unknown'] and (now.replace(tzinfo=pytz.utc) - w.date.replace(tzinfo=pytz.utc)).seconds / 60 / 60 > 12:
            g.add_edge(w.start, w.destination, style='dotted', color='red')
            continue
        g.add_edge(w.start, w.destination, style=get_edge_type(w.start, w.destination), color='black')
    g.layout()
    os.remove('/var/www/mysite/sitemngr/static/pictures/graph.png')
    g.draw('/var/www/mysite/sitemngr/static/pictures/graph.png')
    print 'Graphed', datetime.now().strftime('%m/%d/%Y %H:%M:%S')

def should_update():
    return True

def repeat():
    while 1:
        if should_update():
            graph()
            sleep(60 * 2)

def run():
    graph()
    # repeat()

def run_once():
    graph()
