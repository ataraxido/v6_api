import datetime

from c2corg_api.models.association import Association
from c2corg_api.models.cache_version import CacheVersion, \
    update_cache_version, update_cache_version_associations
from c2corg_api.models.outing import Outing, OUTING_TYPE
from c2corg_api.models.route import Route, ROUTE_TYPE
from c2corg_api.models.waypoint import Waypoint, WAYPOINT_TYPE

from c2corg_api.tests import BaseTestCase


class TestCacheVersion(BaseTestCase):

    def setUp(self):  # noqa
        BaseTestCase.setUp(self)

    def test_trigger_create_cache_version(self):
        waypoint = Waypoint(waypoint_type='summit')
        self.session.add(waypoint)
        self.session.flush()

        cache_version = self.session.query(CacheVersion).get(
            waypoint.document_id)
        self.assertIsNotNone(cache_version)

    def test_update_cache_version_single_wp(self):
        waypoint = Waypoint(waypoint_type='summit')
        waypoint_unrelated = Waypoint(waypoint_type='summit')
        self.session.add_all([waypoint, waypoint_unrelated])
        self.session.flush()

        cache_version = self.session.query(CacheVersion).get(
            waypoint.document_id)
        current_version = cache_version.version

        update_cache_version(waypoint)
        self.session.refresh(cache_version)
        self.assertEqual(cache_version.version, current_version + 1)

        cache_version_untouched = self.session.query(CacheVersion).get(
            waypoint_unrelated.document_id)
        self.assertEqual(cache_version_untouched.version, 1)

    def test_update_cache_version_wp_with_associations(self):
        waypoint1 = Waypoint(waypoint_type='summit')
        waypoint2 = Waypoint(waypoint_type='summit')
        waypoint3 = Waypoint(waypoint_type='summit')
        waypoint_unrelated = Waypoint(waypoint_type='summit')
        self.session.add_all(
            [waypoint1, waypoint2, waypoint3, waypoint_unrelated])
        self.session.flush()

        self.session.add(Association.create(waypoint1, waypoint2))
        self.session.add(Association.create(waypoint3, waypoint1))
        self.session.flush()

        update_cache_version(waypoint1)
        cache_version1 = self.session.query(CacheVersion).get(
            waypoint1.document_id)
        cache_version2 = self.session.query(CacheVersion).get(
            waypoint1.document_id)
        cache_version3 = self.session.query(CacheVersion).get(
            waypoint1.document_id)
        cache_version_untouched = self.session.query(CacheVersion).get(
            waypoint_unrelated.document_id)

        self.assertEqual(cache_version1.version, 2)
        self.assertEqual(cache_version2.version, 2)
        self.assertEqual(cache_version3.version, 2)
        self.assertEqual(cache_version_untouched.version, 1)

    def test_update_cache_version_wp_as_main_wp(self):
        waypoint1 = Waypoint(waypoint_type='summit')
        waypoint2 = Waypoint(waypoint_type='summit')
        waypoint3 = Waypoint(waypoint_type='summit')
        waypoint_unrelated = Waypoint(waypoint_type='summit')
        route = Route(main_waypoint=waypoint1, activities=['skitouring'])
        self.session.add_all(
            [waypoint1, waypoint2, waypoint3, waypoint_unrelated, route])
        self.session.flush()

        self.session.add(Association.create(waypoint1, route))
        self.session.add(Association.create(waypoint2, route))
        self.session.add(Association.create(waypoint3, waypoint2))
        self.session.flush()

        update_cache_version(waypoint1)
        cache_version_wp1 = self.session.query(CacheVersion).get(
            waypoint1.document_id)
        cache_version_wp2 = self.session.query(CacheVersion).get(
            waypoint2.document_id)
        cache_version_wp3 = self.session.query(CacheVersion).get(
            waypoint3.document_id)
        cache_version_route = self.session.query(CacheVersion).get(
            route.document_id)
        cache_version_untouched = self.session.query(CacheVersion).get(
            waypoint_unrelated.document_id)

        self.assertEqual(cache_version_wp1.version, 3)
        self.assertEqual(cache_version_wp2.version, 2)
        self.assertEqual(cache_version_wp3.version, 2)
        self.assertEqual(cache_version_route.version, 2)
        self.assertEqual(cache_version_untouched.version, 1)

    def test_update_cache_version_route(self):
        route1 = Route(activities=['skitouring'])
        route2 = Route(activities=['skitouring'])
        waypoint1 = Waypoint(waypoint_type='summit')
        waypoint2 = Waypoint(waypoint_type='summit')
        waypoint_unrelated = Waypoint(waypoint_type='summit')
        self.session.add_all(
            [waypoint1, waypoint2, waypoint_unrelated, route1, route2])
        self.session.flush()

        self.session.add(Association.create(waypoint1, route1))
        self.session.add(Association.create(route2, route1))
        self.session.add(Association.create(waypoint2, waypoint1))
        self.session.flush()

        update_cache_version(route1)
        cache_version_route1 = self.session.query(CacheVersion).get(
            route1.document_id)
        cache_version_route2 = self.session.query(CacheVersion).get(
            route2.document_id)
        cache_version_wp1 = self.session.query(CacheVersion).get(
            waypoint1.document_id)
        cache_version_wp2 = self.session.query(CacheVersion).get(
            waypoint2.document_id)
        cache_version_untouched = self.session.query(CacheVersion).get(
            waypoint_unrelated.document_id)

        self.assertEqual(cache_version_route1.version, 2)
        self.assertEqual(cache_version_route2.version, 2)
        self.assertEqual(cache_version_wp1.version, 3)
        self.assertEqual(cache_version_wp2.version, 2)
        self.assertEqual(cache_version_untouched.version, 1)

    def test_update_cache_version_outing(self):
        outing = Outing(
            activities=['skitouring'],
            date_start=datetime.date(2016, 2, 1),
            date_end=datetime.date(2016, 2, 1))
        route1 = Route(activities=['skitouring'])
        route2 = Route(activities=['skitouring'])
        waypoint1 = Waypoint(waypoint_type='summit')
        waypoint2 = Waypoint(waypoint_type='summit')
        waypoint_unrelated = Waypoint(waypoint_type='summit')
        self.session.add_all(
            [outing, waypoint1, waypoint2, waypoint_unrelated, route1, route2])
        self.session.flush()

        self.session.add(Association.create(route1, outing))
        self.session.add(Association.create(waypoint1, route1))
        self.session.add(Association.create(route2, outing))
        self.session.add(Association.create(waypoint2, waypoint1))
        self.session.flush()

        update_cache_version(outing)
        cache_version_outing = self.session.query(CacheVersion).get(
            outing.document_id)
        cache_version_route1 = self.session.query(CacheVersion).get(
            route1.document_id)
        cache_version_route2 = self.session.query(CacheVersion).get(
            route2.document_id)
        cache_version_wp1 = self.session.query(CacheVersion).get(
            waypoint1.document_id)
        cache_version_wp2 = self.session.query(CacheVersion).get(
            waypoint2.document_id)
        cache_version_untouched = self.session.query(CacheVersion).get(
            waypoint_unrelated.document_id)

        self.assertEqual(cache_version_outing.version, 2)
        self.assertEqual(cache_version_route1.version, 2)
        self.assertEqual(cache_version_route2.version, 2)
        self.assertEqual(cache_version_wp1.version, 2)
        self.assertEqual(cache_version_wp2.version, 2)
        self.assertEqual(cache_version_untouched.version, 1)

    def test_update_cache_version_associations_removed_wp(self):
        waypoint1 = Waypoint(waypoint_type='summit')
        waypoint2 = Waypoint(waypoint_type='summit')
        waypoint3 = Waypoint(waypoint_type='summit')
        waypoint_unrelated = Waypoint(waypoint_type='summit')
        self.session.add_all(
            [waypoint1, waypoint2, waypoint3, waypoint_unrelated])
        self.session.flush()

        update_cache_version_associations([], [
            {'parent_id': waypoint1.document_id, 'parent_type': WAYPOINT_TYPE,
             'child_id': waypoint2.document_id, 'child_type': WAYPOINT_TYPE},
            {'parent_id': waypoint3.document_id, 'parent_type': WAYPOINT_TYPE,
             'child_id': waypoint1.document_id, 'child_type': WAYPOINT_TYPE}
        ])

        cache_version1 = self.session.query(CacheVersion).get(
            waypoint1.document_id)
        cache_version2 = self.session.query(CacheVersion).get(
            waypoint2.document_id)
        cache_version3 = self.session.query(CacheVersion).get(
            waypoint3.document_id)
        cache_version_untouched = self.session.query(CacheVersion).get(
            waypoint_unrelated.document_id)

        self.assertEqual(cache_version1.version, 2)
        self.assertEqual(cache_version2.version, 2)
        self.assertEqual(cache_version3.version, 2)
        self.assertEqual(cache_version_untouched.version, 1)

    def test_update_cache_version_associations_removed_wp_route(self):
        waypoint1 = Waypoint(waypoint_type='summit')
        waypoint2 = Waypoint(waypoint_type='summit')
        waypoint3 = Waypoint(waypoint_type='summit')
        waypoint_unrelated = Waypoint(waypoint_type='summit')
        route = Route(activities=['skitouring'])
        self.session.add_all(
            [waypoint1, waypoint2, waypoint3, waypoint_unrelated, route])
        self.session.flush()

        self.session.add(Association.create(waypoint2, waypoint1))
        self.session.add(Association.create(waypoint3, waypoint2))
        self.session.flush()

        update_cache_version_associations([], [
            {'parent_id': waypoint1.document_id, 'parent_type': WAYPOINT_TYPE,
             'child_id': route.document_id, 'child_type': ROUTE_TYPE}
        ])

        cache_version1 = self.session.query(CacheVersion).get(
            waypoint1.document_id)
        cache_version2 = self.session.query(CacheVersion).get(
            waypoint2.document_id)
        cache_version3 = self.session.query(CacheVersion).get(
            waypoint3.document_id)
        cache_version_route = self.session.query(CacheVersion).get(
            route.document_id)
        cache_version_untouched = self.session.query(CacheVersion).get(
            waypoint_unrelated.document_id)

        self.assertEqual(cache_version1.version, 2)
        self.assertEqual(cache_version2.version, 2)
        self.assertEqual(cache_version3.version, 2)
        self.assertEqual(cache_version_route.version, 2)
        self.assertEqual(cache_version_untouched.version, 1)

    def test_update_cache_version_associations_removed_route_outing(self):
        waypoint1 = Waypoint(waypoint_type='summit')
        waypoint2 = Waypoint(waypoint_type='summit')
        waypoint3 = Waypoint(waypoint_type='summit')
        waypoint_unrelated = Waypoint(waypoint_type='summit')
        route = Route(activities=['skitouring'])
        outing = Outing(
            activities=['skitouring'],
            date_start=datetime.date(2016, 2, 1),
            date_end=datetime.date(2016, 2, 1))
        self.session.add_all(
            [waypoint1, waypoint2, waypoint3, waypoint_unrelated,
             route, outing])
        self.session.flush()

        self.session.add(Association.create(waypoint1, route))
        self.session.add(Association.create(waypoint2, waypoint1))
        self.session.add(Association.create(waypoint3, waypoint2))
        self.session.flush()

        update_cache_version_associations([], [
            {'parent_id': route.document_id, 'parent_type': ROUTE_TYPE,
             'child_id': outing.document_id, 'child_type': OUTING_TYPE}
        ])

        cache_version1 = self.session.query(CacheVersion).get(
            waypoint1.document_id)
        cache_version2 = self.session.query(CacheVersion).get(
            waypoint2.document_id)
        cache_version3 = self.session.query(CacheVersion).get(
            waypoint3.document_id)
        cache_version_route = self.session.query(CacheVersion).get(
            route.document_id)
        cache_version_outing = self.session.query(CacheVersion).get(
            outing.document_id)
        cache_version_untouched = self.session.query(CacheVersion).get(
            waypoint_unrelated.document_id)

        self.assertEqual(cache_version1.version, 2)
        self.assertEqual(cache_version2.version, 2)
        self.assertEqual(cache_version3.version, 2)
        self.assertEqual(cache_version_route.version, 2)
        self.assertEqual(cache_version_outing.version, 2)
        self.assertEqual(cache_version_untouched.version, 1)