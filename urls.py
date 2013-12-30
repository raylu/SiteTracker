from django.conf import settings
from django.conf.urls import patterns, url
from django.conf.urls.static import static

urlpatterns = patterns('',
   url(r'^$', 'sitemngr.views.index'),
   url(r'^viewall/', 'sitemngr.views.view_all'),
   url(r'^add/', 'sitemngr.views.add'),
   url(r'^viewsite/(\d+)', 'sitemngr.views.view_site'),
   url(r'^editsite/(\d+)', 'sitemngr.views.edit_site'),
   url(r'^addsite/', 'sitemngr.views.add_site'),
   url(r'^viewwormhole/(\d+)', 'sitemngr.views.view_wormhole'),
   url(r'^editwormhole/(\d+)', 'sitemngr.views.edit_wormhole'),
   url(r'^addwormhole/', 'sitemngr.views.add_wormhole'),
   url(r'^recentscanedits/', 'sitemngr.views.recent_scan_edits'),
   url(r'^paste/', 'sitemngr.views.paste'),
   url(r'^system/([-a-zA-Z0-9 ]+)', 'sitemngr.views.system'),
   url(r'^system/', 'sitemngr.views.system_landing'),
   url(r'^lookup/(\w+)', 'sitemngr.views.lookup'),
   url(r'^igbtest/', 'sitemngr.views.igb_test'),
   url(r'^output/', 'sitemngr.views.output'),
   url(r'^help/', 'sitemngr.views.view_help'),
   url(r'^mastertable/', 'sitemngr.views.mastertable'),
   url(r'^changelog/', 'sitemngr.views.changelog'),
   url(r'^checkkills/', 'sitemngr.views.check_kills'),
   url(r'^stats/', 'sitemngr.views.stats'),
   url(r'^settings/', 'sitemngr.views.settings'),
   url(r'^login/', 'sitemngr.views.login_page'),
   url(r'^logout/', 'sitemngr.views.logout_page'),
   url(r'^create_account/', 'sitemngr.views.create_account'),
   url(r'^overlay/', 'sitemngr.views.overlay'),
   url(r'^get_tradehub_jumps/([-a-zA-Z0-9 ]+)', 'sitemngr.views.get_tradehub_jumps'),
   url(r'^get_search_results/([-a-zA-Z0-9 ]+)/([-a-zA-Z0-9_]+)', 'sitemngr.views.get_search_results'),
   url(r'^refreshgraph/', 'sitemngr.views.refresh_graph'),
   url(r'^massclose/', 'sitemngr.views.mass_close')
) + static(settings.STATIC_URL, document_root=settings.STATIC_ROOT) + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
