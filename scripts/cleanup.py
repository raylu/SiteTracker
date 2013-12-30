from sitemngr.models import *
from datetime import tzinfo, timedelta, datetime

class UTC(tzinfo):
    def utcoffset(self, dt):
        return timedelta(0)
    def tzname(self, dt):
        return "UTC"
    def dst(self, dt):
        return timedelta(0)
utc = UTC()
now = datetime.now().replace(tzinfo=utc)

def run():
    cleanup()

def cleanup(offset_days=14):
    print 'Selecting old data'
    sites = []
    sitechanges = []
    wormholes = []
    wormholechanges = []
    for site in Site.objects.filter(closed=True):
        if (now - site.date).days > offset_days:
            sites.append(site)
            for change in SiteChange.objects.filter(site=site):
                if not change in sitechanges:
                    sitechanges.append(change)
    for wormhole in Wormhole.objects.filter(closed=True):
        if (now - wormhole.date).days > offset_days:
            wormholes.append(wormhole)
            for change in WormholeChange.objects.filter(wormhole=wormhole):
                if not change in wormholechanges:
                    wormholechanges.append(change)

    print 'Generating user stats'
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
    for p in PasteUpdated.objects.all():
        if p.user in con:
            con[p.user] += 1
        else:
            con[p.user] = 1
    con = sorted(con.items(), key=lambda kv: kv[1])
    f = open('stats_' + now.strftime('%m.%d.%Y-%H.%M.%S'), 'w')
    for a,b in con:
        f.write('%s %s\n' % (b, a))
    f.write('\nSites: %s\n' % len(Site.objects.all()))
    f.write('SiteChanges: %s\n' % len(SiteChange.objects.all()))
    f.write('Wormholes: %s\n' % len(Wormhole.objects.all()))
    f.write('WormholeChanges: %s\n' % len(WormholeChange.objects.all()))
    f.write('Pastes: %s\n\n' % len(PasteUpdated.objects.all()))

    print 'Deleting old site changes'
    c = deletelist(sitechanges)
    f.write('Deleted %s SiteChanges\n' % c)
    print 'Deleting old sites'
    c = deletelist(sites)
    f.write('Deleted %s Sites\n' % c)
    print 'Deleting old wormhole changes'
    c = deletelist(wormholechanges)
    f.write('Deleted %s WormholeChanges\n' % c)
    print 'Deleting old wormholes'
    c = deletelist(wormholes)
    f.write('Deleted %s Wormholes' % c)
    
    f.close()
    
    print 'Done'

def deletelist(items):
    count = 0
    for i in items:
        i.delete()
        count += 1
        if count % 10 == 0:
            print 'Count = ' + str(count)
    print 'Done, ' + str(count) + ' deleted'
    return count
