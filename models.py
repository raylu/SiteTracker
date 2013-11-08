from django.db import models
import settings

# Site: creator, date, name, scanid, type, where, opened, closed, notes
# SiteChange: site, user, date, changedScanid, changedName, changedType, changedWhere, changedDate, changedOpen, changedClosed, changedNotes
# Wormhole: creator, date, scanid, type, start, destination, time, status, opened, closed, notes
# WormholeChange: wormhole, user, date, changedScanid, changedType, changedStart, changedDestination, changedTime, changedStatus, changedOpened, changedClosed, changedNotes

class Site(models.Model):
    """ Site object for sites in wormhole space """
    # User who entered the site
    creator = models.CharField(max_length=100)
    # When the site was added
    date = models.DateTimeField()
    # Name of the site
    name = models.CharField(max_length=150)
    # Scan id
    scanid = models.CharField(max_length=10)
    # Type of site
    type = models.CharField(max_length=100)
    # Where the site is located
    where = models.CharField(max_length=50)
    # True if the site has been opened
    opened = models.BooleanField(default=False)
    # True if the site is closed (done)
    closed = models.BooleanField(default=False)
    notes = models.TextField()
    def __unicode__(self):
        return unicode('{0}-{1}-{2}'.format(self.id, self.scanid, self.where))
    def numberOfChanges(self):
        return len(SiteChange.objects.filter(site=self.id))
    def getChanges(self):
        return SiteChange.objects.filter(site=self.id)
    # Printout for output into MotD or T2MM
    def printOut(self):
        back = '{0} {1} {2}'.format(self.scanid, self.type, self.name)
        if self.opened:
            back += ' (Open, last updated: {0})'.format(self.date.strftime('%H:%M %m/%d'))
        else:
            back += ' (Closed, last updated: {0})'.format(self.date.strftime('%H:%M %m/%d'))
        return back
    def isAnom(self):
        return self.name in ['Core Garrison', 'Core Stronghold', 'Oruze Osobnyk', 'Quarantine Area']

class SiteChange(models.Model):
    """ SiteChange object for keeping track of changes to sites """
    # Site in question
    site = models.ForeignKey(Site)
    # Date of the change
    date = models.DateTimeField()
    user = models.CharField(max_length=100)
    changedName = models.BooleanField()
    changedScanid = models.BooleanField()
    changedType = models.BooleanField()
    changedWhere = models.BooleanField()
    changedDate = models.BooleanField()
    changedOpened = models.BooleanField()
    changedClosed = models.BooleanField()
    changedNotes = models.BooleanField()
    def __unicode__(self):
        return self.pk

class Wormhole(models.Model):
    """ Wormhole object for wormholes in w-space """
    # User who entered the wormhole
    creator = models.CharField(max_length=100)
    # Date first stored in database
    date = models.DateTimeField()
    # Scan id
    scanid = models.CharField(max_length=10)
    # Type of wormhole (w id)
    type = models.CharField(max_length=50)
    # System where the wormhole was opened
    start = models.CharField(max_length=100)
    # System to where the wormhole leads
    destination = models.CharField(max_length=100)
    # Time of last recording
    time = models.CharField(max_length=150)
    # Status at `time`
    status = models.CharField(max_length=400)
    # True if the wormhole has been opened
    opened = models.BooleanField(default=False)
    # True if the wormhole is closed (done)
    closed = models.BooleanField(default=False)
    notes = models.TextField()
    def __unicode__(self):
        return unicode('{0}-{1}-{2}'.format(self.id, self.scanid, self.start))
    def numberOfChanges(self):
        return len(WormholeChange.objects.filter(wormhole=self.pk))
    def getChanges(self):
        return WormholeChange.objects.filter(wormhole=self.pk)
    # Printout for output into MotD or T2MM
    def printOut(self):
        back = '{0} {1} > {2}'.format(self.scanid, self.start, self.destination)
        if self.opened:
            back += ' (Open, last updated: {0}, status: {1})'.format(self.time, self.status)
        else:
            back += ' (Closed)'
        return back
    def printOutT2MM(self):
        return '{0} {1} > {2}'.format(self.scanid, self.start, self.destination)

class WormholeChange(models.Model):
    """ WormholeChange object for keeping track of changes to wormholes """
    # Wormhole in question
    wormhole = models.ForeignKey(Wormhole)
    # Date of the change
    user = models.CharField(max_length=100)
    date = models.DateTimeField()
    changedScanid = models.BooleanField()
    changedType = models.BooleanField()
    changedStart = models.BooleanField()
    changedDestination = models.BooleanField()
    changedTime = models.BooleanField()
    changedStatus = models.BooleanField()
    changedOpened = models.BooleanField()
    changedClosed = models.BooleanField()
    changedNotes = models.BooleanField()
    def __unicode__(self):
        return self.pk

class Settings(models.Model):
    user = models.CharField(max_length=100)
    editsInNewTabs = models.BooleanField(default=True)
    storeMultiple = models.BooleanField(default=True)
    userBackgroundImage = models.BooleanField(default=True)
    def __unicode__(self):
        return unicode(self.user)

class Chain(models.Model):
    """
        Chains of wormholes and k-space jumps
        'jumpCodes' are -1 for k-space jumpgates and the id of
            the wormhole
    """
    name = models.CharField(max_length=300)
    start = models.CharField(max_length=50)
    end = models.CharField(max_length=50)
    jumps = models.TextField()
    def addJump(self, jumpCode, nextSystem):
        if self.jumps == '':
            self.jumps = '{0}>{1}'.format(jumpCode, nextSystem)
        else:
            self.jumps += ',{0}>{1}'.format(jumpCode, nextSystem)
    def __unicode__(self):
        return unicode('{0}-{1}-{2}'.format(self.name, self.start, self.end))

class Whitelisted(models.Model):
    """ Whitelisted character names for out-of-alliance alts """
    name = models.CharField(max_length=100)
    inAllianceName = models.CharField(max_length=100)
    addedDate = models.DateTimeField('added', blank=True, null=True)
    whitelistedBy = models.CharField(max_length=100, blank=True, null=True)
    whitelistedDate = models.DateTimeField('whitelisted', blank=True, null=True)
    active = models.BooleanField(default=False)
    notes = models.TextField(blank=True, null=True)

class UpdateData(models.Model):
    """ Should update graphs? """
    note = models.TextField(blank=True, null=True)

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
        return unicode(self.scanid)

class PasteMatch:
    def __init__(self, scanid, p_type, allowed):
        self.scanid = scanid
        self.p_type = p_type
        self.allowed = allowed
    def __unicode__(self):
        return unicode(self.scanid)

class KillReport:
    """ Dynamically constructed class sent to /sitemngr/checkkills """
    def __init__(self, system=settings.HOME_SYSTEM, systemid=settings.HOME_SYSTEM_ID, ship=0, pod=0):
        self.system = system
        self.systemid = systemid
        self.ship = ship
        self.pod = pod
    def __unicode__(self):
        return unicode(self.system)
