from django.contrib.auth import authenticate, login
from django.contrib.auth.models import User
from django.shortcuts import render, get_object_or_404
from sitemngr.models import (Site, SiteChange,
                             Wormhole, WormholeChange,
                             PasteData, Whitelisted,
                             Settings, KillReport)
from eveigb import IGBHeaderParser
from eve_db.models import MapSolarSystem
import datetime
import re
import urllib2
import evelink
import settings as appSettings

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
    notices = ['See the stats page for a graph of all-time edit counts.']
    if note and note is not None:
        notices.append(note)
    return render(request, 'sitemngr/index.html', {'sites': sites, 'wormholes': wormholes, 'status': 'open', 'notices': notices, 'newTab': getSettings(eveigb.charname).editsInNewTabs, 'flag': note})

def viewall(request):
    """ Index page, but with the closed objects instead of the open """
    eveigb = IGBHeaderParser(request)
    if not canView(eveigb, request):
        return noaccess(request)
    sites = Site.objects.filter(closed=True)
    wormholes = Wormhole.objects.filter(closed=True)
    return render(request, 'sitemngr/index.html', {'sites': sites, 'wormholes': wormholes, 'status': 'closed'})

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
    return render(request, 'sitemngr/add.html', {'scanid': scanid})

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
    return render(request, 'sitemngr/viewsite.html', {'isForm': False, 'site': site, 'changes': changes})

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
            change = SiteChange(site=site, date=now, user=eveigb.charname, changedName=changedName, changedScanid=changedScanid,
                                changedType=changedType, changedWhere=changedWhere, changedDate=changedDate, changedOpened=changedOpened,
                                changedClosed=changedClosed, changedNotes=changedNotes)
            change.save()
        return index(request)
    return render(request, 'sitemngr/editsite.html', {'isForm': True, 'site': site, 'finish_msg': 'Store changes back into the database:'})

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
            return render(request, 'sitemngr/addsite.html', {'isForm': True,
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
    return render(request, 'sitemngr/addsite.html', {
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
    return render(request, 'sitemngr/viewwormhole.html', {'isForm': False, 'wormhole': wormhole, 'changes': changes})

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
            changed = WormholeChange(wormhole=wormhole, user=eveigb.charname if eveigb.charname is not '' else request.user.username, date=now, changedScanid=changedScanid, changedType=False,
                                 changedStart=changedStart, changedDestination=changedDestination, changedTime=changedTime, changedStatus=changedStatus,
                                 changedOpened=changedOpened, changedClosed=changedClosed, changedNotes=changedNotes)
            changed.save()
        return index(request)
    return render(request, 'sitemngr/viewwormhole.html', {'isForm': True,
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
        # upData = UpdateData(notes='')
        # upData.save()
        if getSettings(eveigb.charname).storeMultiple:
            return render(request, 'sitemngr/addwormhole.html', {
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
    return render(request, 'sitemngr/addwormhole.html', {
                 'isForm': True, 'finish_msg': 'Store new wormhole into the database:', 'g_scanid': g_scanid, 'g_system': g_system, 'g_name': g_name, 'timenow': now.strftime('%m/%d @ %H:%M')})

# ==============================
#     Pastes
# ==============================

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
            # After paste and checking after downtime checkbox
            sites = []
            wormholes = []
            newids = []
            paste = post['pastedata']
            system = post['system']
            allSites = Site.objects.filter(where=system, closed=False)
            for s in allSites:
                sites.append(s)
            allWormholes = Wormhole.objects.filter(start=system, closed=False)
            for w in allWormholes:
                wormholes.append(w)
            for line in paste.split('\n'):
                for section in line.split('\t'):
                    if section is None:
                        pass
                    elif re.match(r'^[a-zA-Z]{3}-\d{3}$', section):
                        newids.append(section[:3].upper())
            return render(request, 'sitemngr/pastescandowntime.html', {'sites': sites, 'wormholes': wormholes,
                           'newids': newids, 'newTab': getSettings(eveigb.charname).editsInNewTabs})
        elif post.has_key('afterdowntime') and post['afterdowntime']:
            # After downtime paste page after submitting database changes
            for k, v in post.iteritems():
                if k == 'csrfmiddlewaretoken' or k == 'afterdowntime':
                    continue
                if v == '-IGNORE-':
                    continue
                if isSite(k):
                    s = getSite(k)
                    if v == '-CLOSE-':
                        s.closed = True
                        s.save()
                        c = SiteChange(site=s, date=now, user=eveigb.charname, changedName=False, changedScanid=False,
                                    changedType=False, changedWhere=False, changedDate=False, changedOpened=False,
                                    changedClosed=True, changedNotes=False)
                        c.save()
                    else:
                        s.notes += ' Scanid: {0} >> {1}'.format(s.scanid, v)
                        s.scanid = v
                        s.save()
                        c = SiteChange(site=s, date=now, user=eveigb.charname, changedName=False, changedScanid=True,
                                    changedType=False, changedWhere=False, changedDate=False, changedOpened=False,
                                    changedClosed=False, changedNotes=False)
                        c.save()
                else:
                    w = getWormhole(k)
                    if v == '-CLOSE-':
                        w.closed = True
                        w.save()
                        c = WormholeChange(wormhole=w, user=eveigb.charname, date=now, changedScanid=False, changedType=False,
                                     changedStart=False, changedDestination=False, changedTime=False, changedStatus=False,
                                     changedOpened=False, changedClosed=True, changedNotes=False)
                        c.save()
                    else:
                        w.notes += 'Scanid: {0} >> {1}'.format(w.scanid, v)
                        w.scanid = v
                        w.save()
                        c = WormholeChange(wormhole=w, user=eveigb.charname, date=now, changedScanid=True, changedType=False,
                                     changedStart=False, changedDestination=False, changedTime=False, changedStatus=False,
                                     changedOpened=False, changedClosed=False, changedNotes=False)
                        c.save()
            return index(request)
        else:
            # Parse data to return to normal paste page
            siteTypes = ['Unstable Wormhole', 'Anomaly', 'Ore Site', 'Relic Site', 'Data Site', 'Gas Site', 'Cosmic Signature']
            present = []
            findnew = []
            notfound = []
            if 'pastedata' in post and post['pastedata'] and 'system' in post and post['system']:
            # {
                paste = post['pastedata']
                system = post['system']
                notfound.extend(Site.objects.filter(where=system, closed=False))
                notfound.extend(Wormhole.objects.filter(start=system, closed=False))
                for line in paste.split('\n'):
                # {
                    newP = PasteData(p_system=system)
                    found = False
                    for section in line.split('\t'):
                    # {
                        if section is None:
                            continue
                        elif 'AU' in section:
                            continue
                        elif '%' in section:
                            continue
                        elif 'wormhole' in section.lower():
                            newP.isSite = False
                        elif section == 'Cosmic Signature':
                            continue
                        elif re.match(r'^[a-zA-Z]{3}-\d{1,3}$', section):
                        # {
                            section = section.upper()
                            if isSite(section[:3]):
                                s = getSite(section[:3])
                                if s.where == system:
                                    notfound.remove(s)
                                    found = True
                                    present.append(s)
                            elif isWormhole(section[:3]):
                                w = getWormhole(section[:3])
                                if w.start == system:
                                    notfound.remove(w)
                                    found = True
                                    present.append(w)
                            if not found:
                                newP.scanid = section[:3]
                        # }
                        elif section in siteTypes:
                            newP.type = section
                        else:
                            newP.name = section
                    # }
                    if not found:
                        findnew.append(newP)
                # }
                return render(request, 'sitemngr/pastescan.html', {'raw': post['pastedata'],
                               'present': present, 'notfound': notfound, 'findnew': findnew, 'timenow': now, 'system': system, 'newTab': getSettings(eveigb.charname).editsInNewTabs})
            # }
    # Base request - show the base pastescan page
    return render(request, 'sitemngr/pastescan.html', {'timenow': now, 'newTab': getSettings(eveigb.charname).editsInNewTabs})


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
    for s in Site.objects.filter(closed=False):
        if (s.where in systems) == False:
            systems.append(s.where)
    for w in Wormhole.objects.filter(closed=False):
        if (w.start in systems) == False:
                systems.append(w.start)
    return render(request, 'sitemngr/systemlanding.html', {'systems': systems, 'timenow': now})

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
    return render(request, 'sitemngr/system.html', {'system': systemid, 'openwormholes': openwormholes, 'closedwormholes': closedwormholes,
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
    for s in Site.objects.all():
        if s.scanid == scanid:
            if system is not None:
                if s.where == system:
                    return viewsite(request, s.id)
            else:
                return viewsite(request, s.id)
    for w in Wormhole.objects.all():
        if w.scanid == scanid:
            if system is not None:
                if w.start == system:
                    return viewwormhole(request, w.id)
            else:
                return viewwormhole(request, w.id)
    return render(request, 'sitemngr/lookup.html')

def mastertable(request):
    """ Master spreadsheet-link page for browsing """
    eveigb = IGBHeaderParser(request)
    if not canView(eveigb, request):
        return noaccess(request)
    sites = Site.objects.all()
    wormholes = Wormhole.objects.all()
    return render(request, 'sitemngr/mastertable.html', {'sites': sites, 'wormholes': wormholes})


# ==============================
#     Data
# ==============================

def changelog(request):
    """ Site changelog """
    return render(request, 'sitemngr/changelog.html')

def igbtest(request):
    """ Show all data that the in-game browser can send to a Trusted Site """
    return render(request, 'sitemngr/igbtest.html')

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
    return render(request, 'sitemngr/recentscanedits.html', {'sites': sites, 'wormholes': wormholes})

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
    for s in Site.objects.filter(closed=False, where=str(appSettings.HOME_SYSTEM)):
        motd += s.printOut() + '\n'
    return render(request, 'sitemngr/output.html', {'motd': motd})

def stats(request):
    """ Returns usage statistics """
    eveigb = IGBHeaderParser(request)
    if not canView(eveigb, request):
        return noaccess(request)
    numSites = len(Site.objects.all())
    numWormholes = len(Wormhole.objects.all())
    numEdits = len(SiteChange.objects.all()) + len(WormholeChange.objects.all())
    con = {}
    for s in Site.objects.all():
        if s.creator in con:
            con[s.creator] += 1
        else:
            con[s.creator] = 1
    for w in Wormhole.objects.all():
        if w.creator in con:
            con[w.creator] += 1
        else:
            con[w.creator] = 1
    for s in SiteChange.objects.all():
        if s.user in con:
            con[s.user] += 1
        else:
            con[s.user] = 1
    for w in WormholeChange.objects.all():
        if w.user in con:
            con[w.user] += 1
        else:
            con[w.user] = 1
    numContributors = len(con)
    conList = []
    con = sorted(con.items(), key=lambda kv: kv[1])
    for a, b in con:
        conList.append(Contributor(a, b))
    return render(request, 'sitemngr/stats.html', {'numSites': numSites,
               'numWormholes': numWormholes, 'numEdits': numEdits, 'numContributors': numContributors, 'allContributors': conList})

def checkkills(request):
    """ Returns a readout of all ship and pod kills in and system with open objects """
    eveigb = IGBHeaderParser(request)
    if not canView(eveigb, request):
        return noaccess(request)
    reports = []
    systems = []
    for w in Wormhole.objects.filter(closed=False):
        if w.start not in systems:
            systems.append(w.start)
        if w.destination not in systems:
            systems.append(w.destination)
    if len(systems) > 0:
        retSys = []
        for s in systems:
            retSys.append(getSystemID(s))
        kills = evemap.kills_by_system()[0]
        for k in kills.iteritems():
            if k[0] in retSys:
                r = KillReport(system=getSystemName(k[0]), systemid=k[0], ship=k[1]['ship'], pod=k[1]['pod'])
                reports.append(r)
    return render(request, 'sitemngr/checkkills.html', {'systems': systems, 'reports': reports})

def viewhelp(request):
    """ Help/instructions page """
    eveigb = IGBHeaderParser(request)
    return render(request, 'sitemngr/help.html', {'able': canView(eveigb, request)})

# ==============================
#     Accounts
# ==============================

def login_page(request):
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
                    return index(request, 'This account is disabled')
            else:
                return index(request, 'An error occurred when logging in')
    return render(request, 'sitemngr/login.html')

def create_account(request):
    """
        Create an account on the server
        Must be done from the in-game browser
    """
    eveigb = IGBHeaderParser(request)
    if not canView(eveigb):
        return noaccess(request)
    if User.objects.get(username__exact=eveigb.charname):
        return index(request, 'You already have an account on this server.')
    if request.method == 'POST':
        p = request.POST
        if p['password']:
            user = User.objects.create_user(username=eveigb.charname, password=p['password'])
            user.save()
            return index(request, 'Successfully created account on the server.')
    return index(request)

def settings(request):
    """ Settings page for viewing and changing user settings """
    # TODO: This page only works for in-game browser character settings
    eveigb = IGBHeaderParser(request)
    if not canView(eveigb):
        return noaccess(request)
    message = None
    try:
        s = Settings.objects.get(user=eveigb.charname)
    except Settings.DoesNotExist:
        s = Settings(user=eveigb.charname, editsInNewTabs=True, storeMultiple=True)
        s.save()
    if request.method == 'POST':
        p = request.POST
        edit = False
        store = False
        if 'edit' in p:
            edit = True
        if 'store' in p:
            store = True
        s.editsInNewTabs = edit
        s.storeMultiple = store
        s.save()
        message = 'Settings saved.'
    edit = s.editsInNewTabs
    store = s.storeMultiple
    return render(request, 'sitemngr/settings.html', {'edit': edit, 'store': store, 'message': message})

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
    return render(request, 'sitemngr/noaccess.html', {'wrongAlliance': wrongAlliance})

def getBoolean(s):
    """ Returns True if the string represents a boolean equalling True """
    return s.lower() in ['true', 't', '1', 'yes', 'on']

def canView(igb, request=None):
    """
        Returns True if the user can view that page by testing
        if they are using the EVE IGB (Trusted mode) and in the appropriate alliance
    """
    if request is not None:
        if request.user is not None:
            if request.user.is_active:
                return True
    isWhitelisted = False
    try:
        w = Whitelisted.objects.get(name=igb.charname)
        if w is not None and w.active:
            isWhitelisted = True
    except Whitelisted.DoesNotExist:
        pass
    return igb is not None and igb.is_igb and igb.trusted and (igb.alliancename == appSettings.ALLIANCE_NAME or isWhitelisted)

def canViewWrongAlliance(igb):
    """
        Returns True if the user can view that page by testing
        if they are using the EVE IGB (Trusted mode), but does not check alliance
    """
    return igb is not None and igb.is_igb and igb.trusted

def isSite(scanid):
    """ Returns True if the scanid represents a site object """
    return getSite(scanid) is not None

def getSite(scanid):
    """ Returns site with scan id (or None) """
    for s in Site.objects.all():
        if s.scanid.lower() == scanid.lower():
            return s
    return None

def isWormhole(scanid):
    """ Returns True if the scanid represents a wormhole object """
    return getWormhole(scanid) is not None

def getWormhole(scanid):
    """ Returns wormhole with scanid (or None) """
    for w in Wormhole.objects.all():
        if w.scanid.lower() == scanid.lower():
            return w
    return None

def getSettings(username):
    """ Returns the settings for a user """
    try:
        s = Settings.objects.get(user=username)
    except Settings.DoesNotExist:
        s = Settings(user=username, editsInNewTabs=True, storeMultiple=True)
        s.save()
    return s
