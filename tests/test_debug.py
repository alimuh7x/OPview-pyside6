import io
import os
import unittest
from contextlib import redirect_stdout

from app.debug import debug_print


class DebugPrintTests(unittest.TestCase):
    def test_debug_print_is_silent_by_default(self):
        os.environ.pop("OPVIEW_DEBUG", None)
        output = io.StringIO()

        with redirect_stdout(output):
            debug_print("hidden")

        self.assertEqual(output.getvalue(), "")


if __name__ == "__main__":
    unittest.main()
