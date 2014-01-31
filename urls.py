from django.conf.urls import patterns, url

urlpatterns = patterns('',
   url(r'^$', 'sitemngr.views.index', name='index'),
   url(r'^viewall/', 'sitemngr.views.view_all', name='view_all'),
   url(r'^add/', 'sitemngr.views.add', name='add'),
   url(r'^viewsite/(\d+)/', 'sitemngr.views.view_site', name='view_site'),
   url(r'^editsite/(\d+)/', 'sitemngr.views.edit_site', name='edit_site'),
   url(r'^addsite/', 'sitemngr.views.add_site', name='add_site'),
   url(r'^viewwormhole/(\d+)/', 'sitemngr.views.view_wormhole', name='view_wormhole'),
   url(r'^editwormhole/(\d+)/', 'sitemngr.views.edit_wormhole', name='edit_wormhole'),
   url(r'^addwormhole/', 'sitemngr.views.add_wormhole', name='add_wormhole'),
   url(r'^recentscanedits/', 'sitemngr.views.recent_scan_edits', name='recent_scan_edits'),
   url(r'^paste/', 'sitemngr.views.paste', name='paste'),
   url(r'^system/(.+)/', 'sitemngr.views.system', name='system'),
   url(r'^systemlanding/', 'sitemngr.views.system_landing', name='system_landing'),
   url(r'^lookup/(\w+)/', 'sitemngr.views.lookup', name='lookup'),
   url(r'^igbtest/', 'sitemngr.views.igb_test', name='igb_test'),
   url(r'^output/', 'sitemngr.views.output', name='output'),
   url(r'^help/', 'sitemngr.views.view_help', name='view_help'),
   url(r'^mastertable/', 'sitemngr.views.mastertable', name='mastertable'),
   url(r'^changelog/', 'sitemngr.views.changelog', name='changelog'),
   url(r'^checkkills/', 'sitemngr.views.check_kills', name='check_kills'),
   url(r'^stats/', 'sitemngr.views.stats', name='stats'),
   url(r'^settings/', 'sitemngr.views.settings', name='settings'),
   url(r'^login/', 'sitemngr.views.login_page', name='login_page'),
   url(r'^logout/', 'sitemngr.views.logout_page', name='logout_page'),
   url(r'^create_account/', 'sitemngr.views.create_account', name='create_account'),
   url(r'^overlay/', 'sitemngr.views.overlay', name='overlay'),
   url(r'^get_tradehub_jumps/(.+)/', 'sitemngr.views.get_tradehub_jumps', name='get_tradehub_jumps'),
   url(r'^get_search_results/(.+)/(.+)/', 'sitemngr.views.get_search_results', name='get_search_results'),
   url(r'^refreshgraph/', 'sitemngr.views.refresh_graph', name='refresh_graph'),
   url(r'^massclose/', 'sitemngr.views.mass_close', name='mass_close'),
   url(r'^deletewormhole/(\d+)/', 'sitemngr.views.delete_wormhole', name='delete_wormhole'),
   url(r'^inlineeditsite/', 'sitemngr.views.inline_edit_site', name='inline_edit_site'),
   url(r'^inlineeditwormhole/', 'sitemngr.views.inline_edit_wormhole', name='inline_edit_wormhole'),
)
