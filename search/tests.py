# -*- coding: utf-8 -*-
from django.db import models
from django.test import TestCase

# use immediate_update on tests
from django.conf import settings
settings.BACKEND = 'search.backends.immediate_update'

from search.core import SearchManager, startswith


# ExtraData is used for ForeignKey tests
class ExtraData(models.Model):
    name = models.CharField(max_length=500)
    description = models.CharField(max_length=500)

    def __unicode__(self):
        return self.name

class Indexed(models.Model):
    extra_data = models.ForeignKey(ExtraData)

    # Test normal and prefix index
    one = models.CharField(max_length=500, null=True)
    two = models.CharField(max_length=500)
    check = models.BooleanField()
    value = models.CharField(max_length=500)

    # search managers
    one_index = SearchManager('one', indexer=startswith)
    one_two_index = SearchManager(('one', 'two'))
    # relation index manager
    value_index = SearchManager('value', integrate=('one', 'check'))

# Test filters
class FiltersIndexed(models.Model):
    value = models.CharField(max_length=500)
    check = models.BooleanField()

    checked_index = SearchManager(('value', ), filters={'check':True, })

class TestIndexed(TestCase):
    def setUp(self):
        extra_data = ExtraData()
        extra_data.save()
        for i in range(3):
            Indexed(extra_data=extra_data, one=u'OneOne%d' % i).save()

        for i in range(3):
            Indexed(extra_data=extra_data, one=u'one%d' % i, two='two%d' % i).save()

        for i in range(3):
            Indexed(extra_data=extra_data, one=(None, u'ÜÄÖ-+!#><|', 'blub')[i],
                    check=bool(i%2), value=u'value%d test-word' % i).save()

        for i in range(3):
            FiltersIndexed(check=bool(i%2), value=u'value%d test-word' % i).save()

    def test_setup(self):
        self.assertEqual(len(Indexed.one_index.search('oneo')), 3)
        self.assertEqual(len(Indexed.one_index.search('one')), 6)

        self.assertEqual(len(Indexed.one_two_index.search('one2')), 1)
        self.assertEqual(len(Indexed.one_two_index.search('two')), 0)
        self.assertEqual(len(Indexed.one_two_index.search('two1')), 1)

        self.assertEqual(len(Indexed.value_index.search('word')), 3)
        self.assertEqual(len(Indexed.value_index.search('test-word')), 3)

        self.assertEqual(len(Indexed.value_index.search('value0').filter(
            check=False)), 1)
        self.assertEqual(len(Indexed.value_index.search('value1').filter(
            check=True, one=u'ÜÄÖ-+!#><|')), 1)
        self.assertEqual(len(Indexed.value_index.search('value2').filter(
            check__exact=False, one='blub')), 1)

        # test filters
        self.assertEqual(len(FiltersIndexed.checked_index.search('test-word')), 1)
        self.assertEqual(len(Indexed.value_index.search('foobar')), 0)

    def test_change(self):
        one = Indexed.one_index.search('oNeone1').get()
        one.one = 'oneoneone'
        one.save()

        value = Indexed.value_index.search('value0').get()
        value.value = 'value1 test-word'
        value.save()
        value.one = 'shidori'
        value.value = 'value3 rasengan/shidori'
        value.save()
        self.assertEqual(len(Indexed.value_index.search('rasengan')), 1)
        self.assertEqual(len(Indexed.value_index.search('value3')), 1)

        value = Indexed.value_index.search('value3').get()
        value.delete()
        self.assertEqual(len(Indexed.value_index.search('value3')), 0)

