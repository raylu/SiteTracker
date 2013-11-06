from django.conf import settings

HOME_SYSTEM = getattr(settings, 'SITEMNGR_HOME_SYSTEM', 'Jita')
HOME_SYSTEM_ID = getattr(settings, 'SITEMNGR_HOME_SYSTEM_ID', '30000142')
ALLIANCE_NAME = getattr(settings, 'SITEMNGR_ALLIANCE_NAME', 'Ocularis Inferno')
RECENT_EDITS_LIMIT = getattr(settings, 'SITEMNGR_RECENT_EDITS_LIMIT', 25)