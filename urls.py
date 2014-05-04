from django.conf.urls import patterns, url

urlpatterns = patterns('',
   url(r'^$', 'sitemngr.views.index', name='sm_index'),
   url(r'^viewall/', 'sitemngr.views.view_all', name='sm_view_all'),
   url(r'^add/', 'sitemngr.views.add', name='sm_add'),
   url(r'^viewsite/(\d+)/', 'sitemngr.views.view_site', name='sm_view_site'),
   url(r'^editsite/(\d+)/', 'sitemngr.views.edit_site', name='sm_edit_site'),
   url(r'^addsite/', 'sitemngr.views.add_site', name='sm_add_site'),
   url(r'^viewwormhole/(\d+)/', 'sitemngr.views.view_wormhole', name='sm_view_wormhole'),
   url(r'^editwormhole/(\d+)/', 'sitemngr.views.edit_wormhole', name='sm_edit_wormhole'),
   url(r'^addwormhole/', 'sitemngr.views.add_wormhole', name='sm_add_wormhole'),
   url(r'^recentscanedits/', 'sitemngr.views.recent_scan_edits', name='sm_recent_scan_edits'),
   url(r'^paste/', 'sitemngr.views.paste', name='sm_paste'),
   url(r'^system/(.+)/', 'sitemngr.views.system', name='sm_system'),
   url(r'^systemlanding/', 'sitemngr.views.system_landing', name='sm_system_landing'),
   url(r'^lookup/(\w+)/', 'sitemngr.views.lookup', name='sm_lookup'),
   url(r'^igbtest/', 'sitemngr.views.igb_test', name='sm_igb_test'),
   url(r'^output/', 'sitemngr.views.output', name='sm_output'),
   url(r'^help/', 'sitemngr.views.view_help', name='sm_view_help'),
   url(r'^mastertable/', 'sitemngr.views.mastertable', name='sm_mastertable'),
   url(r'^changelog/', 'sitemngr.views.changelog', name='sm_changelog'),
   url(r'^checkkills/', 'sitemngr.views.check_kills', name='sm_check_kills'),
   url(r'^stats/', 'sitemngr.views.stats', name='sm_stats'),
   url(r'^settings/', 'sitemngr.views.settings', name='sm_settings'),
   url(r'^login/', 'sitemngr.views.login_page', name='sm_login_page'),
   url(r'^logout/', 'sitemngr.views.logout_page', name='sm_logout_page'),
   url(r'^create_account/', 'sitemngr.views.create_account', name='sm_create_account'),
   url(r'^overlay/', 'sitemngr.views.overlay', name='sm_overlay'),
   url(r'^get_tradehub_jumps/(.+)/', 'sitemngr.views.get_tradehub_jumps', name='sm_get_tradehub_jumps'),
   url(r'^get_search_results/(.+)/', 'sitemngr.views.get_search_results', name='sm_get_search_results'),
   url(r'^refreshgraph/', 'sitemngr.views.refresh_graph', name='sm_refresh_graph'),
   url(r'^massclose/', 'sitemngr.views.mass_close', name='sm_mass_close'),
   url(r'^deletewormhole/(\d+)/', 'sitemngr.views.delete_wormhole', name='sm_delete_wormhole'),
   url(r'^inlineeditsite/', 'sitemngr.views.inline_edit_site', name='sm_inline_edit_site'),
   url(r'^inlineeditwormhole/', 'sitemngr.views.inline_edit_wormhole', name='sm_inline_edit_wormhole'),
   url(r'^system_kills/(.+)/', 'sitemngr.views.system_kills', name='sm_system_kills'),
)
