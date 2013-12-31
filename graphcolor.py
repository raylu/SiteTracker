import re
from sitemngr.models import Wormhole
from eve_db.models import MapSolarSystem
from pygraphviz import *
import urllib2
from time import sleep
from datetime import datetime
import pytz
import os
from . import util

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
emap['Undecayed'] = 'bold'
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
    if util.is_system_wspace(system_name):
        return get_color_wh(system_name)
    try:
        system = MapSolarSystem.objects.get(name=system_name)
    except MapSolarSystem.DoesNotExist:
        return 'black'
    status = system.security_level
    if status > 0.45:
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
            g.add_node(n, color='red', fontcolor='red', shape='box')
            continue
        g.add_node(n, color=get_color(n), shape='ellipse')
    for w in wormholes:
        if w.destination.lower() in ['', ' ', 'unopened', 'closed'] or w.start.lower() in ['', ' ', 'unopened', 'closed']:
            continue
        if w.status in ['Fresh', 'Undecayed'] and (now.replace(tzinfo=pytz.utc) - w.date.replace(tzinfo=pytz.utc)).seconds / 60 / 60 > 20:
            w.status = 'Unknown'
            w.save()
            g.add_edge(w.start, w.destination, style='dotted', color='red', label=w.scanid)
        elif w.status == 'Unknown' and (now.replace(tzinfo=pytz.utc) - w.date.replace(tzinfo=pytz.utc)).seconds / 60 / 60 > 20:
            g.add_edge(w.start, w.destination, style='dotted', color='red', label=w.scanid)
        else:
            g.add_edge(w.start, w.destination, style=get_edge_type(w.start, w.destination), color='black', label=w.scanid)
    g.layout()
    try:
        os.remove('/var/www/mysite/sitemngr/static/pictures/graph.png')
    except OSError:
        pass
    g.draw('/var/www/mysite/sitemngr/static/pictures/graph.png')
    print 'Graphed', datetime.now().strftime('%m/%d/%Y %H:%M:%S')

def repeat():
    while 1:
        graph()
        sleep(60 * 2)

def run():
    graph()

def run_once():
    graph()
