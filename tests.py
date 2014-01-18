# python
from datetime import datetime

# django
from django.test import TestCase

# sitemngr
from sitemngr.models import Site, SiteSnapshot, Wormhole, WormholeSnapshot
import appSettings
import util

now = lambda: datetime.utcnow()

class ObjectsTest(TestCase):
	def test_first_test(self):
		site = Site(creator='SERVER', scanid='AAA', date=now(), name='the name', type='the type', \
			where=appSettings.HOME_SYSTEM, opened=True, closed=False, notes='')
		snap1 = util.snapshot(site)
		self.assertEqual(snap1.scanid, site.scanid)
		site.scanid = 'BBB'
		snap2 = util.snapshot(site)
		self.assertEqual(snap2.scanid, site.scanid)