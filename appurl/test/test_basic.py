from __future__ import print_function

import unittest
from csv import DictReader
from os.path import exists, dirname

from appurl.archive.zip import ZipUrl
from appurl.url import Url, parse_app_url
from appurl.web.download import Downloader
from appurl.web.s3 import S3Url
from appurl.web.web import WebUrl

from appurl.test.support import data_path

class BasicTests(unittest.TestCase):

    def compare_dict(self, name, a, b):
        from rowgenerators.util import flatten
        fa = set('{}={}'.format(k, v) for k, v in flatten(a));
        fb = set('{}={}'.format(k, v) for k, v in flatten(b));

        # The declare lines move around a lot, and rarely indicate an error
        fa = {e for e in fa if not e.startswith('declare=')}
        fb = {e for e in fb if not e.startswith('declare=')}

        errors = len(fa - fb) + len(fb - fa)

        if errors:
            print("=== ERRORS for {} ===".format(name))

        if len(fa - fb):
            print("In a but not b")
            for e in sorted(fa - fb):
                print('    ', e)

        if len(fb - fa):
            print("In b but not a")
            for e in sorted(fb - fa):
                print('    ', e)

        self.assertEqual(0, errors)


    def test_traits(self):

        u = Url("http://example.com/foo/bar.csv")

        self.assertEqual('http',u.proto)
        self.assertEqual('/foo/bar.csv', u.path)

        self.assertEqual('http://example.com/foo/bar.csv', str(u))

        u.path = '/bar/baz.csv'

        self.assertEqual('http://example.com/bar/baz.csv', str(u))



    def test_entry_points(self):

        self.assertIsInstance(parse_app_url('s3://bucket.com/foo/bar/baz.zip'), S3Url)
        self.assertIsInstance(parse_app_url('http://bucket.com/foo/bar/baz.zip'), WebUrl)
        self.assertIsInstance(parse_app_url('file://bucket.com/foo/bar/baz.zip'), ZipUrl)

    def test_entry_point_priorities(self):
        from pkg_resources import iter_entry_points

        eps = [ep.load().__name__ for ep in iter_entry_points(group='appurl.urls')]

        self.assertIn('ExcelFileUrl', eps)
        self.assertIn('WebUrl', eps)


    def test_download(self):
        """Test all three stages of a collection of downloadable URLS"""

        dldr = Downloader()

        with open(data_path('sources.csv')) as f:
            for e in DictReader(f):

                if e['name'] != 'mz_no_zip':
                    continue

                #print(e['name'])
                if not e['resource_class']:
                    continue


                u = parse_app_url(e['url'], downloader=dldr)

                self.assertEqual(e['url_class'], u.__class__.__name__, e['name'])
                self.assertEqual(e['resource_format'], u.resource_format, e['name'])

                r = u.get_resource()
                self.assertEqual(e['resource_class'],r.__class__.__name__, e['name'])
                self.assertEqual(e['resource_format'], r.resource_format, e['name'])

                t = r.get_target()

                self.assertEqual(e['target_class'], t.__class__.__name__, e['name'])
                self.assertEqual(e['target_format'], t.target_format, e['name'])
                self.assertTrue(exists(t.path))

    def test_url_classes(self):

        from appurl import match_url_classes

        with open(data_path('url_classes.csv')) as f:
            for e in DictReader(f):

                if not e['class']:
                    continue

                u = parse_app_url(e['in_url'])

                self.assertEqual(e['url'], str(u), e['in_url'])
                self.assertEqual(e['resource_url'], str(u.resource_url), e['in_url'])
                self.assertEqual(e['resource_file'], u.resource_file, e['in_url'])
                self.assertEqual(e['target_file'], u.target_file or '', e['in_url'])


    def test_component(self):

        with open(data_path('components.csv')) as f:
            for e in DictReader(f):

                b = parse_app_url(e['base_url'])
                c = parse_app_url(e['component_url'])

                self.assertEqual(e['class'], b.__class__.__name__, e['base_url'])

                self.assertEqual(e['join_dir'], str(b.join_dir(c)), e['base_url'])
                self.assertEqual(e['join'], str(b.join(c)), e['base_url'])

                self.assertEqual(str(e['join_target']), str(b.join_target(c)), e['base_url'])


    def test_base_url(self):
        """Simple test of splitting and recombining"""

        for u_s in ('http://server.com/a/b/c/file.csv','http://server.com/a/b/c/file.csv#a',
                    'http://server.com/a/b/c/file.csv#a;b', 'http://server.com/a/b/c/archive.zip#file.csv'):
            self.assertEqual(u_s, str(Url(u_s)))

        self.assertEqual('file.csv', Url('http://server.com/a/b/c/file.csv').target_file)
        self.assertEqual('file.csv', Url('http://server.com/a/b/c/file.csv').resource_file)
        self.assertEqual('http://server.com/a/b/c/file.csv', Url('http://server.com/a/b/c/file.csv').resource_url)

        self.assertEqual('file.csv', Url('http://server.com/a/b/c/resource.zip#file.csv').target_file)
        self.assertEqual('resource.zip', Url('http://server.com/a/b/c/resource.zip#file.csv').resource_file)





    def test_parse_file_urls(self):
        urls = [
            ('file:foo/bar/baz', 'foo/bar/baz', 'file:foo/bar/baz'),
            ('file:/foo/bar/baz', '/foo/bar/baz', 'file:/foo/bar/baz'),
            ('file://example.com/foo/bar/baz', '/foo/bar/baz', 'file://example.com/foo/bar/baz'),
            ('file:///foo/bar/baz', '/foo/bar/baz', 'file:/foo/bar/baz'),
        ]

        for i, o, u in urls:
            p = parse_app_url(i)
            self.assertEqual(o, p.path)
            self.assertEqual(u, str(p))

    def test_windows_urls(self):

        url = 'w:/metatab36/metatab-py/metatab/templates/metatab.csv'

        self.assertEqual('file:w:/metatab36/metatab-py/metatab/templates/metatab.csv',
                          str(parse_app_url(url)))

        url = 'N:/Desktop/metadata.csv#renter_cost'

        self.assertEqual('file:N:/Desktop/metadata.csv#renter_cost',
                          str(parse_app_url(url)))

    def test_query_urls(self):

        url='https://s3.amazonaws.com/private.library.civicknowledge.com/civicknowledge.com-rcfe_health-1/metadata.csv?AWSAccessKeyId=AKIAJFW23EPQCLXRU7DA&Signature=A39XhRP%2FTKAxv%2B%2F5vCubwWPDag0%3D&Expires=1494223447'

        u = Url(url)

        self.assertEqual('metadata.csv', str(u.resource_file))
        self.assertEqual('csv', str(u.resource_format))

        self.assertEqual('metadata.csv', str(u.target_file))
        self.assertEqual('csv', str(u.target_format))

    def test_socrata(self):

        u_s = 'https://data.lacounty.gov/api/views/8rdv-6nb6/rows.csv?accessType=DOWNLOAD'
        u = parse_app_url(u_s)
        self.assertIsInstance(parse_app_url(u_s), WebUrl)

        self.assertEqual('https://data.lacounty.gov/api/views/8rdv-6nb6/rows.csv?accessType=DOWNLOAD', str(u.resource_url))


    def test_fragment(self):

        u = Url('http://example.com/file.csv')
        self.assertEqual((None,None), tuple(u.fragment))
        self.assertEqual('file.csv', u.target_file)
        self.assertEqual(None, u.target_segment)
        self.assertEqual('http://example.com/file.csv', str(u))


        u = Url('http://example.com/file.csv#a')
        self.assertEqual(('a', None), tuple(u.fragment))
        self.assertEqual('a', u.target_file)
        self.assertEqual(None, u.target_segment)
        self.assertEqual('http://example.com/file.csv#a', str(u))

        u = Url('http://example.com/file.csv#a;b')
        self.assertEqual('a', u.target_file)
        self.assertEqual('b', u.target_segment)
        self.assertEqual('http://example.com/file.csv#a;b', str(u))

    def test_targets(self):

        u=parse_app_url('http://library.metatab.org/example.com-example_data_package-2017-us-1.xlsx')

        tfu = u.join_target('random-names')

        self.assertEqual(
            'http://library.metatab.org/example.com-example_data_package-2017-us-1.xlsx#random-names',
            str(tfu))

        r = tfu.get_resource()

        self.assertTrue(str(r)
                        .endswith('library.metatab.org/example.com-example_data_package-2017-us-1.xlsx#random-names'))

        t = r.get_target()

        self.assertTrue(str(t)
                        .endswith('library.metatab.org/example.com-example_data_package-2017-us-1.xlsx#random-names'))


    def test_list(self):

        import appurl

        u = parse_app_url(dirname(appurl.__file__))

        self.assertTrue(len(list(u.list())) > 10)

        return

        u = parse_app_url('http://public.source.civicknowledge.com/example.com/sources/test_data.zip')

        print(type(u))

        for su in u.list():
            for ssu in su.list():
                print(ssu)



#if __name__ == '__main__':
#    unittest.main()
