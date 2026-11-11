import io
import ipaddress
import json
from pathlib import Path
import tempfile
import unittest

from reports import load_config
from server import Catalog, allowed, byte_range, handler


class ServerTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.report = self.base/'external-report'
        (self.report/'home').mkdir(parents=True)
        (self.report/'deg').mkdir()
        self.html = '<html><head><title>Example</title></head><body>Example report</body></html>'
        (self.report/'home/index.html').write_text(self.html)
        (self.report/'deg/index.html').write_text(self.html)
        (self.report/'data.csv').write_text('x,y\n1,2\n')
        (self.report/'private.py').write_text('private')
        self.config = self.base/'config.local.json'
        self.mount = dict(id='demo',name='Example',kind='rnaseq',path='external-report')
        self.config.write_text(json.dumps(dict(reports=[self.mount])))
        self.catalog = Catalog(self.config)
        self.catalog.refresh()
        self.cls = handler(self.catalog,[ipaddress.ip_network('127.0.0.1/32')])
        self.cls.log_message = lambda *args: None

    def request(self, path, headers='', peer='127.0.0.1', method='GET'):
        class Connection:
            def __init__(self, request):
                self.request=io.BytesIO(request)
                self.output=io.BytesIO()
            def makefile(self, *args): return self.request
            def sendall(self, data): self.output.write(data)
        conn=Connection(f'{method} {path} HTTP/1.0\r\n{headers}\r\n'.encode())
        self.cls(conn,(peer,1),None)
        return conn.output.getvalue()

    def test_default_is_empty_and_catalog_omits_private_mounts(self):
        empty=Catalog()
        empty.refresh()
        self.assertEqual(empty.snapshot[2],{})
        self.assertIn(b'"reports": []',empty.snapshot[0])
        self.assertNotIn(str(self.base).encode(),self.catalog.snapshot[0])
        self.assertIn(b'home/index.html',self.catalog.snapshot[0])

    def test_static_assets_and_response_only_presentation(self):
        for asset in ('','index.html','style.css','theme.css','nav.css','nav.js','app.js','catalog.js','favicon.svg'):
            self.assertIn(b'200 OK',self.request('/results/'+asset+'?v=test'))
        response=self.request('/results/reports/demo/home/index.html')
        self.assertIn(b'/results/nav.js?v=',response)
        self.assertIn(b'/results/nav.css?v=',response)
        self.assertEqual((self.report/'home/index.html').read_text(),self.html)
        response=self.request('/results/reports/demo/DEG/INDEX.HTML?d=2&view=full')
        self.assertIn(b'302 Found',response)
        self.assertIn(b'Location: /results/reports/demo/deg/index.html?d=2&view=full\r\n',response)

    def test_boundaries_and_symlink_replacement(self):
        for path in ('/results/config.local.json','/results/reports/demo/private.py',
                     '/results/reports/demo/%2e%2e/config.local.json','/results/files/data.csv'):
            self.assertIn(b'404 Not Found',self.request(path))
        self.assertIn(b'403',self.request('/results/','X-Forwarded-For: 127.0.0.1\r\n',peer='192.0.2.1'))
        target=self.report/'data.csv'
        target.unlink()
        target.symlink_to(self.config)
        self.assertIn(b'404',self.request('/results/reports/demo/data.csv'))

    def test_download_ranges_and_head(self):
        url='/results/reports/demo/data.csv'
        response=self.request(url,'Range: bytes=0-2\r\n')
        self.assertIn(b'206 Partial Content',response)
        self.assertEqual(response.split(b'\r\n\r\n')[1],b'x,y')
        self.assertIn(b'416',self.request(url,'Range: bytes=99-\r\n'))
        self.assertEqual(self.request(url,method='HEAD').split(b'\r\n\r\n')[1],b'')

    def test_invalid_configuration_does_not_replace_catalog(self):
        original=self.catalog.snapshot
        self.config.write_text('invalid JSON')
        with self.assertRaises(ValueError): self.catalog.refresh()
        self.assertEqual(original,self.catalog.snapshot)
        for data in ({}, {'reports':[self.mount,self.mount]}, {'reports':[{'id':'../bad','path':'external-report'}]}):
            self.config.write_text(json.dumps(data))
            with self.assertRaises(ValueError): load_config(self.config)

    def test_network_and_range_parsing(self):
        nets=[ipaddress.ip_network('192.0.2.0/24')]
        self.assertTrue(allowed('192.0.2.1',nets))
        self.assertTrue(allowed('::ffff:192.0.2.1',nets))
        self.assertFalse(allowed('192.0.3.1',nets))
        self.assertFalse(allowed('invalid',nets))
        self.assertEqual(byte_range('bytes=-4',10),(6,9))
        self.assertEqual(byte_range('bytes=8-',10),(8,9))
        for value in ('bytes=12-', 'bytes=-0', 'bytes=4-2', 'bytes=0-1,4-5'):
            with self.assertRaises(ValueError): byte_range(value,10)


if __name__=='__main__': unittest.main()
