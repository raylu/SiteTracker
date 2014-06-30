# SiteManager

A Django app for managing anomalies and signatures in EVE Online for the OI alliance.
It allows users to track Anomalies, Signatures, and Wormholes in space and share the information with others in their alliance.
Browsing to /sitemngr/help/ while running the project will show a help page.

## Setup

1. On a Debian-based machine, install `python-django python-tz`
1. `django-admin startproject sitetracker`
1. `cd sitetracker && chmod +x manage.py`
1. `git clone git@github.com:Celeo/SiteTracker.git sitemngr`
1. Add the following URL to `sitetracker/urls.py`:
`    url(r'^', include('sitemngr.urls')),`
1. `git clone https://github.com/eve-val/evelink evelink.git && ln -s evelink.git/evelink`
1. Either comment out all LDAP-related lines or install `python-django-auth-ldap` and set up LDAP.
1. `./manage.py syncdb`
1. `./manage.py runserver`
1. Go to http://localhost:8000/admin and create a wormhole or site manually before using the site.

## Credits

All EVE Online and CCP references belong to CCP.
