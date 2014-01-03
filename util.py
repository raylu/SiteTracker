# Python
import re
import urllib2

# sitemngr
from models import (Site, SiteChange,
                             Wormhole, WormholeChange,
                             PasteUpdated, Settings)
from . import settings as appSettings

# eve_db
from eve_db.models import MapSolarSystem

def get_time_difference_formatted(old, recent):
    """ Formats the difference between two datetime objects """
    diff = recent - old
    days = diff.days
    m, s = divmod(diff.seconds, 60)
    h, m = divmod(m, 60)
    return '%s days, %s hours, %s minutes, and %s seconds' % (days, h, m, s)

def get_last_update_time():
    """ Returns the time of the most recent database change """
    if not get_last_update():
        return '-never'
    return get_last_update().date

def get_last_update_user():
    """ Returns the user to make the most recent database change """
    last = get_last_update()
    if not last:
        return '-no one-'
    return last.creator if isinstance(last, (Site, Wormhole)) else last.user

def get_last_update():
    """ Returns the object that has the most recent date """
    # add the last of each type of data to the list
    site = Site.objects.last()
    s_change = SiteChange.objects.last()
    wormhole = Wormhole.objects.last()
    w_change = WormholeChange.objects.last()
    paste = PasteUpdated.objects.last()
    dates = []
    # only add dates belonging to actual objects (prevents trying to get the data of a None object)
    if site:
        dates.append(site.date)
    if s_change:
        dates.append(s_change.date)
    if wormhole:
        dates.append(wormhole.date)
    if w_change:
        dates.append(w_change.date)
    if paste:
        dates.append(paste.date)
    # get the most recent date
    date = None
    try:
        date = sorted(dates)[-1]
    except IndexError:
        # if nothing was added to the list, i.e. new database
        return None
    # get the object whose date was selected
    try:
        return Site.objects.get(date=date)
    except Site.DoesNotExist:
        try:
            return Wormhole.objects.get(date=date)
        except Wormhole.DoesNotExist:
            try:
                return SiteChange.objects.get(date=date)
            except SiteChange.DoesNotExist:
                try:
                    return WormholeChange.objects.get(date=date)
                except WormholeChange.DoesNotExist:
                    return PasteUpdated.objects.get(date=date)

def p_get_all_data(line):
    """ Parses all information from a line from the discovery scanner """
    siteTypes = ['Cosmic Signature', 'Data', 'Relic', 'Gas']
    anomTypes = ['Cosmic Anomaly', 'Combat Site', 'Ore Site']  # 'Gas Site' ?
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
        if re.match(r'^[a-zA-Z]{3}-\d{3}$', section):
            data['scanid'] = section[:3].upper().replace('\r', '').replace('\n', '')
            continue
        if section in siteTypes and not data['iswormhole']:
            data['issite'] = True
            data['type'] = section.replace('\r', '').replace('\n', '')
            continue
        if section in anomTypes:
            data['isanom'] = True
            data['type'] = section.replace('\r', '').replace('\n', '')
            continue
        if section in wormholeTypes:
            data['iswormhole'] = True
            data['issite'] = False
            data['type'] = section.replace('\r', '').replace('\n', '')
            continue
        if '%' in section or 'AU' in section:
            continue
        data['name'] = section.replace('\r', '').replace('\n', '')
    return data

class SpaceObject:
    """ Represents an object in space """
    def __init__(self, i, what, name):
        self.id = i
        self.what = what
        self.name = name
    def __unicode__(self):
        return unicode('%s: %s %s' % (self.id, self.what, self.name))

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
    try:
        url = 'http://evemaps.dotlan.net/route/%s:%s' % (start, finish)
        count = 0
        contents = urllib2.urlopen(url).read()
        for line in contents.split('\n'):
            if '<td align="right">' in line:
                count += 1
        return (count - 1) / 2
    except:
        return -1

def is_system(system):
    """ Returns True if the string is the name of a system """
    try:
        MapSolarSystem.objects.get(name=system)
        return True
    except MapSolarSystem.DoesNotExist:
        return False

def get_wormhole_class(system):
    """ Returns the class (1-6) of a wormhole by its system name """
    url = 'http://www.ellatha.com/eve/WormholeSystemview.asp?key={}'.format(system.replace('J', ''))
    contents = urllib2.urlopen(url).read().split('\n')
    for line in contents:
        if line.startswith('<td bgcolor="#F5F5F5">'):
            if re.match(r'^\d$', line.split('>')[1][0]):
                return line.split('>')[1][0]
    return 0

class Result:
    """ Object for use by the get_search_results method """
    def __init__(self, link, text):
        self.link = 'http://tracker.talkinlocal.org/sitemngr/' + link
        self.text = text
    def __unicode__(self):
        return unicode('<Result %s-%s>' % (self.link, self.text))

class Flag:
    def __init__(self, flags):
        self.open_only = 'o' in flags
        self.closed_only = 'c' in flags
        self.chain = 'f' in flags
        self.systems = 'm' in flags
        self.wormholes = 'w' in flags
        self.sites = 's' in flags
        self.universe = 'u' in flags
        self.all = flags == '_'
    def __unicode__(self):
        return 'Flag: Open=%s Closed=%s Chain=%s Universe=%s Systems=%s Wormholes=%s Sites=%s' % (self.open_only, self.closed_only, self.chain, self.universe, self.systems, self.wormholes, self.sites)

def get_system_name(systemid):
    """ Returns the common name for the system from the Eve API's systemid representation """
    try:
        return MapSolarSystem.objects.get(id=systemid).name
    except MapSolarSystem.DoesNotExist:
        return 'null'

def get_system_ID(systemname):
    """ Returns the systemid for use in the Eve API corresponding to the systemname """
    try:
        return MapSolarSystem.objects.get(name=systemname).id
    except MapSolarSystem.DoesNotExist:
        return 'null'

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
            if request.user.is_active and request.user.is_authenticated:
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
