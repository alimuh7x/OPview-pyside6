import unittest

from app.resources import APP_LOGO_PATH, DOCUMENTATION_PATH, HEATMAP_LOGO_PATH


class AppResourcesTests(unittest.TestCase):
    def test_app_logo_uses_main_logo_asset(self):
        self.assertEqual(APP_LOGO_PATH.name, "OP_Logo.png")
        self.assertTrue(APP_LOGO_PATH.exists())

    def test_heatmap_logo_uses_existing_logo_asset(self):
        self.assertEqual(HEATMAP_LOGO_PATH.name, "OP_Logo.png")
        self.assertTrue(HEATMAP_LOGO_PATH.exists())

    def test_documentation_points_to_local_markdown(self):
        self.assertEqual(DOCUMENTATION_PATH.name, "Documentation.md")
        self.assertTrue(DOCUMENTATION_PATH.exists())


if __name__ == "__main__":
    unittest.main()
