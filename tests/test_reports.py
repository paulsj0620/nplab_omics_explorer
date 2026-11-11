import tempfile
import unittest
from pathlib import Path
from reports import resolve

class ReportPathTests(unittest.TestCase):
    def test_case_fallback_does_not_widen_report_boundary(self):
        with tempfile.TemporaryDirectory() as tmp:
            base=Path(tmp)
            root=base/'report'
            (root/'deg').mkdir(parents=True)
            (root/'deg/index.html').write_text('DEG')
            (root/'private.py').write_text('not an asset')
            (base/'secret.html').write_text('not in report')
            registry={'key':'report'}
            self.assertEqual(resolve(base,registry,'key/DEG/INDEX.HTML'),root/'deg/index.html')
            for route in ('key/../secret.html','key/DEG/../../secret.html',
                          'key/.hidden.html','key/private.py','key//deg/index.html','other/deg/index.html'):
                with self.assertRaises(FileNotFoundError):resolve(base,registry,route)
            (root/'escape.html').symlink_to(base/'secret.html')
            for route in ('key/escape.html','key/ESCAPE.HTML'):
                with self.assertRaises(FileNotFoundError):resolve(base,registry,route)
            (root/'deg/Exact.html').write_text('one')
            (root/'deg/exact.html').write_text('two')
            self.assertEqual(resolve(base,registry,'key/deg/Exact.html'),root/'deg/Exact.html')
            with self.assertRaises(FileNotFoundError):resolve(base,registry,'key/deg/EXACT.HTML')
            (root/'deg').rename(root/'original')
            (root/'deg').symlink_to(root/'original',target_is_directory=True)
            with self.assertRaises(FileNotFoundError):resolve(base,registry,'key/DEG/index.html')

if __name__=='__main__':unittest.main()
