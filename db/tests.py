#
# Unit Tests for db
#
# Provides automated tests for db module
#
# Copyright 2010 Greek Research and Technology Network
#

from db.models import *

from django.test import TestCase


class FlavorTestCase(TestCase):
    fixtures = [ 'db_test_data' ]

    def test_flavor(self):
        """Test a flavor object, its internal cost calculation and naming methods"""
        flavor = Flavor.objects.get(pk=30000)

        # test current active/inactive costs
        c_active = flavor.current_cost_active
        c_inactive = flavor.current_cost_inactive

        self.assertEqual(c_active, 10, 'flavor.cost_active should be 10! (%d)' % (c_active,))
        self.assertEqual(c_inactive, 5, 'flavor.cost_inactive should be 5! (%d)' % (c_inactive,))

        # test name property, should be C1R1024D10
        f_name = flavor.name

        self.assertEqual(f_name, 'C1R1024D10', 'flavor.name is not generated correctly, C1R1024D10! (%s)' % (f_name,))

    def test_flavor_get_costs(self):
        """Test the Flavor _get_costs() method"""
        # first an easy test, a Flavor with only one FlavorCost entry
        flavor = Flavor.objects.get(pk=30001)

        start_date = datetime.datetime(year=2010, month=1, day=1)
        end_date = datetime.datetime(year=2010, month=1, day=2)

        # we now that the cost should be 5*24 (inactive) and 10*24 (active)
        r_active = flavor.get_cost_active(start_date, end_date)
        r_inactive = flavor.get_cost_inactive(start_date, end_date)

        self.assertEqual(len(r_active), 1, 'flavor.get_cost_active() should have returned 1 entry (%d)' %(len(r_active),))
        self.assertEqual(len(r_inactive), 1, 'flavor.get_cost_inactive() should have returned 1 entry (%d)'% (len(r_inactive),))

        self.assertEqual(10*24, r_active[0][1], 'flavor.get_cost_active() is not working properly (%d!=%d)' % (r_active[0][1], 10*24))
        self.assertEqual(5*24, r_inactive[0][1], 'flavor.get_cost_inactive() is not working properly (%d!=%d)' % (r_inactive[0][1], 5*24))

        # The second test, will involve a more complex cost example
        # The overall cost will be calculated by two FlavorCost entries

        flavor = Flavor.objects.get(pk=30000)

        start_date = datetime.datetime(year=2010, month=12, day=31)
        end_date = datetime.datetime(year=2011, month=01, day=2)

        # this is more complicated, active costs are 5*24 + 10*24 = 360
        # and inactive costs are 2*24 + 5*24 = 168
        
        r_active = flavor.get_cost_active(start_date, end_date)
        r_inactive = flavor.get_cost_inactive(start_date, end_date)

        self.assertEqual(len(r_active), 2, 'flavor.get_cost_active() should have returned 2 entries (%d)' %(len(r_active),))
        self.assertEqual(len(r_inactive), 2, 'flavor.get_cost_inactive() should have returned 2 entries (%d)'% (len(r_inactive),))

        ta_cost = sum([x[1] for x in r_active])
        tia_cost = sum([x[1] for x in r_inactive])

        self.assertEqual(360, ta_cost, 'flavor.get_cost_active() is not working properly (%d!=%d)' % (ta_cost, 360))
        self.assertEqual(168, tia_cost, 'flavor.get_cost_inactive() is not working properly (%d!=%d)' % (tia_cost, 168))


