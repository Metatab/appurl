from __future__ import print_function

import unittest

from appurl.url import parse_app_url
from appurl.web.download import Downloader


class TestUrlParse(unittest.TestCase):
    def test_fragment(self):
        def u(frag):
            return parse_app_url("http://example.com/foo.csv#" + frag)

        self.assertEqual({}, u('a').fragment_query)
        self.assertEqual({}, u('a;b').fragment_query)
        self.assertEqual({'foo': 'bar'}, u('a;b&foo=bar').fragment_query)
        self.assertEqual({'foo': 'bar'}, u('a;&foo=bar').fragment_query)
        self.assertEqual({'foo': 'bar'}, u('a&foo=bar').fragment_query)
        self.assertEqual({'foo': 'bar'}, u('&foo=bar').fragment_query)
        self.assertEqual({'foo': 'bar'}, u(';&foo=bar').fragment_query)

        url = u('a;b&encoding=utf8')

        self.assertEqual('utf8', url.encoding)

        url.encoding = 'ascii'
        url.start = 5

        self.assertEqual('http://example.com/foo.csv#a;b&encoding=ascii&start=5', str(url))

        url = u('a;b&target_format=foo&resource_format=bar')

        self.assertEqual('foo', url.target_format)
        self.assertEqual('bar', url.resource_format)

        us = 'http://public.source.civicknowledge.com/example.com/sources/test_data.zip#unicode-latin1.csv&encoding=latin1'

        url = parse_app_url(us)

        self.assertEqual('latin1', url.encoding)
        self.assertEqual('latin1', url.get_resource().encoding)
        self.assertEqual('latin1', url.get_resource().get_target().encoding)

    def test_fragment_2(self):
        url = parse_app_url(
            'http://public.source.civicknowledge.com/example.com/sources/renter_cost_excel07.zip#target_format=xlsx')

        self.assertEqual('zip', url.resource_format)
        self.assertEqual('renter_cost_excel07.zip', url.target_file)
        self.assertEqual('xlsx', url.target_format)

        r = url.get_resource()

        self.assertEqual('xlsx', r.target_format)
        self.assertEqual('zip', r.resource_format)

    def test_two_extensions(self):
        u_s = 'http://public.source.civicknowledge.com/example.com/sources/simple-example.csv.zip'

        u = parse_app_url(u_s, Downloader())

        self.assertEqual('simple-example.csv.zip', u.resource_file)
        self.assertEqual('simple-example.csv.zip', u.target_file)
        self.assertEqual('zip', u.target_format)

        r = u.get_resource()
        self.assertEqual('simple-example.csv.zip', r.resource_file)
        self.assertEqual('simple-example.csv', r.target_file)
        self.assertEqual('csv', r.target_format)

    def test_shapefile_url(self):
        from appurl.web.web import WebUrl

        u_s = 'shapefile+http://public.source.civicknowledge.com.s3.amazonaws.com/example.com/geo/Parks_SD.zip'

        u = parse_app_url(u_s)

        self.assertIsInstance(u, WebUrl)

        r = u.get_resource()

        self.assertTrue(str(r).startswith('shapefile+'))

    def test_s3_url(self):
        from appurl.web.s3 import S3Url

        url_str = 's3://bucket/a/b/c/file.csv'

        u = parse_app_url(url_str)

        self.assertIsInstance(u, S3Url)

    def test_python_url(self):
        from appurl.file import python
        from rowgenerators import get_generator
        from types import ModuleType

        import sys

        foo = ModuleType('foo')
        sys.modules['foo'] = foo
        foo.bar = ModuleType('bar')
        sys.modules['foo.bar'] = foo.bar
        foo.bar.baz = ModuleType('baz')
        sys.modules['foo.bar.baz'] = foo.bar.baz

        def foobar(*args, **kwargs):
            for i in range(10):
                yield i

        foo.bar.baz.foobar = foobar

        u = parse_app_url("python:foo.bar.baz#foobar")

        g = get_generator(u)

        self.assertEqual(45, sum(list(g)))


if __name__ == '__main__':
    unittest.main()
