from datetime import datetime
import re

# Django
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.contrib.auth.models import User
from django.contrib.auth import authenticate, login, logout
from django.views.decorators.csrf import csrf_exempt
from django.http import HttpResponse

# sitemngr
from models import (Site, SiteSnapshot,
                    Wormhole, WormholeSnapshot,
                    PasteUpdated, Settings,
                    System, DatabaseUpToDate)
import settings as appSettings
import util

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
    if not util.can_view(eveigb, request):
        return no_access(request)
    notices = ['Be sure to check out the video tutorial series, posted on the forums!']
    if request.method == 'POST':
        p = request.POST
        if p['data_type'] == 'wormhole':
            scanid = p['scanid'].upper()
            start = p['start']
            destination = p['destination']
            status = p['status']
            Wormhole(creator=util.get_display_name(eveigb, request), date=datetime.utcnow(), scanid=scanid.upper(), start=start, destination=destination,
                            status=status, opened=False if destination.lower() in ['unopened', 'closed'] else True, closed=False, notes='').save()
            notices.append('New wormhole added')
        elif p['data_type'] == 'site':
            scanid = p['scanid'].upper()
            name = p['name']
            type = p['type']
            where = p['where']
            Site(name=name, scanid=scanid.upper(), type=type, where=where, creator=util.get_display_name(eveigb, request), date=datetime.utcnow(), opened=False, closed=False, notes='').save()
            notices.append('New site added')
    sites = Site.objects.filter(closed=False)
    wormholes = Wormhole.objects.filter(closed=False)
    
    # timers for couting down the rest of a wormhole's lifespan
    maxTimers = {}
    for wormhole in wormholes:
        maxTimers[wormhole.id] = util.maxTimeLeft(wormhole)

    # check if the wormhole objects and graph are out of sync
    if is_dirty():
        tidy()
    now = datetime.utcnow()
    # get the last updated time and player
    lasteditdict = util.get_last_update()
    last_update_diff, last_update_user = util.get_time_difference_formatted(lasteditdict['time'].replace(tzinfo=None), now), lasteditdict['user']
    uptodatedict = util.get_last_up_to_date()
    last_up_to_date_diff, last_up_to_date_user = util.get_time_difference_formatted(uptodatedict['time'].replace(tzinfo=None), now), uptodatedict['user']
    return render(request, 'sitemngr/index.html', {'maxTimers': maxTimers, 'displayname': util.get_display_name(eveigb, request), 'homepage': True, 'homesystem': appSettings.HOME_SYSTEM, \
        'sites': sites, 'wormholes': wormholes, 'status': 'open', 'notices': notices, 'newTab': util.get_settings(util.get_display_name(eveigb, request)).editsInNewTabs, 'backgroundimage': util.get_settings(util.get_display_name(eveigb, request)).userBackgroundImage, \
        'flag': note, 'last_update_diff': last_update_diff, 'last_update_user': last_update_user, 'last_up_to_date_diff': last_up_to_date_diff, 'last_up_to_date_user': last_up_to_date_user})

def view_all(request):
    """ Index page, but with the closed objects instead of the open """
    eveigb = IGBHeaderParser(request)
    if not util.can_view(eveigb, request):
        return no_access(request)
    sites = Site.objects.filter(closed=True)
    wormholes = Wormhole.objects.filter(closed=True)
    return render(request, 'sitemngr/index.html', {'displayname': util.get_display_name(eveigb, request), 'sites': sites, 'wormholes': wormholes, 'status': 'closed'})

def add(request):
    """
        Landing page for adding to the database - only used for clarification from
            the user after using the paste page
    """
    eveigb = IGBHeaderParser(request)
    if not util.can_view(eveigb, request):
        return no_access(request)
    scanid = ''
    if request.method == 'GET':
        g = request.GET
        if g.has_key('scanid') and g['scanid']:
            scanid = g['scanid']
    return render(request, 'sitemngr/add.html', {'displayname': util.get_display_name(eveigb, request), 'scanid': scanid})

# ==============================
#     Site
# ==============================

def view_site(request, siteid):
    """ Views all the data on a particular site, including a list of snapshots """
    eveigb = IGBHeaderParser(request)
    if not util.can_view(eveigb, request):
        return no_access(request)
    site = get_object_or_404(Site, pk=siteid)
    snapshots = site.get_snapshots()
    return render(request, 'sitemngr/viewsite.html', {'displayname': util.get_display_name(eveigb, request), 'isForm': False, 'site': site, 'snapshots': snapshots})

def edit_site(request, siteid):
    """ Edit site page for changing data """
    eveigb = IGBHeaderParser(request)
    if not util.can_view(eveigb, request):
        return no_access(request)
    site = get_object_or_404(Site, pk=siteid)
    if request.method == 'POST':
        p = request.POST
        if util.do_edit_site(p, site, util.get_display_name(eveigb, request)):
            return redirect('/sitemngr/')
    return render(request, 'sitemngr/editsite.html', {'displayname': util.get_display_name(eveigb, request), 'isForm': True, 'site': site, 'finish_msg': 'Store changes back into the database:'})

def add_site(request):
    """ Add a site to the databse """
    eveigb = IGBHeaderParser(request)
    if not util.can_view(eveigb, request):
        return no_access(request)
    g_scanid = None
    g_system = None
    g_type = None
    g_name = None
    now = datetime.utcnow()
    if request.method == 'POST':
        p = request.POST
        s_scanid = p['scanid'].upper()
        s_name = p['name'] if 'name' in p else 'Unknown'
        s_type = p['type']
        s_where = p['where'] if 'where' in p else 'Unknown'
        s_opened = True if 'opened' in p else False
        s_closed = True if 'closed' in p else False
        s_notes = p['notes'] if 'notes' in p else ''
        try:
            # check for the same site already in the database and unclosed
            Site.objects.get(scanid=s_scanid, where=s_where, type=s_type, name=s_name)
            messages.add_message(request, messages.INFO, 'That exact site already exists in the database! You can use the masterlist page to find it.')
            return redirect('/sitemngr/')
        except Site.DoesNotExist:
            pass
        site = Site(name=s_name, scanid=s_scanid, type=s_type, where=s_where, creator=util.get_display_name(eveigb, request), date=now, opened=s_opened, closed=s_closed, notes=s_notes)
        site.save()
        # return the user to the appropriate page, depending on their user settings
        if util.get_settings(util.get_display_name(eveigb, request)).storeMultiple:
            return render(request, 'sitemngr/addsite.html', {'displayname': util.get_display_name(eveigb, request), 'isForm': True,
                 'message': 'Successfully stored the data into the database.', 'finish_msg': 'Store new site into the database:', 'timenow': now.strftime('%m/%d @ %H:%M')})
        else:
            return redirect('/sitemngr/')
    # fill in passed information from the paste page
    elif request.method == 'GET':
        g = request.GET
        g_scanid = g['scanid'] if 'scanid' in g else None
        g_system = g['system'] if 'system' in g else None
        g_type = g['type'] if 'type' in g else None
        g_name = g['name'] if 'name' in g else None
    return render(request, 'sitemngr/addsite.html', {'request': request, 'displayname': util.get_display_name(eveigb, request),
             'isForm': True, 'finish_msg': 'Store new site into the database:', 'g_scanid': g_scanid, 'g_system': g_system, 'g_type': g_type, 'g_name': g_name, 'timenow': now})

# ==============================
#     Wormhole
# ==============================

def view_wormhole(request, wormholeid):
    """ Views all the data on a particular wormhole, including a list of snapshots """
    eveigb = IGBHeaderParser(request)
    if not util.can_view(eveigb, request):
        return no_access(request)
    wormhole = get_object_or_404(Wormhole, pk=wormholeid)
    snapshots = wormhole.get_snapshots()
    return render(request, 'sitemngr/viewwormhole.html', {'displayname': util.get_display_name(eveigb, request), 'isForm': False, 'wormhole': wormhole, 'snapshots': snapshots})

def edit_wormhole(request, wormholeid):
    """ Edit wormhole page for changing data """
    eveigb = IGBHeaderParser(request)
    if not util.can_view(eveigb, request):
        return no_access(request)
    wormhole = get_object_or_404(Wormhole, pk=wormholeid)
    if request.method == 'POST':
        p = request.POST
        if util.do_edit_wormhole(p, wormhole, util.get_display_name(eveigb, request)):
            set_dirty()
            return redirect('/sitemngr/')
    return render(request, 'sitemngr/editwormhole.html', {'displayname': util.get_display_name(eveigb, request), 'isForm': True,
          'wormhole': wormhole, 'finish_msg': 'Store changes back into the database'})

def add_wormhole(request):
    """ Add a wormhole to the databse """
    eveigb = IGBHeaderParser(request)
    if not util.can_view(eveigb, request):
        return no_access(request)
    g_scanid = ''
    g_start = ''
    g_end = ''
    g_name = ''
    now = datetime.utcnow()
    if request.method == 'POST':
        p = request.POST
        s_scanid = p['scanid'].upper()
        s_start = p['start'] if 'start' in p else 'Unknown'
        s_destination = p['destination'] if 'destination' in p else 'Unknown'
        s_status = p['status']
        s_opened = True if 'opened' in p else False
        s_closed = True if 'closed' in p else False
        s_notes = p['notes'] if 'notes' in p else ''
        try:
            # check for the same wormhole already in the database and unclosed
            Wormhole.objects.get(start=s_start, destination=s_destination, opened=True, closed=False)
            messages.add_message(request, messages.INFO, 'That exact wormhole already exists in the database! You can use the masterlist page to find it.')
            return redirect('/sitemngr/')
        except Wormhole.DoesNotExist:
            pass
        wormhole = Wormhole(creator=util.get_display_name(eveigb, request), date=now, scanid=s_scanid, start=s_start, destination=s_destination,
                            status=s_status, opened=s_opened, closed=s_closed, notes=s_notes)
        wormhole.save()
        # make the new view of the index page update the graph
        set_dirty()
        # return the user to the appropriate page, depending on their user settings
        if util.get_settings(util.get_display_name(eveigb, request)).storeMultiple:
            return render(request, 'sitemngr/addwormhole.html', {'request': request, 'displayname': util.get_display_name(eveigb, request),
                    'isForm': True, 'message': 'Successfully stored the data into the database.', 'finish_msg': 'Store new site into database:', 'timenow': now.strftime('%m/%d @ %H:%M')})
        else:
            return redirect('/sitemngr/')
    # fill in passed information from the paste page
    elif request.method == 'GET':
        g = request.GET
        g_scanid = g['scanid'] if 'scanid' in g else None
        g_start = g['start'] if 'start' in g else None
        g_end = g['end'] if 'end' in g else None
        g_name = g['name'] if 'name' in g else None
    return render(request, 'sitemngr/addwormhole.html', {'request': request, 'displayname': util.get_display_name(eveigb, request),
                 'isForm': True, 'finish_msg': 'Store new wormhole into the database:', 'g_scanid': g_scanid, 'g_start': g_start, 'g_end': g_end, 'g_name': g_name, 'timenow': now.strftime('%m/%d @ %H:%M')})

# ==============================
#     Pastes
# ==============================

def paste(request):
    """
        Allow players to paste data from their system scanner into a
        textarea and submit for automatic review.
    """
    eveigb = IGBHeaderParser(request)
    if not util.can_view(eveigb, request):
        return no_access(request)
    now = datetime.utcnow()
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
                data = util.p_get_all_data(line)
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
                    paste_data.append(util.PasteMatch(scanid=site.scanid, name=site.name, p_type='anom', allowed=[a + ': ' + names[a] for a in new_anoms] if len(exact_matches) == 0 else [e + ':' + names[e] for e in exact_matches]))
                else:
                    paste_data.append(util.PasteMatch(scanid=site.scanid, name=site.name, p_type='site', allowed=[s + ': ' + names[s] for s in new_sites] if len(exact_matches) == 0 else [e + ':' + names[e] for e in exact_matches]))
            allWormholes = Wormhole.objects.filter(start=system, closed=False)
            if len(new_wormholes) > 0:
                for wormhole in allWormholes:
                    wormholes.append(wormhole)
                    paste_data.append(util.PasteMatch(scanid=wormhole.scanid, name='%s > %s' % (wormhole.start, wormhole.destination), p_type='wormhole', allowed=new_wormholes))
            else:
                for wormhole in allWormholes:
                    wormholes.append(wormhole)
                    paste_data.append(util.PasteMatch(scanid=wormhole.scanid, name='%s > %s' % (wormhole.start, wormhole.destination), p_type='wormhole', allowed=new_sites))
            for a in new_anoms:
                newids.append(util.SpaceObject(a, 'Anomaly', names[a]))
            for s in new_sites:
                newids.append(util.SpaceObject(s, 'Signature', names[s]))
            for w in new_wormholes:
                newids.append(util.SpaceObject(w, 'Wormhole', ''))
            return render(request, 'sitemngr/pastescandowntime.html', {'system': system, 'pastedata': paste_data, 'sites': sites, 'wormholes': wormholes, 'newids': newids,
                           'displayname': util.get_display_name(eveigb, request), 'newTab': util.get_settings(util.get_display_name(eveigb, request)).editsInNewTabs, 'backgroundimage': util.get_settings(util.get_display_name(eveigb, request)).userBackgroundImage})
        elif post.has_key('afterdowntime') and post['afterdowntime']:
            # After downtime paste page after submitting database changes
            PasteUpdated(user=util.get_display_name(eveigb, request), date=datetime.utcnow()).save()
            for k, v in post.iteritems():
                if ' ' in k:
                    k = k.split(' ')[0]
                if ':' in v:
                    v = v.split(':')[0]
                if k == 'csrfmiddlewaretoken' or k == 'afterdowntime':
                    continue
                if v == '-IGNORE-':
                    continue
                if util.is_site(k):
                    site = util.get_site(k)
                    util.snapshot(site).save()
                    if v == '-CLOSE-':
                        site.closed = True
                        site.save()
                    else:
                        site.scanid = v
                else:
                    wormhole = util.get_wormhole(k)
                    util.snapshot(wormhole).save()
                    if v == '-CLOSE-':
                        wormhole.closed = True
                        wormhole.save()
                    else:
                        wormhole.scanid = v
                        wormhole.save()
            set_dirty()
            return redirect('/sitemngr/')
        else:
            # Parse data to return to normal paste page
            if 'pastedata' in post and post['pastedata'] and 'system' in post and post['system']:
                PasteUpdated(user=util.get_display_name(eveigb, request), date=datetime.utcnow()).save()
                present = []
                findnew = []
                notfound = []
                paste = post['pastedata']
                system = post['system']
                notfound.extend(Site.objects.filter(where=system, closed=False))
                notfound.extend(Wormhole.objects.filter(start=system, closed=False))
                for line in paste.split('\n'):
                    found = False
                    newP = util.PasteData(p_system=system)
                    data = util.p_get_all_data(line)
                    newP.isSite = True if data['issite'] else False
                    newP.isWormhole = True if data['iswormhole'] else False
                    newP.scanid = data['scanid']
                    newP.type = data['type']
                    newP.name = data['name']
                    if util.is_site(newP.scanid):
                        site = util.get_site(newP.scanid)
                        if site.where == system and not site.closed:
                            # Should not have to call this
                            if site in notfound:
                                notfound.remove(site)
                            found = True
                            present.append(site)
                    elif util.is_wormhole(newP.scanid):
                        wormhole = util.get_wormhole(newP.scanid)
                        if wormhole.start == system and not wormhole.closed:
                            # Should not have to call this
                            if wormhole in notfound:
                                notfound.remove(wormhole)
                            found = True
                            present.append(wormhole)
                    if not found:
                        findnew.append(newP)
                return render(request, 'sitemngr/pastescan.html', {'displayname': util.get_display_name(eveigb, request), 'raw': post['pastedata'],
                               'present': present, 'notfound': notfound, 'findnew': findnew, 'timenow': now, 'system': system, 'newTab': util.get_settings(util.get_display_name(eveigb, request)).editsInNewTabs, 'backgroundimage': util.get_settings(util.get_display_name(eveigb, request)).userBackgroundImage})
    # Base request - show the base pastescan page
    return render(request, 'sitemngr/pastescan.html', {'displayname': util.get_display_name(eveigb, request), 'timenow': now, 'newTab': util.get_settings(util.get_display_name(eveigb, request)).editsInNewTabs, 'backgroundimage': util.get_settings(util.get_display_name(eveigb, request)).userBackgroundImage})


# ==============================
#     Systems
# ==============================

def system_landing(request):
    """ Return a list of a systems with active sites """
    eveigb = IGBHeaderParser(request)
    if not util.can_view(eveigb, request):
        return no_access(request)
    now = datetime.utcnow()
    systems = []
    for site in Site.objects.filter(closed=False):
        if not site.where in systems:
            systems.append(site.where)
    for wormhole in Wormhole.objects.filter(closed=False):
        if not wormhole.start in systems:
                systems.append(wormhole.start)
        if not wormhole.destination in systems:
            systems.append(wormhole.destination)
    return render(request, 'sitemngr/systemlanding.html', {'displayname': util.get_display_name(eveigb, request), 'systems': systems, 'timenow': now})

def system(request, systemid):
    """
        Show all wormholes into and out of this system.
        Also show all closed wormholes in this system in the last 10 (configurable) days.
    """
    eveigb = IGBHeaderParser(request)
    if not util.can_view(eveigb, request):
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
        util.get_wormhole_class(systemid)
    # otherwise, it has a security level
    else:
        try:
            security = 2
            is_kspace = True
        except System.DoesNotExist:
                pass
    is_in_chain = util.is_system_in_chain(systemid)
    closest_chain = None
    closest_jumps = 5000
    # determine closest chain system to this
    if is_kspace and util.is_system(systemid):
        for chain in util.get_chain_systems():
            if not util.is_system(chain):
                continue
            if not util.is_system_kspace(chain):
                continue
            jumps = util.get_jumps_between(chain, systemid)
            if jumps < closest_jumps:
                closest_jumps = jumps
                closest_chain = chain
    else:
        # wormhole class
        try:
            clazz = util.get_wormhole_class(systemid)
        except:
            pass
    kills_npc = kills_ship = kills_pod = 0
    kills = evemap.kills_by_system()[0]
    for k in kills.iteritems():
        if str(k[0]) == systemid:
            kills_npc = k[1]['faction']
            kills_ship = k[1]['ship']
            kills_pod = k[1]['pod']
    return render(request, 'sitemngr/system.html', {'displayname': util.get_display_name(eveigb, request), 'system': systemid, 'openwormholes': openwormholes, 'closedwormholes': closedwormholes,
                            'class': clazz, 'security': security, 'kspace': is_kspace, 'opensites': opensites, 'unopenedsites': unopenedsites,
                            'is_in_chain': is_in_chain, 'closest_chain': closest_chain, 'closest_jumps': closest_jumps,
                            'kills_npc': kills_npc, 'kills_ship': kills_ship, 'kills_pod': kills_pod})

def get_tradehub_jumps(request, system):
    """ Shows the number of jumps from each tradehub system """
    jumps = []
    for hub in util.get_tradehub_system_names():
        jumps.append([hub, util.get_jumps_between(system, hub)])
    return render(request, 'sitemngr/tradehubjumps.html', dict((x.lower(), y) for x, y in jumps))

# ==============================
#     Reference lookup
# ==============================

def lookup(request, scanid):
    """ Lookup page for finding sites and wormholes by their scanid """
    eveigb = IGBHeaderParser(request)
    if not util.can_view(eveigb, request):
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
    if not util.can_view(eveigb, request):
        return no_access(request)
    sites = Site.objects.all()
    wormholes = Wormhole.objects.all()
    return render(request, 'sitemngr/mastertable.html', {'displayname': util.get_display_name(eveigb, request), 'sites': sites, 'wormholes': wormholes})

def delete_wormhole(request, wormholeid):
    """ Deletes the wormhole and all it's change objects from the database, permanently """
    if not request or not request.user or not request.user.is_staff:
        messages.add_message(request, messages.INFO, 'You do not have access to that page')
        return redirect('/sitemngr/')
    try:
        wormhole = Wormhole.objects.get(id=wormholeid)
        for c in WormholeSnapshot.objects.filter(wormhole=wormhole):
            c.delete()
        wormhole.delete()
        messages.add_message(request, messages.INFO, 'Wormhole and its changes permanently deleted from the database')
        return redirect('/sitemngr/')
    except Wormhole.DoesNotExist:
        messages.add_message(request, messages.INFO, 'Invalid wormhole id number')
        return redirect('/sitemngr/')

# ==============================
#     Data
# ==============================

def changelog(request):
    """ Site changelog """
    eveigb = IGBHeaderParser(request)
    return render(request, 'sitemngr/changelog.html', {'displayname': util.get_display_name(eveigb, request)})

def igb_test(request):
    """ Show all data that the in-game browser can send to a Trusted Site """
    eveigb = IGBHeaderParser(request)
    return render(request, 'sitemngr/igbtest.html', {'displayname': util.get_display_name(eveigb, request)})

def recent_scan_edits(request):
    """ Returns a readout of all recent scanid changes """
    eveigb = IGBHeaderParser(request)
    if not util.can_view(eveigb, request):
        return no_access(request)
    sites = []
    wormholes = []
    count = 0
    for snap in SiteSnapshot.objects.all().order_by('-id'):
        if not snap.site in sites:
            sites.append(snap.site)
            count += 1
        if count == int(appSettings.RECENT_EDITS_LIMIT) + 1:
            break
    count = 0
    for snap in WormholeSnapshot.objects.all().order_by('-id'):
        if not snap.wormhole in wormholes:
            wormholes.append(snap.wormhole)
            count += 1
        if count == int(appSettings.RECENT_EDITS_LIMIT) + 1:
            break
    return render(request, 'sitemngr/recentscanedits.html', {'displayname': util.get_display_name(eveigb, request), 'sites': sites, 'wormholes': wormholes})

# ==============================
#     Output
# ==============================

def output(request):
    """ Output current data for the channel MotD """
    eveigb = IGBHeaderParser(request)
    if not util.can_view(eveigb, request):
        return no_access(request)
    wormholes = Wormhole.objects.filter(closed=False, start=appSettings.HOME_SYSTEM)
    motd = str(appSettings.HOME_SYSTEM) + ' Intel Channel\nWormholes:\n'
    for w in wormholes:
        motd += w.printOut() + '\n'
    motd += 'Signatures:\n'
    for site in Site.objects.filter(closed=False, where=str(appSettings.HOME_SYSTEM)):
        motd += site.printOut() + '\n'
    return render(request, 'sitemngr/output.html', {'displayname': util.get_display_name(eveigb, request), 'motd': motd})

def stats(request):
    """ Returns usage statistics """
    eveigb = IGBHeaderParser(request)
    if not util.can_view(eveigb, request):
        return no_access(request)
    numSites = Site.objects.count()
    numWormholes = Wormhole.objects.count()
    numEdits = SiteSnapshot.objects.count() + WormholeSnapshot.objects.count()
    numPastes = PasteUpdated.objects.count()
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
    for snap in SiteSnapshot.objects.all():
        if snap.user in con:
            con[snap.user] += 1
        else:
            con[snap.user] = 1
    for snap in WormholeSnapshot.objects.all():
        if snap.user in con:
            con[snap.user] += 1
        else:
            con[snap.user] = 1
    for paste in PasteUpdated.objects.all():
        if paste.user in con:
            con[paste.user] += 1
        else:
            con[paste.user] = 1
    numContributors = len(con)
    conList = []
    con = sorted(con.items(), key=lambda kv: kv[1])
    for name, count in con:
        conList.append(util.Contributor(name, count))
    return render(request, 'sitemngr/stats.html', {'displayname': util.get_display_name(eveigb, request), 'numSites': numSites,
               'numWormholes': numWormholes, 'numPastes': numPastes, 'numEdits': numEdits, 'numContributors': numContributors, 'allContributors': conList})

def check_kills(request):
    """ Returns a readout of all ship and pod kills in and system with open objects """
    eveigb = IGBHeaderParser(request)
    if not util.can_view(eveigb, request):
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
            retSys.append(util.get_system_ID(system))
        kills = evemap.kills_by_system()[0]
        for k in kills.iteritems():
            if k[0] in retSys:
                r = util.KillReport(system=util.get_system_name(k[0]), systemid=k[0], npc=k[1]['faction'], ship=k[1]['ship'], pod=k[1]['pod'])
                reports.append(r)
    return render(request, 'sitemngr/checkkills.html', {'displayname': util.get_display_name(eveigb, request), 'systems': systems, 'reports': reports})

def view_help(request):
    """ Help/instructions page """
    eveigb = IGBHeaderParser(request)
    return render(request, 'sitemngr/help.html', {'displayname': util.get_display_name(eveigb, request), 'able': util.can_view(eveigb, request)})

def overlay(request):
    """ Return a wealth of quickly-viewed information to be presented to on the idnex page """
    eveigb = IGBHeaderParser(request)
    if not util.can_view(eveigb, request):
        return no_access(request)
    data = ''
    # if the c2 static is open
    c2_open = False
    # list of highsec systems in the chain
    hs = []
    # closest chain system to jita
    jita_closest = None
    jita_jumps = 5000
    least = 5000
    # if the user is in-game, then get their current position
    home_system = appSettings.HOME_SYSTEM
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
                jumps = util.get_jumps_between(system, current_system)
                if jumps < closest_jumps:
                    closest_in = system
                    closest_jumps = jumps
    # look for an open c2 connection, and all highsec systems in the chain
    for wormhole in Wormhole.objects.filter(opened=True, closed=False):
        if not wormhole.destination.lower() in ['', ' ', 'closed', 'unopened', 'unknown']:
            if re.match(r'^J\d{6}$', wormhole.destination):
                if wormhole.start == home_system:
                    if not wormhole.destination.lower() in ['', ' ', 'closed', 'unopened', 'unknown']:
                        if re.match(r'^J\d{6}$', wormhole.destination):
                            if util.get_wormhole_class(wormhole.destination) == '2':
                                # we know that we have a connection to a C2
                                c2_open = True
                continue
            if not util.is_system(wormhole.destination):
                continue
            # determine if this system is the closest to Jita
            jumps = util.get_jumps_between('Jita', wormhole.destination)
            if int(jumps) < least:
                least = int(jumps)
                jita_closest = wormhole.destination
                jita_jumps = jumps
            # ensure that the system is actually in Eve, and not a user typo
            try:
                obj = System.objects.get(name=wormhole.destination)
                status = obj.security_level
                if status > 0.45:
                    hs.append(wormhole.destination)
            except System.DoesNotExist:
                continue
    # kills in the home system
    kills_npc = kills_ship = kills_pod = 0
    kills = evemap.kills_by_system()[0]
    for k in kills.iteritems():
        if str(k[0]) == appSettings.HOME_SYSTEM_ID:
            kills_npc = k[1]['faction']
            kills_ship = k[1]['ship']
            kills_pod = k[1]['pod']
    return render(request, 'sitemngr/overlay.html', {'displayname': util.get_display_name(eveigb, request), 'home_system': home_system, 'current_system': current_system, 'is_in_kspace': is_in_kspace, 'is_in_chain_system': is_in_chain_system,
                     'c2_open': c2_open, 'hs': hs, 'jita_closest': jita_closest, 'jita_jumps': jita_jumps, 'closest_in': closest_in, 'closest_jumps': closest_jumps,
                     'kills_npc': kills_npc, 'kills_ship': kills_ship, 'kills_pod': kills_pod, 'data': data})

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
                    return redirect('/sitemngr/')
                else:
                    messages.add_message(request, messages.INFO, 'That account is disabled')
                    return redirect('/sitemngr/')
            else:
                messages.add_message(request, messages.INFO, 'An error occurred when logging in - check your username and password')
                return redirect('/sitemngr/')
        else:
            messages.add_message(request, messages.INFO, 'You must enter both a username and a password')
            return redirect('/sitemngr/')
    return render(request, 'sitemngr/login.html', {'note': note, 'displayname': util.get_display_name(IGBHeaderParser(request), request)})

def logout_page(request):
    """ If the user is logged into an account, they are logged off """
    logout(request)
    return redirect('/sitemngr/')

def create_account(request):
    """
        Create an account on the server
        Must be done from the in-game browser
    """
    if request.method == 'POST':
        eveigb = IGBHeaderParser(request)
        if not util.can_view(eveigb):
            return no_access(request)
        try:
            if User.objects.get(username__exact=eveigb.charname):
                messages.add_message(request, messages.INFO, 'You already have an account on this server')
                return redirect('/sitemngr/')
        except User.DoesNotExist:
            pass
        p = request.POST
        if p['password']:
            user = User.objects.create_user(username=eveigb.charname, password=p['password'])
            user.save()
            # messages.add_message(request, messages.INFO, 'Successfully created account on the server')
            return redirect('/sitemngr/')
        return login_page(request, 'You must enter a password.')
    return redirect('/sitemngr/')

def settings(request):
    """ Settings page for viewing and changing user settings """
    eveigb = IGBHeaderParser(request)
    if not util.can_view(eveigb, request):
        return no_access(request)
    message = None
    try:
        settings = Settings.objects.get(user=util.get_display_name(eveigb, request))
    except Settings.DoesNotExist:
        settings = Settings(user=util.get_display_name(eveigb, request), editsInNewTabs=True, storeMultiple=True)
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
    return render(request, 'sitemngr/settings.html', {'displayname': util.get_display_name(eveigb, request), 'edit': edit, 'store': store, 'image': image, 'message': message})

def get_search_results(request, keyword, flags):
    """ Returns a list of links for use by the search feature on the index page """
    flags = util.Flag(flags)
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
        for system in util.get_chain_systems():
            if system.startswith(keyword) and not system in raw:
                ret.append(util.Result('system/%s' % system, system))
                raw.append(system)
        # check tradehub system names
        if flags.universe and not flags.chain:
            for system in util.get_tradehub_system_names():
                if system.startswith(keyword) and not system in raw:
                    ret.append(util.Result('system/%s' % system, system))
    # check site names and locations, and scanids
    for site in sites:
        if site.where.startswith(keyword) or site.name.startswith(keyword) or site.scanid.startswith(keyword) or site.scanid == keyword:
            ret.append(util.Result('viewsite/%s' % site.id, 'Site %s' % site))
            raw.append(site)
    # check wormhole start and destination system names, and scanids
    for wormhole in wormholes:
        if wormhole.start.startswith(keyword) or wormhole.destination.startswith(keyword) or wormhole.scanid.startswith(keyword) or wormhole.scanid == keyword:
            ret.append(util.Result('viewwormhole/%s' % wormhole.id, 'Wormhole %s' % wormhole))
            raw.append(wormhole)
    # if we've found nothing else, then check system names from all of the universe if we can include systems
    if flags.universe or (len(ret) == 0 and not flags.wormholes and not flags.sites and not flags.chain):
        for system in System.objects.all():
            if system.name.startswith(keyword):
                ret.append(util.Result('system/%s' % system.name, system.name))
    if len(ret) == 0:
        ret.append(util.Result('', 'No results'))
    return render(request, 'sitemngr/search_results.html', {'results': ret, 'flags': flags})

def refresh_graph(request):
    """ A simple redirect used for manually refreshing the wormhole chain graph """
    set_dirty()
    return redirect('/sitemngr/')

def mass_close(request):
    """ Close multiple wormholes at once, to be used for deleting entire chains after their connection is set to closed """
    eveigb = IGBHeaderParser(request)
    if not util.can_view(eveigb, request):
        return no_access(request)
    data = ''
    if request.method == 'POST':
        p = request.POST
        for k in p.iterkeys():
            if k == 'csrfmiddlewaretoken':
                continue
            wormhole = Wormhole.objects.get(id=k)
            util.snapshot(wormhole).save()
            wormhole.closed = True
            wormhole.save()
        set_dirty()
    wormholes = Wormhole.objects.filter(closed=False)
    return render(request, 'sitemngr/massclose.html', {'displayname': util.get_display_name(eveigb, request), 'wormholes': wormholes, 'data': data})

@csrf_exempt
def inline_edit_site(request):
    eveigb = IGBHeaderParser(request)
    if not util.can_view(eveigb, request):
        return no_access(request)
    if request.method == 'POST':
        p = request.POST.copy()
        site = get_object_or_404(Site, pk=p['id'])
        p['opened'] = site.opened
        p['closed'] = site.closed
        result = util.do_edit_site(p, site, util.get_display_name(eveigb, request))
        if result:
            return HttpResponse(result)
        else:
            return HttpResponse('Error: Site edit function returned False - no changes made')
    else:
        return HttpResponse('Error: Invalid page access.')

@csrf_exempt
def inline_edit_wormhole(request):
    eveigb = IGBHeaderParser(request)
    if not util.can_view(eveigb, request):
        return no_access(request)
    if request.method == 'POST':
        p = request.POST.copy()
        wormhole = get_object_or_404(Wormhole, pk=p['id'])
        p['opened'] = wormhole.opened
        p['closed'] = wormhole.closed
        result = util.do_edit_wormhole(p, wormhole, util.get_display_name(eveigb, request))
        if result:
            set_dirty()
            return HttpResponse(result)
        else:
            return HttpResponse('Error: Wormhole edit function returned False - no changes made')
    else:
        return HttpResponse('Error: Invalid page access.')

def no_access(request):
    """ Shown when the viewer is restricted from viewing the page """
    eveigb = IGBHeaderParser(request)
    wrongAlliance = util.can_view_wrong_alliance(eveigb)
    return render(request, 'sitemngr/noaccess.html', {'displayname': util.get_display_name(eveigb, request), 'wrongAlliance': wrongAlliance})

def mark_up_to_date(request):
    """ User manually marked the database as up to date """
    eveigb = IGBHeaderParser(request)
    if not util.can_view(eveigb, request):
        return no_access(request)
    DatabaseUpToDate(user=util.get_display_name(eveigb, request), date=datetime.utcnow(), by='Manual').save()
    return redirect('/sitemngr/')
