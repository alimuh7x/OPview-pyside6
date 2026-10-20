import unittest

from utils.vtk_utils import clear_reader_cache, reader_cache


class VTKReaderCacheTests(unittest.TestCase):
    def tearDown(self):
        reader_cache.clear()

    def test_clear_reader_cache_removes_stale_readers(self):
        reader_cache["stale-reader"] = object()

        clear_reader_cache("unit-test")

        self.assertNotIn("stale-reader", reader_cache)
