from django.db import models
import settings

class Site(models.Model):
    """ Site object for sites in wormhole space """
    creator = models.CharField(max_length=100)
    date = models.DateTimeField()
    name = models.CharField(max_length=150, blank=False)
    scanid = models.CharField(max_length=10, blank=False)
    type = models.CharField(max_length=100, blank=False)
    where = models.CharField(max_length=50, blank=False)
    opened = models.BooleanField(default=False, blank=False)
    closed = models.BooleanField(default=False, blank=False)
    notes = models.TextField(blank=True)
    def __repr__(self):
        return '<Site-%s-%s-%s>' % (self.id, self.scanid, self.where)
    def __unicode__(self):
        return '<Site-%s-%s-%s>' % (self.id, self.scanid, self.where)
    def numberOfChanges(self):
        return len(SiteChange.objects.filter(site=self.id))
    def getChanges(self):
        return SiteChange.objects.filter(site=self.id)
    def printOut(self):
        return '{0} [{1}] {2} - {3}'.format(self.scanid, self.type[0], self.name, 'Open' if self.opened else 'Closed')
    def isAnom(self):
        return self.name in ['Average Frontier Deposit', 'Exceptional Core Deposit', 'Unexceptional Frontier Reservoir', 'Ordinary Permiter Deposit', 'Core Garrison', 'Core Stronghold', 'Oruze Osobnyk', 'Quarantine Area', 'Ordinary Perimeter Deposit', 'Rarified Core Deposit', 'Unexceptional Frontier Deposit']

class SiteChange(models.Model):
    """ SiteChange object for keeping track of changes to sites """
    site = models.ForeignKey(Site)
    date = models.DateTimeField(blank=False, default=False)
    user = models.CharField(max_length=100, blank=False, default=False)
    changedName = models.BooleanField(blank=False, default=False)
    changedScanid = models.BooleanField(blank=False, default=False)
    changedType = models.BooleanField(blank=False, default=False)
    changedWhere = models.BooleanField(blank=False, default=False)
    changedDate = models.BooleanField(blank=False, default=False)
    changedOpened = models.BooleanField(blank=False, default=False)
    changedClosed = models.BooleanField(blank=False, default=False)
    changedNotes = models.BooleanField(blank=False, default=False)
    def __repr__(self):
        return '<SiteChange-%s-%s-%s>' % (self.id, self.site.id, self.date.strftime('%m/%d/%Y %H:%M:%S'))
    def __unicode__(self):
        return '<SiteChange-%s-%s-%s>' % (self.id, self.site.id, self.date.strftime('%m/%d/%Y %H:%M:%S'))

class Wormhole(models.Model):
    """ Wormhole object for wormholes in w-space """
    creator = models.CharField(max_length=100)
    date = models.DateTimeField()
    scanid = models.CharField(max_length=10)
    type = models.CharField(max_length=50)
    start = models.CharField(max_length=100)
    destination = models.CharField(max_length=100)
    time = models.CharField(max_length=150)
    status = models.CharField(max_length=400)
    opened = models.BooleanField(default=False)
    closed = models.BooleanField(default=False)
    notes = models.TextField()
    def __repr__(self):
        return '<Wormhole-%s-%s-%s-%s-%s>' % (self.id, self.scanid, self.start, self.destination, self.status)
    def __unicode__(self):
        return '<Wormhole-%s-%s-%s-%s-%s>' % (self.id, self.scanid, self.start, self.destination, self.status)
    def numberOfChanges(self):
        return len(WormholeChange.objects.filter(wormhole=self.pk))
    def getChanges(self):
        return WormholeChange.objects.filter(wormhole=self.pk)
    # Printout for output into MotD or T2MM
    def printOut(self):
        return '{0} {1} > {2} ({3})'.format(self.scanid, self.start, self.destination, self.status)
    def get_status_colored(self):
        if self.status in ['Fresh', 'Undecayed']:
            return "<span color='green'>%s</span>" % self.status
        elif self.status in ['< 50% mass', '< 50% time', 'Unknown']:
            return "<span color='orange'>%s</span>" % self.status
        else:
            return "<span color='red'>%s</span>" % self.status

class WormholeChange(models.Model):
    """ WormholeChange object for keeping track of changes to wormholes """
    wormhole = models.ForeignKey(Wormhole)
    user = models.CharField(max_length=100)
    date = models.DateTimeField()
    changedScanid = models.BooleanField()
    changedType = models.BooleanField()
    changedStart = models.BooleanField()
    changedDestination = models.BooleanField()
    changedTime = models.BooleanField()
    changedStatus = models.BooleanField()
    changedOpened = models.BooleanField()
    changedClosed = models.BooleanField(blank=False, default=False)
    changedNotes = models.BooleanField(blank=False, default=False)
    def __repr__(self):
        return '<WormholeChange-%s-%s-%s>' % (self.id, self.wormhole.id, self.date.strftime('%m/%d/%Y %H:%M:%S'))
    def __unicode__(self):
        return '<WormholeChange-%s-%s-%s>' % (self.id, self.wormhole.id, self.date.strftime('%m/%d/%Y %H:%M:%S'))

class Settings(models.Model):
    user = models.CharField(max_length=100)
    editsInNewTabs = models.BooleanField(default=True)
    storeMultiple = models.BooleanField(default=True)
    userBackgroundImage = models.BooleanField(default=True)
    def __unicode__(self):
        return '<Settings-%s>' % self.user

class PasteUpdated(models.Model):
    """ Recording when someone uses the paste feature """
    user = models.CharField(max_length=100)
    date = models.DateTimeField()
    def __unicode__(self):
        return '<PasteUpdated-%s>' % self.user

# ========================

class PasteData:
    """ Dynamically constructed class sent to /sitemngr/addsite and  /sitemngr/addwormhole from /sitemngr/paste  """
    def __init__(self, p_scanid='', p_system=str(settings.HOME_SYSTEM), p_name='', p_type='Anomoly', p_isSite=True, p_isWormhole=False):
        self.scanid = p_scanid
        self.system = p_system
        self.name = p_name
        self.type = p_type
        self.isSite = p_isSite
        self.iswormhole = p_isWormhole
    def __unicode__(self):
        return self.scanid

class PasteMatch:
    def __init__(self, scanid, name, p_type, allowed):
        self.scanid = scanid
        self.name = name
        self.p_type = p_type
        self.allowed = allowed
    def __unicode__(self):
        return self.scanid

class KillReport:
    """ Dynamically constructed class sent to /sitemngr/checkkills """
    def __init__(self, system=settings.HOME_SYSTEM, systemid=settings.HOME_SYSTEM_ID, npc=0, ship=0, pod=0):
        self.system = system
        self.systemid = systemid
        self.npc = npc
        self.ship = ship
        self.pod = pod
    def __unicode__(self):
        return self.system
