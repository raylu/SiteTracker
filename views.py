# Python
import datetime
import re
import urllib2

# Django
from django.shortcuts import render, get_object_or_404
from django.contrib.auth.models import User
from django.contrib.auth import authenticate, login, logout

# sitemngr
from sitemngr.models import (Site, SiteChange,
                             Wormhole, WormholeChange,
                             PasteData, Settings,
                             KillReport, PasteMatch)
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

# ==============================
#     Index
# ==============================

def index(request, note=None):
    """ Index page - lists all open sites """
    eveigb = IGBHeaderParser(request)
    if not canView(eveigb, request):
        return noaccess(request)
    sites = Site.objects.filter(closed=False)
    wormholes = Wormhole.objects.filter(closed=False)
    notices = ['The downtime paste page has been completely redone.']
    if note and note is not None:
        notices.append(note)
    return render(request, 'sitemngr/index.html', {'displayname': get_display_name(eveigb, request), 'sites': sites, 'wormholes': wormholes, 'status': 'open', 'notices': notices, 'newTab': getSettings(get_display_name(eveigb, request)).editsInNewTabs, 'backgroundimage': getSettings(get_display_name(eveigb, request)).userBackgroundImage, 'flag': note})

def viewall(request):
    """ Index page, but with the closed objects instead of the open """
    eveigb = IGBHeaderParser(request)
    if not canView(eveigb, request):
        return noaccess(request)
    sites = Site.objects.filter(closed=True)
    wormholes = Wormhole.objects.filter(closed=True)
    return render(request, 'sitemngr/index.html', {'displayname': get_display_name(eveigb, request), 'sites': sites, 'wormholes': wormholes, 'status': 'closed'})

def add(request):
    """
        Landing page for adding to the database - only used for clarification from
            the user after using the paste page
    """
    eveigb = IGBHeaderParser(request)
    if not canView(eveigb, request):
        return noaccess(request)
    scanid = ''
    if request.method == 'GET':
        g = request.GET
        if g.has_key('scanid') and g['scanid']:
            scanid = g['scanid']
    return render(request, 'sitemngr/add.html', {'displayname': get_display_name(eveigb, request), 'scanid': scanid})

# ==============================
#     Site
# ==============================

def viewsite(request, siteid):
    """ Views all the data on a particular site, including a list of changes """
    eveigb = IGBHeaderParser(request)
    if not canView(eveigb, request):
        return noaccess(request)
    site = get_object_or_404(Site, pk=siteid)
    changes = site.getChanges()
    return render(request, 'sitemngr/viewsite.html', {'displayname': get_display_name(eveigb, request), 'isForm': False, 'site': site, 'changes': changes})

def editsite(request, siteid):
    """ Edit site page for changing data """
    eveigb = IGBHeaderParser(request)
    if not canView(eveigb, request):
        return noaccess(request)
    site = get_object_or_404(Site, pk=siteid)
    if request.method == 'POST':
        p = request.POST
        now = datetime.datetime.now()
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
                site.scanid = p['scanid']
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
        if changedName or changedScanid or changedType or changedWhere or changedDate or changedOpened or changedClosed or changedNotes:
            if appendNotes is not None:
                site.notes += appendNotes
            site.save()
            change = SiteChange(site=site, date=now, user=eveigb.charname if eveigb.charname is not '' else request.user.username, changedName=changedName, changedScanid=changedScanid,
                                changedType=changedType, changedWhere=changedWhere, changedDate=changedDate, changedOpened=changedOpened,
                                changedClosed=changedClosed, changedNotes=changedNotes)
            change.save()
        return index(request)
    return render(request, 'sitemngr/editsite.html', {'displayname': get_display_name(eveigb, request), 'isForm': True, 'site': site, 'finish_msg': 'Store changes back into the database:'})

def addsite(request):
    """ Add a site to the databse """
    eveigb = IGBHeaderParser(request)
    if not canView(eveigb, request):
        return noaccess(request)
    g_scanid = ''
    g_system = ''
    g_type = ''
    g_name = ''
    now = datetime.datetime.now()
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
            s_scanid = p['scanid']
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
        site = Site(name=s_name, scanid=s_scanid, type=s_type, where=s_where, creator=eveigb.charname, date=now, opened=s_opened, closed=s_closed, notes=s_notes)
        site.save()
        if getSettings(eveigb.charname).storeMultiple:
            return render(request, 'sitemngr/addsite.html', {'displayname': get_display_name(eveigb, request), 'isForm': True,
                 'message': 'Successfully stored the data into the database.', 'finish_msg': 'Store new site into the database:', 'timenow': now.strftime('%m/%d @ %H:%M')})
        else:
            return index(request)
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

def viewwormhole(request, wormholeid):
    """ Views all the data on a particular wormhole, including a list of changes """
    eveigb = IGBHeaderParser(request)
    if not canView(eveigb, request):
        return noaccess(request)
    wormhole = get_object_or_404(Wormhole, pk=wormholeid)
    changes = wormhole.getChanges()
    return render(request, 'sitemngr/viewwormhole.html', {'displayname': get_display_name(eveigb, request), 'isForm': False, 'wormhole': wormhole, 'changes': changes})

def editwormhole(request, wormholeid):
    """ Edit wormhole page for changing data """
    eveigb = IGBHeaderParser(request)
    if not canView(eveigb, request):
        return noaccess(request)
    wormhole = get_object_or_404(Wormhole, pk=wormholeid)
    if request.method == 'POST':
        p = request.POST
        now = datetime.datetime.now()
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
                wormhole.scanid = p['scanid']
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
        if changedScanid or changedStart or changedDestination or changedTime or changedStatus or changedOpened or changedClosed or changedNotes:
            if appendNotes is not None:
                wormhole.notes += appendNotes
            wormhole.save()
            change = WormholeChange(wormhole=wormhole, user=eveigb.charname if eveigb.charname is not '' else request.user.username, date=now, changedScanid=changedScanid, changedType=False, changedStart=changedStart, changedDestination=changedDestination, changedTime=changedTime, changedStatus=changedStatus, changedOpened=changedOpened, changedClosed=changedClosed, changedNotes=changedNotes)
            change.save()
        return index(request)
    return render(request, 'sitemngr/viewwormhole.html', {'displayname': get_display_name(eveigb, request), 'isForm': True,
          'wormhole': wormhole, 'finish_msg': 'Store changes back into the database'})

def addwormhole(request):
    """ Add a wormhole to the databse """
    eveigb = IGBHeaderParser(request)
    if not canView(eveigb, request):
        return noaccess(request)
    g_scanid = ''
    g_system = ''
    g_name = ''
    now = datetime.datetime.now()
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
            s_scanid = p['scanid']
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
        wormhole = Wormhole(creator=eveigb.charname, date=now, scanid=s_scanid, type='null', start=s_start, destination=s_destination,
                            time=s_time, status=s_status, opened=s_opened, closed=s_closed, notes=s_notes)
        wormhole.save()
        if getSettings(eveigb.charname).storeMultiple:
            return render(request, 'sitemngr/addwormhole.html', {'request': request, 'displayname': get_display_name(eveigb, request),
                    'isForm': True, 'message': 'Successfully stored the data into the database.', 'finish_msg': 'Store new site into database:', 'timenow': now.strftime('%m/%d @ %H:%M')})
        else:
            return index(request)
    elif request.method == 'GET':
        g = request.GET
        if g.has_key('scanid') and g['scanid']:
            g_scanid = g['scanid']
        if g.has_key('system') and g['system']:
            g_system = g['system']
        if g.has_key('name') and g['name']:
            g_name = g['name']
    return render(request, 'sitemngr/addwormhole.html', {'request': request, 'displayname': get_display_name(eveigb, request),
                 'isForm': True, 'finish_msg': 'Store new wormhole into the database:', 'g_scanid': g_scanid, 'g_system': g_system, 'g_name': g_name, 'timenow': now.strftime('%m/%d @ %H:%M')})

# ==============================
#     Pastes
# ==============================

def p_get_all_data(line):
    siteTypes = ['Cosmic Signature', 'Data Site', 'Relic Site']
    anomTypes = ['Combat Site', 'Ore Site']  # 'Gas Site' ?
    wormholeTypes = ['Wormhole', 'Unstable Wormhole']
    data = {}
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
    if not canView(eveigb, request):
        return noaccess(request)
    now = datetime.datetime.now()
    if request.method == 'POST':
        post = request.POST
        if post.has_key('downtime') and post['downtime']:
            # After paste and checking after downtime checkbox - prepare data for user to make changes after downtime
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
                           'displayname': get_display_name(eveigb, request), 'newTab': getSettings(get_display_name(eveigb, request)).editsInNewTabs, 'backgroundimage': getSettings(get_display_name(eveigb, request)).userBackgroundImage})
        elif post.has_key('afterdowntime') and post['afterdowntime']:
            # After downtime paste page after submitting database changes
            for k, v in post.iteritems():
                if ' ' in k:
                    k = k.split(' ')[0]
                if ':' in v:
                    v = v.split(':')[0]
                if k == 'csrfmiddlewaretoken' or k == 'afterdowntime':
                    continue
                if v == '-IGNORE-':
                    continue
                if isSite(k):
                    site = getSite(k)
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
                    wormhole = getWormhole(k)
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
            return index(request)
        else:
            # Parse data to return to normal paste page
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
                    if isSite(newP.scanid):
                        site = getSite(newP.scanid)
                        if site.where == system:
                            notfound.remove(site)
                            found = True
                            present.append(site)
                    elif isWormhole(newP.scanid):
                        wormhole = getWormhole(newP.scanid)
                        if wormhole.start == system:
                            notfound.remove(wormhole)
                            found = True
                            present.append(wormhole)
                    if not found:
                        findnew.append(newP)
                return render(request, 'sitemngr/pastescan.html', {'displayname': get_display_name(eveigb, request), 'raw': post['pastedata'],
                               'present': present, 'notfound': notfound, 'findnew': findnew, 'timenow': now, 'system': system, 'newTab': getSettings(get_display_name(eveigb, request)).editsInNewTabs, 'backgroundimage': getSettings(get_display_name(eveigb, request)).userBackgroundImage})
    # Base request - show the base pastescan page
    return render(request, 'sitemngr/pastescan.html', {'displayname': get_display_name(eveigb, request), 'timenow': now, 'newTab': getSettings(get_display_name(eveigb, request)).editsInNewTabs, 'backgroundimage': getSettings(get_display_name(eveigb, request)).userBackgroundImage})


# ==============================
#     Systems
# ==============================

def systemlanding(request):
    """ Return a list of a systems with active sites """
    eveigb = IGBHeaderParser(request)
    if not canView(eveigb, request):
        return noaccess(request)
    now = datetime.datetime.now()
    systems = []
    for site in Site.objects.filter(closed=False):
        if (site.where in systems) == False:
            systems.append(site.where)
    for wormhole in Wormhole.objects.filter(closed=False):
        if (wormhole.start in systems) == False:
                systems.append(wormhole.start)
    return render(request, 'sitemngr/systemlanding.html', {'displayname': get_display_name(eveigb, request), 'systems': systems, 'timenow': now})

def system(request, systemid):
    """
        Show all wormholes into and out of this system.
        Also show all closed wormholes in this system in the last 10 (configurable) days.
    """
    eveigb = IGBHeaderParser(request)
    if not canView(eveigb, request):
        return noaccess(request)
    openwormholes = []
    opensites = Site.objects.filter(where=systemid, closed=False, opened=True)
    openwormholes.extend(Wormhole.objects.filter(start=systemid, closed=False, opened=True))
    unopenedsites = Site.objects.filter(where=systemid, closed=False, opened=False)
    for w in Wormhole.objects.filter(destination=systemid, closed=False, opened=True):
        if not w in openwormholes:
            openwormholes.append(w)
    closedwormholes = Wormhole.objects.filter(start=systemid, closed=True)
    clazz = 0
    if re.match(r'J\d{6}', systemid):
        contents = urllib2.urlopen('http://www.ellatha.com/eve/WormholeSystemview.asp?key={0}'.format(systemid.replace('J', ''))).read().split('\n')
        nextLine = False
        for line in contents:
            if 'Class:' in line:
                nextLine = True
                continue
            if nextLine:
                clazz = line.split('&')[0][-1]
                break
    return render(request, 'sitemngr/system.html', {'displayname': get_display_name(eveigb, request), 'system': systemid, 'openwormholes': openwormholes, 'closedwormholes': closedwormholes,
                            'class': clazz, 'opensites': opensites, 'unopenedsites': unopenedsites})


# ==============================
#     Reference lookup
# ==============================

def lookup(request, scanid):
    """ Lookup page for finding sites and wormholes by their scanid """
    eveigb = IGBHeaderParser(request)
    if not canView(eveigb, request):
        return noaccess(request)
    system = None
    if request.method == 'GET':
        g = request.GET
        if g.has_key('system') and g['system']:
            system = g['system']
    for site in Site.objects.all():
        if site.scanid == scanid:
            if system is not None:
                if site.where == system:
                    return viewsite(request, site.id)
            else:
                return viewsite(request, site.id)
    for wormhole in Wormhole.objects.all():
        if wormhole.scanid == scanid:
            if system is not None:
                if wormhole.start == system:
                    return viewwormhole(request, wormhole.id)
            else:
                return viewwormhole(request, wormhole.id)
    return render(request, 'sitemngr/lookup.html')

def mastertable(request):
    """ Master spreadsheet-link page for browsing """
    eveigb = IGBHeaderParser(request)
    if not canView(eveigb, request):
        return noaccess(request)
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

def igbtest(request):
    """ Show all data that the in-game browser can send to a Trusted Site """
    eveigb = IGBHeaderParser(request)
    return render(request, 'sitemngr/igbtest.html', {'displayname': get_display_name(eveigb, request)})

def recentscanedits(request):
    """ Returns a readout of all recent scanid changes """
    eveigb = IGBHeaderParser(request)
    if not canView(eveigb, request):
        return noaccess(request)
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
    if not canView(eveigb, request):
        return noaccess(request)
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
    if not canView(eveigb, request):
        return noaccess(request)
    numSites = len(Site.objects.all())
    numWormholes = len(Wormhole.objects.all())
    numEdits = len(SiteChange.objects.all()) + len(WormholeChange.objects.all())
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
    numContributors = len(con)
    conList = []
    con = sorted(con.items(), key=lambda kv: kv[1])
    for name, count in con:
        conList.append(Contributor(name, count))
    return render(request, 'sitemngr/stats.html', {'displayname': get_display_name(eveigb, request), 'numSites': numSites,
               'numWormholes': numWormholes, 'numEdits': numEdits, 'numContributors': numContributors, 'allContributors': conList})

def checkkills(request):
    """ Returns a readout of all ship and pod kills in and system with open objects """
    eveigb = IGBHeaderParser(request)
    if not canView(eveigb, request):
        return noaccess(request)
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
            retSys.append(getSystemID(system))
        kills = evemap.kills_by_system()[0]
        for k in kills.iteritems():
            if k[0] in retSys:
                r = KillReport(system=getSystemName(k[0]), systemid=k[0], ship=k[1]['ship'], pod=k[1]['pod'])
                reports.append(r)
    return render(request, 'sitemngr/checkkills.html', {'displayname': get_display_name(eveigb, request), 'systems': systems, 'reports': reports})

def viewhelp(request):
    """ Help/instructions page """
    eveigb = IGBHeaderParser(request)
    return render(request, 'sitemngr/help.html', {'displayname': get_display_name(eveigb, request), 'able': canView(eveigb, request)})

# ==============================
#     Accounts
# ==============================

# TODO: 
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
    return render(request, 'sitemngr/login.html', {'note': note})

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
        if not canView(eveigb):
            return noaccess(request)
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
    if not canView(eveigb, request):
        return noaccess(request)
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

# ==============================
#     Util
# ==============================

def getSystemName(systemid):
    """ Returns the common name for the system from the Eve API's systemid representation """
    try:
        return MapSolarSystem.objects.get(id=systemid).name
    except MapSolarSystem.DoesNotExist:
        return 'null'

def getSystemID(systemname):
    """ Returns the systemid for use in the Eve API corresponding to the systemname """
    try:
        return MapSolarSystem.objects.get(name=systemname).id
    except MapSolarSystem.DoesNotExist:
        return 'null'

class Contributor:
    def __init__(self, name, points):
        self.name = name
        self.points = points

def noaccess(request):
    """ Shown when the viewer is restricted from viewing the page """
    eveigb = IGBHeaderParser(request)
    wrongAlliance = canViewWrongAlliance(eveigb)
    return render(request, 'sitemngr/noaccess.html', {'displayname': get_display_name(eveigb, request), 'wrongAlliance': wrongAlliance})

def getBoolean(s):
    """ Returns True if the string represents a boolean equalling True """
    return s.lower() in ['true', 't', '1', 'yes', 'on']

def get_display_name(eveigb, request):
    if request.user is not None:
        if request.user.is_active and request.user.is_authenticated:
            return request.user.username
    if eveigb.trusted:
        return eveigb.charname
    return 'someone'

def canView(igb, request=None):
    """
        Returns True if the user can view that page by testing
            if they are using the EVE IGB (Trusted mode) and in the appropriate alliance
    """
    if request is not None:
        if request.user is not None:
            if request.user.is_active:
                return True
    return igb is not None and igb.is_igb and igb.trusted and igb.alliancename == appSettings.ALLIANCE_NAME

def canViewWrongAlliance(igb):
    """
        Returns True if the user can view that page by testing
            if they are using the EVE IGB (Trusted mode), but does not check alliance
    """
    return igb is not None and igb.is_igb and igb.trusted and igb.alliancename != appSettings.ALLIANCE_NAME

def isSite(scanid):
    """ Returns True if the scanid represents a site object """
    return getSite(scanid) is not None

def getSite(scanid):
    """ Returns site with scan id (or None) """
    for site in Site.objects.all():
        if site.scanid.lower() == scanid.lower():
            return site
    return None

def isWormhole(scanid):
    """ Returns True if the scanid represents a wormhole object """
    return getWormhole(scanid) is not None

def getWormhole(scanid):
    """ Returns wormhole with scanid (or None) """
    for wormhole in Wormhole.objects.all():
        if wormhole.scanid.lower() == scanid.lower():
            return wormhole
    return None

def getSettings(username):
    """ Returns the settings for a user """
    try:
        settings = Settings.objects.get(user=username)
    except Settings.DoesNotExist:
        settings = Settings(user=username, editsInNewTabs=True, storeMultiple=True)
        settings.save()
    return settings
