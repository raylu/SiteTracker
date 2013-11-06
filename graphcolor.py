import re
from sitemngr.models import Wormhole, UpdateData
from eve_db.models import MapSolarSystem
from pygraphviz import *
import httplib2
from time import sleep
from datetime import datetime
import os
import shutil

cmap = {}
cmap['HS'] = 'gold'
cmap['LS'] = 'purple'
cmap['NS'] = 'brown'
cmap['1'] = 'blue'
cmap['2'] = 'green'
cmap['3'] = 'yellow'
cmap['4'] = 'orange'
cmap['5'] = 'red'
cmap['6'] = 'black'

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
		http = httplib2.Http()
		headers, body = http.request('http://www.ellatha.com/eve/WormholeSystemview.asp?key={0}'.format(system_name.replace('J', '')))
		level = body.split('<td bgcolor="#FFFFFF" width="20%"><b>Class:</b>&nbsp;</td>')[1].strip().split('</tr>')[0].split('>')[1][0]
		return cmap[level]
	except:
		pass
	return 'black'

def graph():
	g = AGraph(label='Overview')
	wormholes = Wormhole.objects.filter(opened=True, closed=False)
	nodes = []
	for w in wormholes:
		if not w.start in nodes:
			nodes.append(w.start)
		if not w.destination in nodes:
			nodes.append(w.destination)
	for n in nodes:
		g.add_node(n, color=get_color(n))
	for w in wormholes:
		g.add_edge(w.start, w.destination)
	g.layout()
	g.draw('graph.png')

def should_update():
	# u_list = UpdateData.objects.all()
	# if len(u_list) > 0:
		# for u in u_list:
			# u.delete()
		# return True
	# return False
	return True
	
def repeat():
	file = os.path.join(os.getcwd() + '/graph.png')
	destination = os.path.join(os.getcwd() + '/sitemngr/static/pictures/graph.png')
	while 1:
		if should_update():
			graph()
			sleep(5)
			shutil.move(file, destination)
			print 'Graphed and moved', datetime.now().strftime('%m/%d/%Y %H:%M:%S')
			sleep(60*5)
