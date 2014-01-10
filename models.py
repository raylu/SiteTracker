from django.db import models

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
    def printOut(self):
        return '{0} [{1}] {2} - {3}'.format(self.scanid, self.type[0], self.name, 'Open' if self.opened else 'Closed')
    def isAnom(self):
        return self.name in ['Average Frontier Deposit', 'Exceptional Core Deposit', 'Unexceptional Frontier Reservoir', 'Ordinary Permiter Deposit', 'Core Garrison', 'Core Stronghold', 'Oruze Osobnyk', 'Quarantine Area', 'Ordinary Perimeter Deposit', 'Rarified Core Deposit', 'Unexceptional Frontier Deposit']
    def get_snapshots(self):
        return SiteSnapshop.objects.filter(site=self.id)

class SiteSnapshop(models.Model):
    """ A snapshot of a Site object, used for recording changes in data """
    site = models.ForeignKey(Site)
    date = models.DateTimeField(blank=False, default=False)
    user = models.CharField(max_length=100, blank=False, default=False)
    scanid = models.CharField(max_length=10, blank=False)
    type = models.CharField(max_length=100, blank=False)
    where = models.CharField(max_length=50, blank=False)
    opened = models.BooleanField(default=False, blank=False)
    closed = models.BooleanField(default=False, blank=False)
    notes = models.TextField(blank=True)
    def __repr__(self):
        return '<SiteSnapshop-%s-%s>' % (self.id, self.site.id)

class Wormhole(models.Model):
    """ Wormhole object for wormholes in w-space """
    creator = models.CharField(max_length=100)
    date = models.DateTimeField()
    scanid = models.CharField(max_length=10)
    start = models.CharField(max_length=100)
    destination = models.CharField(max_length=100)
    time = models.CharField(max_length=150)
    status = models.CharField(max_length=400)
    opened = models.BooleanField(default=False)
    closed = models.BooleanField(default=False)
    notes = models.TextField()
    def __repr__(self):
        return '<Wormhole-%s-%s-%s-%s-%s>' % (self.id, self.scanid, self.start, self.destination, self.status)
    def printOut(self):
        return '{0} {1} > {2} ({3})'.format(self.scanid, self.start, self.destination, self.status)

class WormholeSnapshot(models.Model):
    """ A snapshot of a Wormhole object, used for recording changes in data """
    wormhole = models.ForeignKey(Wormhole)
    date = models.DateTimeField()
    scanid = models.CharField(max_length=10)
    start = models.CharField(max_length=100)
    destination = models.CharField(max_length=100)
    time = models.CharField(max_length=150)
    status = models.CharField(max_length=400)
    opened = models.BooleanField(default=False)
    closed = models.BooleanField(default=False)
    notes = models.TextField()
    def __repr__(self):
        return '<WormholeSnapshot-%s-%s>' % (self.id, self.wormhole.id)

class Settings(models.Model):
    user = models.CharField(max_length=100)
    editsInNewTabs = models.BooleanField(default=True)
    storeMultiple = models.BooleanField(default=True)
    userBackgroundImage = models.BooleanField(default=True)
    def __repr__(self):
        return '<Settings-%s>' % self.user

class PasteUpdated(models.Model):
    """ Recording when someone uses the paste feature """
    user = models.CharField(max_length=100)
    date = models.DateTimeField()
    def __repr__(self):
        return '<PasteUpdated-%s>' % self.user
