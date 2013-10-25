from django.contrib import admin
from sitemngr.models import Site, SiteChange, Wormhole, WormholeChange, Settings, Whitelisted

class SiteManager(admin.ModelAdmin):
    fields = ['creator', 'name', 'scanid', 'type', 'where', 'date', 'opened', 'closed', 'notes']
    list_display = ['name', 'scanid', 'type', 'where', 'creator', 'date', 'opened', 'closed']

class SiteChangeManager(admin.ModelAdmin):
    fields = ['user', 'site', 'date', 'changedScanid', 'changedName', 'changedType', 'changedWhere', 'changedDate', 'changedOpened', 'changedClosed', 'changedNotes']
    list_display = ['user', 'site', 'date']

class WormholeManager(admin.ModelAdmin):
    fields = ['creator', 'date', 'scanid', 'type', 'start', 'destination', 'time', 'status', 'opened', 'closed']
    list_display = ['creator', 'date', 'scanid', 'type', 'start', 'destination', 'opened', 'closed']

class WormholeChangeManager(admin.ModelAdmin):
    fields = [ 'user', 'wormhole', 'date', 'changedScanid', 'changedType', 'changedStart', 'changedDestination', 'changedTime', 'changedStatus', 'changedOpened', 'changedClosed', 'changedNotes']
    list_display = [ 'user', 'wormhole', 'date']

class SettingsManager(admin.ModelAdmin):
    fields = ['user', 'editsInNewTabs', 'storeMultiple']
    list_display = ['user', 'editsInNewTabs', 'storeMultiple']

class WhitelistedManager(admin.ModelAdmin):
    fields = ['name', 'inAllianceName', 'addedDate', 'whitelistedBy', 'whitelistedDate', 'active', 'notes']
    list_display = ['name', 'inAllianceName', 'whitelistedBy', 'active']

admin.site.register(Site, SiteManager)
admin.site.register(SiteChange, SiteChangeManager)
admin.site.register(Wormhole, WormholeManager)
admin.site.register(WormholeChange, WormholeChangeManager)
admin.site.register(Settings, SettingsManager)
admin.site.register(Whitelisted, WhitelistedManager)
