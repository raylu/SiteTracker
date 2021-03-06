# Python
import re
import requests
from datetime import datetime
import pytz

# sitemngr
from .models import *
from . import appSettings

# ldap
from django_auth_ldap.backend import LDAPBackend
ldap_backend = LDAPBackend()

def get_time_difference_formatted(old, recent):
    """ Formats the difference between two datetime objects """
    diff = recent - old
    days = diff.days
    m, s = divmod(diff.seconds, 60)
    h, m = divmod(m, 60)
    return '{} days, {} hours, {} minutes, and {} seconds'.format(days, h, m, s)

def get_last_update():
    """ Returns a dict of info for the last time a user made an edit """
    # add the last of each type of data to the list
    site = Site.objects.last()
    sitesnap = SiteSnapshot.objects.last()
    wormhole = Wormhole.objects.last()
    wormholesnap = WormholeSnapshot.objects.last()
    # paste = PasteUpdated.objects.last()
    dates = []
    # only add dates belonging to actual objects (prevents trying to get the data of a None object)
    if site:
        dates.append(site.date)
    if sitesnap:
        dates.append(sitesnap.date)
    if wormhole:
        dates.append(wormhole.date)
    if wormholesnap:
        dates.append(wormholesnap.date)
    # if paste:
        # dates.append(paste.date)
    # get the most recent date
    date = None
    try:
        date = sorted(dates)[-1]
        print(date)
    except IndexError:
        # if nothing was added to the list, i.e. new database
        print('Last update parse IndexError')
        return {'time': None, 'user': None}
    except TypeError:
        # one of more of the fields was filled, and one or more was None
        print('Last update parse TypeError')
        return {'time': None, 'user': None}
    # return the appropriate not None information
    if site and site.date == date:
        return {'time': date, 'user': site.creator}
    if sitesnap and sitesnap.date == date:
        return {'time': date, 'user': sitesnap.snappedBy}
    if wormhole and wormhole.date == date:
        return {'time': date, 'user': wormhole.creator}
    if wormholesnap and wormholesnap.date == date:
        return {'time': date, 'user': wormholesnap.snappedBy}
    # if paste and paste.date == date:
        # return {'time': date, 'user': paste.user}
    return {'time': '-never-', 'user': '-no one-'}

def get_last_up_to_date():
    """ Return a dict of info for the last time the database was marked as up to date """
    if DatabaseUpToDate.objects.count() == 0:
        return {'time': '-never', 'user': '-no one-'}
    last = DatabaseUpToDate.objects.last()
    return {'time': last.date, 'user': last.user}

def ellapsed_timers():
    ret = {}
    now = datetime.now(pytz.utc)
    for wormhole in Wormhole.objects.filter(opened=True, closed=False):
        diff = (now - wormhole.date)
        days = diff.days
        m, s = divmod(diff.seconds, 60)
        h, m = divmod(m, 60)
        h += days * 24 if not days > 1 else 0
        passed = '{}:{}:{}'.format(h, m, s)
        ret[wormhole.id] = passed
    return ret

def p_get_all_data(line):
    """ Parses all information from a line from the discovery scanner """
    baseTypes = ['Cosmic Anomaly', 'Cosmic Signature']
    siteTypes = ['Data Site', 'Relic Site', 'Gas Site']
    anomTypes = ['Combat Site', 'Ore Site']
    wormholeTypes = ['Wormhole', 'Unstable Wormhole']
    data = {}
    # defaults to ensure that we don't get a KeyError trying to access information not pulled from the line
    data['scanid'] = ''
    data['issite'] = False
    data['isanom'] = False
    data['iswormhole'] = False
    data['name'] = ''
    data['type'] = ''
    for section in line.split('\t'):
        if section is None:
            continue
        section = section.replace('\r', '').replace('\n', '')
        if re.match(r'^[A-Z]{3}-\d{3}$', section):
            data['scanid'] = section[:3].upper()
            continue
        if section in siteTypes and not data['iswormhole']:
            data['issite'] = True
            data['type'] = section.split(' ')[0]
            continue
        if section in anomTypes:
            data['isanom'] = True
            data['type'] = section.split(' ')[0]
            continue
        if section in wormholeTypes:
            data['iswormhole'] = True
            data['issite'] = False
            data['type'] = section
            continue
        if '%' in section or 'AU' in section or re.match(r'^\d+ km$', section.strip()):
            continue
        if not section in baseTypes:
            data['name'] = section
    return data

class SpaceObject:
    """ Represents an object in space """
    def __init__(self, i, what, name):
        self.id = i
        self.what = what
        self.name = name
    def __repr__(self):
        return '<SpaceObject-{}-{}-{}>'.format(self.id, self.what, self.name)

def is_system_in_chain(system):
    """ Returns if the syetem is directly in the chain """
    return system in get_chain_systems()

def get_chain_systems():
    """ Returns all systems directly in the chain """
    chain_systems = [w.destination for w in Wormhole.objects.filter(opened=True, closed=False)]
    chain_systems.extend([w.start for w in Wormhole.objects.filter(opened=True, closed=False)])
    return chain_systems

def is_system_kspace(system):
    """ Returns if the system is in kspace """
    return not re.match(r'^J\d{6}$', system)

def is_system_wspace(system):
    """ Returns if the system is in wspace """
    return re.match(r'^J\d{6}$', system)

def get_tradehub_system_names():
    """ Returns the names of all of the tradehub systems """
    return ['Jita', 'Rens', 'Dodixie', 'Amarr', 'Hek']

def get_jumps_between(start, finish):
    """ Polls Dotlan to calculate jumps between two systems """
    if start == finish:
        return 0
    try:
        url = 'http://evemaps.dotlan.net/route/{}:{}'.format(start.replace(' ', '_'), finish.replace(' ', '_'))
        count = 0
        contents = requests.get(url).text
        for line in contents.split('\n'):
            if '<td align="right">' in line:
                count += 1
        return (count - 1) / 2
    except:
        return -1

def is_system(system):
    """ Returns True if the string is the name of a system """
    try:
        System.objects.get(name=system)
        return True
    except System.DoesNotExist:
        return False

def get_wormhole_class(system):
    """ Returns the class (1-6) of a wormhole by its system name """
    try:
        s = System.objects.get(name=system)
        if s.clazz:
            return s.clazz
    except System.DoesNotExist:
        pass
    url = 'http://www.ellatha.com/eve/WormholeSystemview.asp?key={}'.format(system.replace('J', ''))
    try:
        contents = requests.get(url).text.split('\n')
        for line in contents:
            if line.startswith('<td bgcolor="#F5F5F5">'):
                if re.match(r'^\d$', line.split('>')[1][0]):
                    clazz = line.split('>')[1][0]
                    try:
                        s = System.objects.get(name=system)
                        s.clazz = clazz
                        s.save()
                    except System.DoesNotExist:
                        pass
                    return clazz
    except:
        pass
    return 0

class Result:
    """ Object for use by the get_search_results method """
    def __init__(self, link, text):
        self.link = 'http://tracker.talkinlocal.org/' + link
        self.text = text
    def __repr__(self):
        return '<Result {}-{}>'.format(self.link, self.text)

def get_system_name(systemid):
    """ Returns the common name for the system from the Eve API's systemid representation """
    try:
        return System.objects.get(mapid=systemid).name
    except System.DoesNotExist:
        return 'null'

def get_system_ID(systemname):
    """ Returns the systemid for use in the Eve API corresponding to the systemname """
    try:
        return System.objects.get(name=systemname).id
    except System.DoesNotExist:
        return 'null'

def get_system_proper_name(systemname):
    """ Returns the proper in-game name of a system (proper capitalization) """
    try:
        return System.objects.get(name__iexact=systemname).name
    except:
        return systemname

class Contributor:
    """ Object for use by the stats page """
    def __init__(self, name, points):
        self.name = name
        self.points = points

def getBoolean(s):
    """ Returns True if the string represents a boolean equalling True """
    if type(s) == bool:
        return s
    return s.lower() in ['true', 't', '1', 'yes', 'on']

def get_display_name(eveigb, request):
    """ Returns the correct name of a user from their browser """
    if request is not None:
        if request.user is not None:
            if request.user.is_active and request.user.is_authenticated():
                return request.user.username
    if eveigb and eveigb.trusted:
        return eveigb.charname
    return 'someone'

def can_view(igb, request=None):
    """
        Returns True if the user can view that page by testing
            if they are using the EVE IGB (Trusted mode) and in the appropriate alliance
    """
    if get_display_name(igb, request) in appSettings.BLOCKED_USERS:
        return False
    if request is not None:
        if request.user is not None:
            if request.user.is_active:
                user = ldap_backend.populate_user(request.user.username)
                if user is None:
                    return False
                if not user.account_status == 'Internal':
                    return False
                return True
    return igb is not None and igb.is_igb and igb.trusted and igb.alliancename == appSettings.ALLIANCE_NAME

def can_view_wrong_alliance(igb):
    """
        Returns True if the user can view that page by testing
            if they are using the EVE IGB (Trusted mode), but does not check alliance
    """
    return igb is not None and igb.is_igb and igb.trusted and igb.alliancename != appSettings.ALLIANCE_NAME

def is_site(scanid):
    """ Returns True if the scanid represents a site object """
    return get_site(scanid) is not None

def get_site(scanid):
    """ Returns site with scan id (or None) """
    for site in Site.objects.all():
        if site.scanid.lower() == scanid.lower():
            return site
    return None

def is_wormhole(scanid):
    """ Returns True if the scanid represents a wormhole object """
    return get_wormhole(scanid) is not None

def get_wormhole(scanid):
    """ Returns wormhole with scanid (or None) """
    for wormhole in Wormhole.objects.all():
        if wormhole.scanid.lower() == scanid.lower():
            return wormhole
    return None

def get_settings(username):
    """ Returns the settings for a user """
    try:
        settings = Settings.objects.get(user=username)
    except Settings.DoesNotExist:
        settings = Settings(user=username, editsInNewTabs=True, storeMultiple=True)
        settings.save()
    return settings

def get_system_information(system):
    data = {
        'region': 'region',
        'constellation': 'constellation',
        'faction': 'faction',
        'jumps': [-1, -1],
        'npckills': [0, 0],
        'shipkills': [0, 0],
        'podkills': [0, 0],
        'pirates': 'pirates',
        'wormhole_effect': 'wormhole_effect',
        'connections': 'connections'
    }
    # website lines
    contents = [line.strip() for line in requests.get('http://evemaps.dotlan.net/system/' + system).text.split('\n') if line and not line == '']
    # recent kills
    kills = []
    for line in contents:
        if re.match(r'^<td align="right">\d+</td>$', line):
            kills.append(re.search(r'\d+', line).group(0))
        if len(kills) == 6:
            break
    data['shipkills'] = [kills[0], kills[1]]
    data['npckills'] = [kills[2], kills[3]]
    data['podkills'] = [kills[4], kills[5]]
    # faction
    for line in contents:
        if '<td colspan="3">' in line:
            data['faction'] = line.split('>')[1].split('<')[0]
            break
    # region
    for line in contents:
        if '/region/' in line:
            data['region'] = re.search(r'/region/\w+', line).group(0).split('/')[2].replace('_', ' ')
            break
    # constellation
    next = False
    for line in contents:
        if next:
            data['constellation'] = re.search(r'/universe/\w+', line).group(0).split('/')[2].replace('_', ' ')
            break
        if '<td><b>Constellation</b></td>' in line:
            next = True
    # pirates
    for line in contents:
        if '<td nowrap="nowrap" colspan="2">' in line:
            data['pirates'] = line.split('>')[1].split('<')[0]
    # jumps
    for line in contents:
        if '<td width="5%" align="right">' in line:
            if data['jumps'][0] == -1:
                data['jumps'][0] = line.split('>')[1].split('<')[0]
            else:
                data['jumps'][1] = line.split('>')[1].split('<')[0]
                break
    # wormhole_effect
    for line in contents:
        if '<h2>Wormhole System Effect:' in line:
            data['wormhole_effect'] = ''.join(s + ' ' for s in line.split(' ')[3:(len(line.split(' ')) - 4)])[:-1]
            break
    # wormhole statics
    systemObject = System.objects.get(name=system)
    s = ''
    if ',' in systemObject.static:
        for static in systemObject.static.split(','):
            s += static.replace(':', ' to ') + '\n'
        s = s[:-1]
    else:
        s = systemObject.static.replace(':', ' to ')
    data['connections'] = s
    return data

def snapshot(model, display_name):
    """
        Create and return SiteSnapshot/WormholeSnapshot
        Note: The returned snapshot is NOT SAVED!
    """
    if isinstance(model, Site):
        snap = SiteSnapshot(site=model, date=datetime.now(), user=model.creator, scanid=model.scanid, name=model.name,
            type=model.type, where=model.where, opened=model.opened, closed=model.closed, notes=model.notes, snappedBy=display_name)
        return snap
    elif isinstance(model, Wormhole):
        snap = WormholeSnapshot(wormhole=model, date=datetime.now(), user=model.creator, scanid=model.scanid,
            start=model.start, destination=model.destination, status=model.status,
            opened=model.opened, closed=model.closed, notes=model.notes, otherscanid=model.otherscanid, snappedBy=display_name)
        return snap
    return None

def do_edit_site(p, site, display_name):
    """ Edits a site """
    snap = snapshot(site, display_name)
    changedName = False
    changedScanid = False
    changedType = False
    changedWhere = False
    changedDate = False
    changedOpened = False
    changedClosed = False
    changedNotes = False
    p = p.copy()
    if 'name' in p and p['name']:
        if p['name'] != site.name:
            changedName = True
            site.name = p['name']
    if 'scanid' in p and p['scanid']:
        p['scanid'] = p['scanid'].upper()
        if p['scanid'] != site.scanid:
            changedScanid = True
            site.scanid = p['scanid'].upper()
    if 'type' in p and p['type']:
        if p['type'] != site.type:
            changedType = True
            site.type = p['type']
    if 'where' in p and p['where']:
        if get_system_proper_name(p['where']) != site.where:
            changedWhere = True
            site.where = get_system_proper_name(p['where'])
    if 'opened' in p and p['opened']:
        if getBoolean(p['opened']) != site.opened:
            changedOpened = True
            site.opened = getBoolean(p['opened'])
    else:
        if site.opened == True:
            site.opened = False
            changedOpened = True
    if 'closed' in p and p['closed']:
        if getBoolean(p['closed']) != site.closed:
            changedClosed = True
            site.closed = getBoolean(p['closed'])
    else:
        if site.closed == True:
            site.closed = False
            changedClosed = True 
    if 'notes' in p and p['notes']:
        if p['notes'] != site.notes:
            changedNotes = True
            site.notes = p['notes']
    if changedName or changedScanid or changedType or changedWhere or changedDate or changedOpened or changedClosed or changedNotes:
        site.save()
        snap.save()
        return snap
    return False

def do_edit_wormhole(p, wormhole, display_name):
    """ Edits a wormhole """
    snap = snapshot(wormhole, display_name)
    changedScanid = False
    changedStart = False
    changedDestination = False
    changedTime = False
    changedStatus = False
    changedOpened = False
    changedClosed = False
    changedNotes = False
    changedOtherScanid = False
    p = p.copy()
    if 'scanid' in p and p['scanid']:
        p['scanid'] = p['scanid'].upper()
        if p['scanid'] != wormhole.scanid:
            changedScanid = True
            wormhole.scanid = p['scanid'].upper()
    if 'start' in p and p['start']:
        if get_system_proper_name(p['start']) != wormhole.start:
            changedStart = True
            wormhole.start = get_system_proper_name(p['start'])
    if 'destination' in p and p['destination']:
        if get_system_proper_name(p['destination']) != wormhole.destination:
            changedDestination = True
            wormhole.destination = get_system_proper_name(p['destination'])
    if 'status' in p and p['status']:
        if p['status'] != wormhole.status:
            changedStatus = True
            wormhole.status = p['status']
    if 'opened' in p and p['opened']:
        if getBoolean(p['opened']) != wormhole.opened:
            changedOpened = True
            wormhole.opened = getBoolean(p['opened'])
    else:
        if wormhole.opened == True:
            wormhole.opened = False
            changedOpened = True
    if 'closed' in p and p['closed']:
        if getBoolean(p['closed']) != wormhole.closed:
            changedClosed = True
            wormhole.closed = getBoolean(p['closed'])
    else:
        if wormhole.closed == True:
            wormhole.closed = False
            changedClosed = True
    if 'notes' in p and p['notes']:
        if p['notes'] != wormhole.notes:
            changedNotes = True
            wormhole.notes = p['notes']
    if 'otherscanid' in p and p['otherscanid']:
        if p['otherscanid'] != wormhole.otherscanid:
            changedOtherScanid = True
            wormhole.otherscanid = p['otherscanid'].upper()
    if changedScanid or changedStart or changedDestination or changedTime or changedStatus or changedOpened or changedClosed or changedNotes or changedOtherScanid:
        wormhole.save()
        snap.save()
        return snap
    return False

class PasteData:
    """ Dynamically constructed class sent to /sitemngr/addsite and  /sitemngr/addwormhole from /sitemngr/paste  """
    def __init__(self, p_scanid='', p_system=str(appSettings.HOME_SYSTEM), p_name='', p_type='Anomoly', p_isSite=True, p_isWormhole=False):
        self.scanid = p_scanid
        self.system = p_system
        self.name = p_name
        self.type = p_type
        self.isSite = p_isSite
        self.iswormhole = p_isWormhole
    def __repr__(self):
        return '<PasteData-{}-{}>'.format(self.scanid, self.system)

class PasteMatch:
    """ Used by the after downtime scan page to match a scanid with its allowed matches """
    def __init__(self, scanid, name, p_type, allowed):
        self.scanid = scanid
        self.name = name
        self.p_type = p_type
        self.allowed = allowed
    def __repr__(self):
        return '<PasteMatch-{}-{}-{}-{}>'.format(self.scanid, self.name, self.p_type, self.allowed)
    def as_string(self):
        return '{}: {}'.format(self.scanid, self.name)

class KillReport:
    """ Dynamically constructed class sent to /sitemngr/checkkills """
    def __init__(self, system=appSettings.HOME_SYSTEM, systemid=appSettings.HOME_SYSTEM_ID, npc=0, ship=0, pod=0):
        self.system = system
        self.systemid = systemid
        self.npc = npc
        self.ship = ship
        self.pod = pod
    def __repr__(self):
        return '<KillReport-{}-{}-{}-{}-{}>'.format(self.system, self.systemid, self.npc, self.ship, self.pod)
