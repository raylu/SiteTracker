# Python
from datetime import datetime
import re
import urllib2
from math import floor

# Django
from django.shortcuts import render, get_object_or_404
from django.contrib.auth.models import User
from django.contrib.auth import authenticate, login, logout

# sitemngr
from sitemngr.models import (Site, SiteChange,
                             Wormhole, WormholeChange,
                             PasteData, PasteUpdated,
                             KillReport, PasteMatch, Settings)
import settings as appSettings

# eve_db
from eve_db.models import MapSolarSystem

# eveigb
from eveigb import IGBHeaderParser

# evelink
import evelink
eve = evelink.eve.EVE()
eveapi = evelink.api.API()
evemap = evelink.map.Map(api=eveapi)

# scripts
useGraphing = True
try:
    import graphcolor
except ImportError:
    useGraphing = False

dirty = True

def set_dirty():
    global dirty
    dirty = True

def is_dirty():
    global dirty
    return dirty

def tidy():
    global dirty
    dirty = False
    if useGraphing:
        graphcolor.run_once()

# ==============================
#     Index
# ==============================

def index(request, note=None):
    """ Index page - lists all open sites """
    eveigb = IGBHeaderParser(request)
    if not can_view(eveigb, request):
        return no_access(request)
    sites = Site.objects.filter(closed=False)
    wormholes = Wormhole.objects.filter(closed=False)
    notices = ['All tables went on a diet.']
    # check if the wormhole objects and graph are out of sync
    if is_dirty():
        tidy()
        if useGraphing:
            notices.append('Graph updated!')
        else:
            notices.append('Graph would be updated, but it\'s not being used.')
    now = datetime.utcnow()
    # get the last updated time and player
    last_update_diff = None
    try:
        last_update_diff = get_time_difference_formatted(get_last_update_time().replace(tzinfo=None), now)
    except TypeError:
        last_update_diff = '-never-'
    last_update_user = get_last_update_user()
    return render(request, 'sitemngr/index.html', {'displayname': get_display_name(eveigb, request), 'sites': sites, 'wormholes': wormholes, 'status': 'open', 'notices': notices, 'newTab': get_settings(get_display_name(eveigb, request)).editsInNewTabs, 'backgroundimage': get_settings(get_display_name(eveigb, request)).userBackgroundImage, 'flag': note, 'now': now, 'last_update_diff': last_update_diff, 'last_update_user': last_update_user})

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

def view_all(request):
    """ Index page, but with the closed objects instead of the open """
    eveigb = IGBHeaderParser(request)
    if not can_view(eveigb, request):
        return no_access(request)
    sites = Site.objects.filter(closed=True)
    wormholes = Wormhole.objects.filter(closed=True)
    return render(request, 'sitemngr/index.html', {'displayname': get_display_name(eveigb, request), 'sites': sites, 'wormholes': wormholes, 'status': 'closed'})

def add(request):
    """
        Landing page for adding to the database - only used for clarification from
            the user after using the paste page
    """
    eveigb = IGBHeaderParser(request)
    if not can_view(eveigb, request):
        return no_access(request)
    scanid = ''
    if request.method == 'GET':
        g = request.GET
        if g.has_key('scanid') and g['scanid']:
            scanid = g['scanid']
    return render(request, 'sitemngr/add.html', {'displayname': get_display_name(eveigb, request), 'scanid': scanid})

# ==============================
#     Site
# ==============================

def view_site(request, siteid):
    """ Views all the data on a particular site, including a list of changes """
    eveigb = IGBHeaderParser(request)
    if not can_view(eveigb, request):
        return no_access(request)
    site = get_object_or_404(Site, pk=siteid)
    changes = site.getChanges()
    return render(request, 'sitemngr/viewsite.html', {'displayname': get_display_name(eveigb, request), 'isForm': False, 'site': site, 'changes': changes})

def edit_site(request, siteid):
    """ Edit site page for changing data """
    eveigb = IGBHeaderParser(request)
    if not can_view(eveigb, request):
        return no_access(request)
    site = get_object_or_404(Site, pk=siteid)
    if request.method == 'POST':
        p = request.POST
        now = datetime.now()
        changedName = False
        changedScanid = False
        changedType = False
        changedWhere = False
        changedDate = False
        changedOpened = False
        changedClosed = False
        changedNotes = False
        appendNotes = None
        if p.has_key('name') and p['name']:
            if p['name'] != site.name:
                changedName = True
                site.name = p['name']
        if p.has_key('scanid') and p['scanid']:
            if p['scanid'] != site.scanid:
                changedScanid = True
                appendNotes = 'Scanid: {0} >> {1}'.format(site.scanid, p['scanid'])
                site.scanid = p['scanid'].upper()
        if p.has_key('type') and p['type']:
            if p['type'] != site.type:
                changedType = True
                site.type = p['type']
        if p.has_key('where') and p['where']:
            if p['where'] != site.where:
                changedWhere = True
                site.where = p['where']
        if p.has_key('opened') and p['opened']:
            if getBoolean(p['opened']) != site.opened:
                changedOpened = True
                site.opened = getBoolean(p['opened'])
        else:
            if site.opened == True:
                site.opened = False
                changedOpened = True
        if p.has_key('closed') and p['closed']:
            if getBoolean(p['closed']) != site.closed:
                changedClosed = True
                site.closed = getBoolean(p['closed'])
        else:
            if site.closed == True:
                site.closed = False
                changedClosed = True 
        if p.has_key('notes') and p['notes']:
            if p['notes'] != site.notes:
                changedNotes = True
                site.notes = p['notes']
        # ensure that at least one piece of data was changed
        if changedName or changedScanid or changedType or changedWhere or changedDate or changedOpened or changedClosed or changedNotes:
            if appendNotes is not None:
                site.notes += appendNotes
            # save the changes made to the site object
            site.save()
            # construct a change for this edit
            change = SiteChange(site=site, date=now, user=get_display_name(eveigb, request), changedName=changedName, changedScanid=changedScanid,
                                changedType=changedType, changedWhere=changedWhere, changedDate=changedDate, changedOpened=changedOpened,
                                changedClosed=changedClosed, changedNotes=changedNotes)
            change.save()
        return index(request)
    return render(request, 'sitemngr/editsite.html', {'displayname': get_display_name(eveigb, request), 'isForm': True, 'site': site, 'finish_msg': 'Store changes back into the database:'})

def add_site(request):
    """ Add a site to the databse """
    eveigb = IGBHeaderParser(request)
    if not can_view(eveigb, request):
        return no_access(request)
    g_scanid = ''
    g_system = ''
    g_type = ''
    g_name = ''
    now = datetime.now()
    if request.method == 'POST':
        p = request.POST
        s_name = 'null'
        s_scanid = 'null'
        s_type = 'null'
        s_where = 'null'
        s_opened = False
        s_closed = False
        s_notes = ''
        if p.has_key('name') and p['name']:
            s_name = p['name']
        if p.has_key('scanid') and p['scanid']:
            s_scanid = p['scanid'].upper()
        if p.has_key('type') and p['type']:
            s_type = p['type']
        if p.has_key('where') and p['where']:
            s_where = p['where']
        if p.has_key('opened') and p['opened']:
            s_opened = getBoolean(p['opened'])
        if p.has_key('closed') and p['closed']:
            s_closed = getBoolean(p['closed'])
        if p.has_key('notes') and p['notes']:
            s_notes = p['notes']
        site = Site(name=s_name, scanid=s_scanid, type=s_type, where=s_where, creator=get_display_name(eveigb, request), date=now, opened=s_opened, closed=s_closed, notes=s_notes)
        site.save()
        # return the user to the appropriate page, depending on their user settings
        if get_settings(eveigb.charname).storeMultiple:
            return render(request, 'sitemngr/addsite.html', {'displayname': get_display_name(eveigb, request), 'isForm': True,
                 'message': 'Successfully stored the data into the database.', 'finish_msg': 'Store new site into the database:', 'timenow': now.strftime('%m/%d @ %H:%M')})
        else:
            return index(request)
    # fill in passed information from the paste page
    elif request.method == 'GET':
        g = request.GET
        if g.has_key('scanid') and g['scanid']:
            g_scanid = g['scanid']
        if g.has_key('system') and g['system']:
            g_system = g['system']
        if g.has_key('type') and g['type']:
            g_type = g['type']
        if g.has_key('name') and g['name']:
            g_name = g['name']
    return render(request, 'sitemngr/addsite.html', {'request': request, 'displayname': get_display_name(eveigb, request),
             'isForm': True, 'finish_msg': 'Store new site into the database:', 'g_scanid': g_scanid, 'g_system': g_system, 'g_type': g_type, 'g_name': g_name, 'timenow': now})

# ==============================
#     Wormhole
# ==============================

def view_wormhole(request, wormholeid):
    """ Views all the data on a particular wormhole, including a list of changes """
    eveigb = IGBHeaderParser(request)
    if not can_view(eveigb, request):
        return no_access(request)
    wormhole = get_object_or_404(Wormhole, pk=wormholeid)
    changes = wormhole.getChanges()
    return render(request, 'sitemngr/viewwormhole.html', {'displayname': get_display_name(eveigb, request), 'isForm': False, 'wormhole': wormhole, 'changes': changes})

def edit_wormhole(request, wormholeid):
    """ Edit wormhole page for changing data """
    eveigb = IGBHeaderParser(request)
    if not can_view(eveigb, request):
        return no_access(request)
    wormhole = get_object_or_404(Wormhole, pk=wormholeid)
    if request.method == 'POST':
        p = request.POST
        now = datetime.now()
        changedScanid = False
        changedStart = False
        changedDestination = False
        changedTime = False
        changedStatus = False
        changedOpened = False
        changedClosed = False
        changedNotes = False
        appendNotes = None
        if p.has_key('scanid') and p['scanid']:
            if p['scanid'] != wormhole.scanid:
                changedScanid = True
                appendNotes = ' Scanid: {0} >> {1}'.format(wormhole.scanid, p['scanid'])
                wormhole.scanid = p['scanid'].upper()
        if p.has_key('start') and p['start']:
            if p['start'] != wormhole.start:
                changedStart = True
                wormhole.start = p['start']
        if p.has_key('destination') and p['destination']:
            if p['destination'] != wormhole.destination:
                changedDestination = True
                wormhole.destination = p['destination']
        if p.has_key('time') and p['time']:
            if p['time'] != wormhole.time:
                changedTime = True
                wormhole.time = p['time']
        if p.has_key('status') and p['status']:
            if p['status'] != wormhole.status:
                changedStatus = True
                wormhole.status = p['status']
        if p.has_key('opened') and p['opened']:
            if getBoolean(p['opened']) != wormhole.opened:
                changedOpened = True
                wormhole.opened = getBoolean(p['opened'])
        else:
            if wormhole.opened == True:
                wormhole.opened = False
                changedOpened = True
        if p.has_key('closed') and p['closed']:
            if getBoolean(p['closed']) != wormhole.closed:
                changedClosed = True
                wormhole.closed = getBoolean(p['closed'])
        else:
            if wormhole.closed == True:
                wormhole.closed = False
                changedClosed = True
        if p.has_key('notes') and p['notes']:
            if getBoolean(p['notes']) != wormhole.notes:
                changedNotes = True
                wormhole.notes = p['notes']
        # ensure that at least one piece of data was changed
        if changedScanid or changedStart or changedDestination or changedTime or changedStatus or changedOpened or changedClosed or changedNotes:
            if appendNotes is not None:
                wormhole.notes += appendNotes
            # save the changes made to the wormhole object
            wormhole.save()
            # construct a change for this edit
            change = WormholeChange(wormhole=wormhole, user=get_display_name(eveigb, request), date=now, changedScanid=changedScanid, changedType=False, changedStart=changedStart, changedDestination=changedDestination, changedTime=changedTime, changedStatus=changedStatus, changedOpened=changedOpened, changedClosed=changedClosed, changedNotes=changedNotes)
            change.save()
            # make the new view of the index page update the graph
            set_dirty()
        return index(request)
    return render(request, 'sitemngr/editwormhole.html', {'displayname': get_display_name(eveigb, request), 'isForm': True,
          'wormhole': wormhole, 'finish_msg': 'Store changes back into the database'})

def add_wormhole(request):
    """ Add a wormhole to the databse """
    eveigb = IGBHeaderParser(request)
    if not can_view(eveigb, request):
        return no_access(request)
    g_scanid = ''
    g_start = ''
    g_end = ''
    g_name = ''
    now = datetime.now()
    if request.method == 'POST':
        p = request.POST
        s_scanid = 'null'
        s_start = 'null'
        s_destination = 'null'
        s_time = now
        s_status = 'Fresh'
        s_opened = False
        s_closed = False
        s_notes = ''
        if p.has_key('scanid') and p['scanid']:
            s_scanid = p['scanid'].upper()
        if p.has_key('start') and p['start']:
            s_start = p['start']
        if p.has_key('destination') and p['destination']:
            s_destination = p['destination']
        if p.has_key('time') and p['time']:
            s_time = p['time']
        if p.has_key('status') and p['status']:
            s_status = p['status']
        if p.has_key('opened') and p['opened']:
            s_opened = getBoolean(p['opened'])
        if p.has_key('closed') and p['closed']:
            s_closed = getBoolean(p['closed'])
        if p.has_key('notes') and p['notes']:
            s_notes = p['notes']
        wormhole = Wormhole(creator=get_display_name(eveigb, request), date=now, scanid=s_scanid, type='null', start=s_start, destination=s_destination,
                            time=s_time, status=s_status, opened=s_opened, closed=s_closed, notes=s_notes)
        wormhole.save()
        # make the new view of the index page update the graph
        set_dirty()
        # return the user to the appropriate page, depending on their user settings
        if get_settings(eveigb.charname).storeMultiple:
            return render(request, 'sitemngr/addwormhole.html', {'request': request, 'displayname': get_display_name(eveigb, request),
                    'isForm': True, 'message': 'Successfully stored the data into the database.', 'finish_msg': 'Store new site into database:', 'timenow': now.strftime('%m/%d @ %H:%M')})
        else:
            return index(request)
    # fill in passed information from the paste page
    elif request.method == 'GET':
        g = request.GET
        if g.has_key('scanid') and g['scanid']:
            g_scanid = g['scanid']
        if g.has_key('start') and g['start']:
            g_start = g['start']
        if g.has_key('end') and g['end']:
            g_end = g['end']
        if g.has_key('name') and g['name']:
            g_name = g['name']
    return render(request, 'sitemngr/addwormhole.html', {'request': request, 'displayname': get_display_name(eveigb, request),
                 'isForm': True, 'finish_msg': 'Store new wormhole into the database:', 'g_scanid': g_scanid, 'g_start': g_start, 'g_end': g_end, 'g_name': g_name, 'timenow': now.strftime('%m/%d @ %H:%M')})

# ==============================
#     Pastes
# ==============================

def p_get_all_data(line):
    """ Parses all information from a line from the discovery scanner """
    siteTypes = ['Cosmic Signature', 'Data Site', 'Relic Site']
    anomTypes = ['Combat Site', 'Ore Site']  # 'Gas Site' ?
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
        if section in siteTypes:
            data['issite'] = True
            data['type'] = section.replace('\r', '').replace('\n', '')
            continue
        if section in anomTypes:
            data['isanom'] = True
            data['type'] = section.replace('\r', '').replace('\n', '')
            continue
        if section in wormholeTypes:
            data['iswormhole'] = True
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

def paste(request):
    """
        Allow players to paste data from their system scanner into a
        textarea and submit for automatic review.
    """
    eveigb = IGBHeaderParser(request)
    if not can_view(eveigb, request):
        return no_access(request)
    now = datetime.now()
    if request.method == 'POST':
        post = request.POST
        if post.has_key('downtime') and post['downtime']:
            # After paste and checking after downtime checkbox - prepare data for user to make changes after downtime
            PasteUpdated(user=get_display_name(eveigb, request), date=datetime.now()).save()
            sites = []
            wormholes = []
            newids = []
            new_anoms = []
            new_sites = []
            new_wormholes = []
            names = {}
            paste = post['pastedata']
            system = post['system']
            for line in paste.split('\n'):
                data = p_get_all_data(line)
                if data['issite']:
                    new_sites.append(data['scanid'])
                    names[data['scanid']] = data['name']
                elif data['isanom']:
                    new_anoms.append(data['scanid'])
                    names[data['scanid']] = data['name']
                else:
                    new_wormholes.append(data['scanid'])
            paste_data = []
            allSites = Site.objects.filter(where=system, closed=False)
            for site in allSites:
                sites.append(site)
                exact_matches = []
                for i, n in names.iteritems():
                    if n == site.name:
                        exact_matches.append(i)
                if site.isAnom():
                    paste_data.append(PasteMatch(scanid=site.scanid, name=site.name, p_type='anom', allowed=[a + ': ' + names[a] for a in new_anoms] if len(exact_matches) == 0 else [e + ':' + names[e] for e in exact_matches]))
                else:
                    paste_data.append(PasteMatch(scanid=site.scanid, name=site.name, p_type='site', allowed=[s + ': ' + names[s] for s in new_sites] if len(exact_matches) == 0 else [e + ':' + names[e] for e in exact_matches]))
            allWormholes = Wormhole.objects.filter(start=system, closed=False)
            for wormhole in allWormholes:
                wormholes.append(wormhole)
                paste_data.append(PasteMatch(scanid=wormhole.scanid, name='%s > %s' % (wormhole.start, wormhole.destination), p_type='wormhole', allowed=new_wormholes))
            for s in new_sites:
                newids.append(SpaceObject(s, 'Signature', names[s]))
            for a in new_anoms:
                newids.append(SpaceObject(a, 'Anomaly', names[s]))
            for w in new_wormholes:
                newids.append(SpaceObject(w, 'Wormhole', ''))
            return render(request, 'sitemngr/pastescandowntime.html', {'system': system, 'pastedata': paste_data, 'sites': sites, 'wormholes': wormholes, 'newids': newids,
                           'displayname': get_display_name(eveigb, request), 'newTab': get_settings(get_display_name(eveigb, request)).editsInNewTabs, 'backgroundimage': get_settings(get_display_name(eveigb, request)).userBackgroundImage})
        elif post.has_key('afterdowntime') and post['afterdowntime']:
            # After downtime paste page after submitting database changes
            PasteUpdated(user=get_display_name(eveigb, request), date=datetime.now()).save()
            for k, v in post.iteritems():
                if ' ' in k:
                    k = k.split(' ')[0]
                if ':' in v:
                    v = v.split(':')[0]
                if k == 'csrfmiddlewaretoken' or k == 'afterdowntime':
                    continue
                if v == '-IGNORE-':
                    continue
                if is_site(k):
                    site = get_site(k)
                    if v == '-CLOSE-':
                        site.closed = True
                        site.save()
                        change = SiteChange(site=site, date=now, user=eveigb.charname, changedName=False, changedScanid=False,
                                    changedType=False, changedWhere=False, changedDate=False, changedOpened=False,
                                    changedClosed=True, changedNotes=False)
                        change.save()
                    else:
                        site.notes += ' Scanid: {0} >> {1}'.format(site.scanid, v)
                        site.scanid = v
                        site.save()
                        change = SiteChange(site=site, date=now, user=eveigb.charname, changedName=False, changedScanid=True,
                                    changedType=False, changedWhere=False, changedDate=False, changedOpened=False,
                                    changedClosed=False, changedNotes=False)
                        change.save()
                else:
                    wormhole = get_wormhole(k)
                    if v == '-CLOSE-':
                        wormhole.closed = True
                        wormhole.save()
                        change = WormholeChange(wormhole=wormhole, user=eveigb.charname, date=now, changedScanid=False, changedType=False,
                                     changedStart=False, changedDestination=False, changedTime=False, changedStatus=False,
                                     changedOpened=False, changedClosed=True, changedNotes=False)
                        change.save()
                    else:
                        wormhole.notes += 'Scanid: {0} >> {1}'.format(wormhole.scanid, v)
                        wormhole.scanid = v
                        wormhole.save()
                        change = WormholeChange(wormhole=wormhole, user=eveigb.charname, date=now, changedScanid=True, changedType=False,
                                     changedStart=False, changedDestination=False, changedTime=False, changedStatus=False,
                                     changedOpened=False, changedClosed=False, changedNotes=False)
                        change.save()
            set_dirty()
            return index(request)
        else:
            # Parse data to return to normal paste page
            PasteUpdated(user=get_display_name(eveigb, request), date=datetime.now()).save()
            present = []
            findnew = []
            notfound = []
            if 'pastedata' in post and post['pastedata'] and 'system' in post and post['system']:
                paste = post['pastedata']
                system = post['system']
                notfound.extend(Site.objects.filter(where=system, closed=False))
                notfound.extend(Wormhole.objects.filter(start=system, closed=False))
                for line in paste.split('\n'):
                    found = False
                    newP = PasteData(p_system=system)
                    data = p_get_all_data(line)
                    newP.isSite = True if data['issite'] else False
                    newP.isWormhole = True if data['iswormhole'] else False
                    newP.scanid = data['scanid']
                    newP.type = data['type']
                    newP.name = data['name']
                    if is_site(newP.scanid):
                        site = get_site(newP.scanid)
                        if site.where == system:
                            # Should not have to call this
                            if site in notfound:
                                notfound.remove(site)
                            found = True
                            present.append(site)
                    elif is_wormhole(newP.scanid):
                        wormhole = get_wormhole(newP.scanid)
                        if wormhole.start == system:
                            # Should not have to call this
                            if wormhole in notfound:
                                notfound.remove(wormhole)
                            found = True
                            present.append(wormhole)
                    if not found:
                        findnew.append(newP)
                return render(request, 'sitemngr/pastescan.html', {'displayname': get_display_name(eveigb, request), 'raw': post['pastedata'],
                               'present': present, 'notfound': notfound, 'findnew': findnew, 'timenow': now, 'system': system, 'newTab': get_settings(get_display_name(eveigb, request)).editsInNewTabs, 'backgroundimage': get_settings(get_display_name(eveigb, request)).userBackgroundImage})
    # Base request - show the base pastescan page
    return render(request, 'sitemngr/pastescan.html', {'displayname': get_display_name(eveigb, request), 'timenow': now, 'newTab': get_settings(get_display_name(eveigb, request)).editsInNewTabs, 'backgroundimage': get_settings(get_display_name(eveigb, request)).userBackgroundImage})


# ==============================
#     Systems
# ==============================

def system_landing(request):
    """ Return a list of a systems with active sites """
    eveigb = IGBHeaderParser(request)
    if not can_view(eveigb, request):
        return no_access(request)
    now = datetime.now()
    systems = []
    for site in Site.objects.filter(closed=False):
        if not site.where in systems:
            systems.append(site.where)
    for wormhole in Wormhole.objects.filter(closed=False):
        if not wormhole.start in systems:
                systems.append(wormhole.start)
        if not wormhole.destination in systems:
            systems.append(wormhole.destination)
    return render(request, 'sitemngr/systemlanding.html', {'displayname': get_display_name(eveigb, request), 'systems': systems, 'timenow': now})

def system(request, systemid):
    """
        Show all wormholes into and out of this system.
        Also show all closed wormholes in this system in the last 10 (configurable) days.
    """
    eveigb = IGBHeaderParser(request)
    if not can_view(eveigb, request):
        return no_access(request)
    opensites = Site.objects.filter(where=systemid, closed=False, opened=True)
    unopenedsites = Site.objects.filter(where=systemid, closed=False, opened=False)
    openwormholes = []
    openwormholes.extend(Wormhole.objects.filter(start=systemid, closed=False, opened=True))
    for w in Wormhole.objects.filter(destination=systemid, closed=False, opened=True):
        if not w in openwormholes:
            openwormholes.append(w)
    closedwormholes = Wormhole.objects.filter(start=systemid, closed=True)
    clazz = 0
    security = None
    is_kspace = None
    # if the system is in wormhole space, it has a class
    if re.match(r'J\d{6}', systemid):
        get_wormhole_class(systemid)
    # otherwise, it has a security level
    else:
        try:
            security = floor(MapSolarSystem.objects.get(name=systemid).security_level * 10) / 10
            is_kspace = True
        except MapSolarSystem.DoesNotExist:
                pass
    is_in_chain = is_system_in_chain(systemid)
    closest_chain = None
    closest_jumps = 5000
    # determine closest chain system to this
    if is_kspace and is_system(systemid):
        for chain in get_chain_systems():
            if not is_system(chain):
                continue
            if not is_system_kspace(chain):
                continue
            jumps = get_jumps_between(chain, systemid)
            if jumps < closest_jumps:
                closest_jumps = jumps
                closest_chain = chain
    return render(request, 'sitemngr/system.html', {'displayname': get_display_name(eveigb, request), 'system': systemid, 'openwormholes': openwormholes, 'closedwormholes': closedwormholes,
                            'class': clazz, 'security': security, 'kspace': is_kspace, 'opensites': opensites, 'unopenedsites': unopenedsites,
                            'is_in_chain': is_in_chain, 'closest_chain': closest_chain, 'closest_jumps': closest_jumps})

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

def get_tradehub_jumps(request, system):
    """ Shows the number of jumps from each tradehub system """
    jumps = []
    for hub in get_tradehub_system_names():
        jumps.append([hub, get_jumps_between(system, hub)])
    return render(request, 'sitemngr/tradehubjumps.html', dict((x.lower(), y) for x, y in jumps))

def get_tradehub_system_names():
    """ Returns the names of all of the tradehub systems """
    return ['Jita', 'Rens', 'Dodixie', 'Amarr', 'Hek']

def get_jumps_between(start, finish):
    """ Polls Dotlan to calculate jumps between two systems """
    url = 'http://evemaps.dotlan.net/route/%s:%s' % (start, finish)
    count = 0
    contents = urllib2.urlopen(url).read()
    for line in contents.split('\n'):
        if '<td align="right">' in line:
            count += 1
    return (count - 1) / 2

# ==============================
#     Reference lookup
# ==============================

def lookup(request, scanid):
    """ Lookup page for finding sites and wormholes by their scanid """
    eveigb = IGBHeaderParser(request)
    if not can_view(eveigb, request):
        return no_access(request)
    system = None
    if request.method == 'GET':
        g = request.GET
        if g.has_key('system') and g['system']:
            system = g['system']
    for site in Site.objects.all():
        if site.scanid == scanid:
            if system is not None:
                if site.where == system:
                    return view_site(request, site.id)
            else:
                return view_site(request, site.id)
    for wormhole in Wormhole.objects.all():
        if wormhole.scanid == scanid:
            if system is not None:
                if wormhole.start == system:
                    return view_wormhole(request, wormhole.id)
            else:
                return view_wormhole(request, wormhole.id)
    return render(request, 'sitemngr/lookup.html')

def mastertable(request):
    """ Master spreadsheet-link page for browsing """
    eveigb = IGBHeaderParser(request)
    if not can_view(eveigb, request):
        return no_access(request)
    sites = Site.objects.all()
    wormholes = Wormhole.objects.all()
    return render(request, 'sitemngr/mastertable.html', {'displayname': get_display_name(eveigb, request), 'sites': sites, 'wormholes': wormholes})


# ==============================
#     Data
# ==============================

def changelog(request):
    """ Site changelog """
    eveigb = IGBHeaderParser(request)
    return render(request, 'sitemngr/changelog.html', {'displayname': get_display_name(eveigb, request)})

def igb_test(request):
    """ Show all data that the in-game browser can send to a Trusted Site """
    eveigb = IGBHeaderParser(request)
    return render(request, 'sitemngr/igbtest.html', {'displayname': get_display_name(eveigb, request)})

def recent_scan_edits(request):
    """ Returns a readout of all recent scanid changes """
    eveigb = IGBHeaderParser(request)
    if not can_view(eveigb, request):
        return no_access(request)
    sites = []
    wormholes = []
    count = 0
    for s in SiteChange.objects.filter(changedScanid=True).order_by('-id'):
        sites.append(s.site)
        count += 1
        if count == int(appSettings.RECENT_EDITS_LIMIT) + 1:
            break
    count = 0
    for w in WormholeChange.objects.filter(changedScanid=True).order_by('-id'):
        wormholes.append(w.wormhole)
        count += 1
        if count == int(appSettings.RECENT_EDITS_LIMIT) + 1:
            break
    return render(request, 'sitemngr/recentscanedits.html', {'displayname': get_display_name(eveigb, request), 'sites': sites, 'wormholes': wormholes})

# ==============================
#     Output
# ==============================

def output(request):
    """ Output current data for the channel MotD """
    eveigb = IGBHeaderParser(request)
    if not can_view(eveigb, request):
        return no_access(request)
    wormholes = Wormhole.objects.filter(closed=False, start=appSettings.HOME_SYSTEM)
    motd = str(appSettings.HOME_SYSTEM) + ' Intel Channel\n\nWormholes:\n'
    for w in wormholes:
        motd += w.printOut() + '\n'
    motd += '\nSignatures:\n'
    for site in Site.objects.filter(closed=False, where=str(appSettings.HOME_SYSTEM)):
        motd += site.printOut() + '\n'
    return render(request, 'sitemngr/output.html', {'displayname': get_display_name(eveigb, request), 'motd': motd})

def stats(request):
    """ Returns usage statistics """
    eveigb = IGBHeaderParser(request)
    if not can_view(eveigb, request):
        return no_access(request)
    numSites = len(Site.objects.all())
    numWormholes = len(Wormhole.objects.all())
    numEdits = len(SiteChange.objects.all()) + len(WormholeChange.objects.all())
    numPastes = len(PasteUpdated.objects.all())
    con = {}
    for site_change in Site.objects.all():
        if site_change.creator in con:
            con[site_change.creator] += 1
        else:
            con[site_change.creator] = 1
    for wormhole_change in Wormhole.objects.all():
        if wormhole_change.creator in con:
            con[wormhole_change.creator] += 1
        else:
            con[wormhole_change.creator] = 1
    for site_change in SiteChange.objects.all():
        if site_change.user in con:
            con[site_change.user] += 1
        else:
            con[site_change.user] = 1
    for wormhole_change in WormholeChange.objects.all():
        if wormhole_change.user in con:
            con[wormhole_change.user] += 1
        else:
            con[wormhole_change.user] = 1
    for paste in PasteUpdated.objects.all():
        if paste.user in con:
            con[paste.user] += 1
        else:
            con[paste.user] = 1
    numContributors = len(con)
    conList = []
    con = sorted(con.items(), key=lambda kv: kv[1])
    for name, count in con:
        conList.append(Contributor(name, count))
    return render(request, 'sitemngr/stats.html', {'displayname': get_display_name(eveigb, request), 'numSites': numSites,
               'numWormholes': numWormholes, 'numPastes': numPastes, 'numEdits': numEdits, 'numContributors': numContributors, 'allContributors': conList})

def check_kills(request):
    """ Returns a readout of all ship and pod kills in and system with open objects """
    eveigb = IGBHeaderParser(request)
    if not can_view(eveigb, request):
        return no_access(request)
    reports = []
    systems = []
    for wormhole in Wormhole.objects.filter(closed=False):
        if wormhole.start not in systems:
            systems.append(wormhole.start)
        if wormhole.destination not in systems:
            systems.append(wormhole.destination)
    if len(systems) > 0:
        retSys = []
        for system in systems:
            retSys.append(get_system_ID(system))
        kills = evemap.kills_by_system()[0]
        for k in kills.iteritems():
            if k[0] in retSys:
                r = KillReport(system=get_system_name(k[0]), systemid=k[0], npc=k[1]['faction'], ship=k[1]['ship'], pod=k[1]['pod'])
                reports.append(r)
    return render(request, 'sitemngr/checkkills.html', {'displayname': get_display_name(eveigb, request), 'systems': systems, 'reports': reports})

def view_help(request):
    """ Help/instructions page """
    eveigb = IGBHeaderParser(request)
    return render(request, 'sitemngr/help.html', {'displayname': get_display_name(eveigb, request), 'able': can_view(eveigb, request)})

def overlay(request):
    """ Return a wealth of quickly-viewed information to be presented to on the idnex page """
    eveigb = IGBHeaderParser(request)
    if not can_view(eveigb, request):
        return no_access(request)
    data = ''
    # if the c2 static is open
    c2_open = False
    # list of highsec systems in the chain
    hs = []
    # closest chain system to jita
    jita_closest = None
    least = 5000
    # if the user is in-game, then get their current position
    current_system = eveigb.solarsystemname
    is_in_kspace = current_system and not re.match(r'^J\d{6}$', current_system)
    is_in_chain_system = False
    chain_systems = [w.destination for w in Wormhole.objects.filter(opened=True, closed=False)]
    chain_systems.extend(w.start for w in Wormhole.objects.filter(opened=True, closed=False))
    # if the user is in-game, then determine if they are in a chain system
    if current_system:
        if current_system in chain_systems:
            is_in_chain_system = True
    closest_in = None
    closest_jumps = 5000
    # if the user is in-game and not in a chain system, then determine the closest chain system
    if not is_in_chain_system:
        for system in chain_systems:
            if not re.match(r'^J\d{6}$', system):
                jumps = get_jumps_between(system, current_system)
                if jumps < closest_jumps:
                    closest_in = system
                    closest_jumps = jumps
    # look for an open c2 connection, and all highsec systems in the chain
    for wormhole in Wormhole.objects.filter(opened=True, closed=False):
        if not wormhole.destination.lower() in ['', ' ', 'closed', 'unopened', 'unknown']:
            if re.match(r'^J\d{6}$', wormhole.destination):
                if wormhole.start == appSettings.HOME_SYSTEM:
                    if not wormhole.destination.lower() in ['', ' ', 'closed', 'unopened', 'unknown']:
                        if re.match(r'^J\d{6}$', wormhole.destination):
                            if get_wormhole_class(wormhole.destination) == '2':
                                # we know that we have a connection to a C2
                                c2_open = True
                continue
            if not is_system(wormhole.destination):
                continue
            # determine if this system is the closest to Jita
            jumps = get_jumps_between('Jita', wormhole.destination)
            if int(jumps) < least:
                least = int(jumps)
                jita_closest = wormhole.destination
            # ensure that the system is actually in Eve, and not a user typo
            try:
                obj = MapSolarSystem.objects.get(name=wormhole.destination)
                status = obj.security_level
                if status > 0.5:
                    hs.append(wormhole.destination)
            except MapSolarSystem.DoesNotExist:
                continue
    # kills in the home system
    kills_npc = kills_ship = kills_pod = 0
    kills = evemap.kills_by_system()[0]
    for k in kills.iteritems():
        if str(k[0]) == appSettings.HOME_SYSTEM_ID:
            kills_npc = k[1]['faction']
            kills_ship = k[1]['ship']
            kills_pod = k[1]['pod']
    return render(request, 'sitemngr/overlay.html', {'displayname': get_display_name(eveigb, request), 'current_system': current_system, 'is_in_kspace': is_in_kspace, 'is_in_chain_system': is_in_chain_system,
                     'c2_open': c2_open, 'hs': hs, 'jita_closest': jita_closest, 'closest_in': closest_in, 'closest_jumps': closest_jumps,
                     'kills_npc': kills_npc, 'kills_ship': kills_ship, 'kills_pod': kills_pod, 'data': data})

def is_system(system):
    """ Returns True if the string is the name of a system """
    try:
        MapSolarSystem.objects.get(name=system)
        return True
    except MapSolarSystem.DoesNotExist:
        return False

def get_wormhole_class(system):
    """ Returns the class (1-6) of a wormhole by its system name """
    try:
        url = 'http://www.ellatha.com/eve/WormholeSystemview.asp?key={}'.format(system.replace('J', ''))
        contents = urllib2.urlopen(url).read().split('\n')
        for line in contents:
            if line.startswith('<td bgcolor="#F5F5F5">'):
                if re.match(r'^\d$', line.split('>')[1][0]):
                    return line.split('>')[1][0]
    except:
        pass
    return 0

# ==============================
#     Accounts
# ==============================

def login_page(request, note=None):
    """ A standard User login page """
    if request.method == 'POST':
        p = request.POST
        if p['username'] and p['password']:
            user = authenticate(username=p['username'], password=p['password'])
            if user is not None:
                if user.is_active:
                    login(request, user)
                    return index(request, 'Successfully logged in')
                else:
                    return render(request, 'sitemngr/login.html', {'note': 'This account is disabled'})
            else:
                return render(request, 'sitemngr/login.html', {'note': 'An error occurred when logging in - check your username and password'})
        else:
            return index(request, 'You must enter both a username and a password.')
    else:
        note = 'Nope'
    return render(request, 'sitemngr/login.html', {'note': note, 'displayname': get_display_name(None, request)})

def logout_page(request):
    """ If the user is logged into an account, they are logged off """
    logout(request)
    return index(request, 'You have been logged out.')

def create_account(request):
    """
        Create an account on the server
        Must be done from the in-game browser
    """
    if request.method == 'POST':
        eveigb = IGBHeaderParser(request)
        if not can_view(eveigb):
            return no_access(request)
        try:
            if User.objects.get(username__exact=eveigb.charname):
                return index(request, 'You already have an account on this server.')
        except User.DoesNotExist:
            pass
        p = request.POST
        if p['password']:
            user = User.objects.create_user(username=eveigb.charname, password=p['password'])
            user.save()
            return index(request, 'Successfully created account on the server.')
        return login_page(request, 'You must enter a password.')
    return index(request)

def settings(request):
    """ Settings page for viewing and changing user settings """
    eveigb = IGBHeaderParser(request)
    if not can_view(eveigb, request):
        return no_access(request)
    message = None
    try:
        settings = Settings.objects.get(user=eveigb.charname)
    except Settings.DoesNotExist:
        settings = Settings(user=eveigb.charname, editsInNewTabs=True, storeMultiple=True)
        settings.save()
    if request.method == 'POST':
        p = request.POST
        edit = False
        store = False
        image = False
        if 'edit' in p:
            edit = True
        if 'store' in p:
            store = True
        if 'image' in p:
            image = True
        settings.editsInNewTabs = edit
        settings.storeMultiple = store
        settings.userBackgroundImage = image
        settings.save()
        message = 'Settings saved.'
    edit = settings.editsInNewTabs
    store = settings.storeMultiple
    image = settings.userBackgroundImage
    return render(request, 'sitemngr/settings.html', {'displayname': get_display_name(eveigb, request), 'edit': edit, 'store': store, 'image': image, 'message': message})

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

def get_search_results(request, keyword, flags):
    """ Returns a list of links for use by the search feature on the index page """
    flags = Flag(flags)
    ret = []
    raw = []
    wormholes = []
    if flags.open_only and not flags.closed_only:
        wormholes.extend([w for w in Wormhole.objects.filter(opened=True)])
    elif not flags.open_only and flags.closed_only:
        wormholes.extend([w for w in Wormhole.objects.filter(opened=False)])
    else:
        wormholes.extend([w for w in Wormhole.objects.all()])
    if flags.sites or flags.systems:
        wormholes = []
    sites = []
    if flags.open_only and not flags.closed_only:
        sites.extend([s for s in Site.objects.filter(opened=True)])
    elif not flags.open_only and flags.closed_only:
        sites.extend([s for s in Site.objects.filter(opened=False)])
    else:
        sites.extend([s for s in Site.objects.all()])
    if flags.wormholes or flags.systems:
        sites = []
    if not flags.wormholes and not flags.sites:
        # check system names in the chain
        for system in get_chain_systems():
            if system.startswith(keyword) and not system in raw:
                ret.append(Result('system/%s' % system, system))
                raw.append(system)
        # check tradehub system names
        if flags.universe and not flags.chain:
            for system in get_tradehub_system_names():
                if system.startswith(keyword) and not system in raw:
                    ret.append(Result('system/%s' % system, system))
    # check site names and locations, and scanids
    for site in sites:
        if site.where.startswith(keyword) or site.name.startswith(keyword) or site.scanid.startswith(keyword) or site.scanid == keyword:
            ret.append(Result('viewsite/%s' % site.id, 'Site %s' % site))
            raw.append(site)
    # check wormhole start and destination system names, and scanids
    for wormhole in wormholes:
        if wormhole.start.startswith(keyword) or wormhole.destination.startswith(keyword) or wormhole.scanid.startswith(keyword) or wormhole.scanid == keyword:
            ret.append(Result('viewwormhole/%s' % wormhole.id, 'Wormhole %s' % wormhole))
            raw.append(wormhole)
    # if we've found nothing else, then check system names from all of the universe if we can include systems
    if flags.universe or (len(ret) == 0 and not flags.wormholes and not flags.sites and not flags.chain):
        for system in MapSolarSystem.objects.all():
            if system.name.startswith(keyword):
                ret.append(Result('system/%s' % system.name, system.name))
    if len(ret) == 0:
        ret.append(Result('', 'No results'))
    return render(request, 'sitemngr/search_results.html', {'results': ret, 'flags': flags})

def refresh_graph(request):
    """ A simple redirect used for manually refreshing the wormhole chain graph """
    set_dirty()
    return index(request)

# ==============================
#     Util
# ==============================

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

def no_access(request):
    """ Shown when the viewer is restricted from viewing the page """
    eveigb = IGBHeaderParser(request)
    wrongAlliance = can_view_wrong_alliance(eveigb)
    return render(request, 'sitemngr/noaccess.html', {'displayname': get_display_name(eveigb, request), 'wrongAlliance': wrongAlliance})

def getBoolean(s):
    """ Returns True if the string represents a boolean equalling True """
    return s.lower() in ['true', 't', '1', 'yes', 'on']

def get_display_name(eveigb, request):
    """ Returns the correct name of a user from their browser """
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
