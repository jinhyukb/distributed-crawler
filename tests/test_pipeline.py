import unittest
from src.models import BookData

class TestPipelineValidation(unittest.TestCase):
    def test_schema_parsing(self):
        raw_data = {
            "title": "A Light in the Attic",
            "price": "£51.77",
            "in_stock": True,
            "rating": 3,
            "detail_url": "https://books.toscrape.com/catalogue/a-light-in-the-attic_1000/index.html"
        }
        validated = BookData(**raw_data)
        self.assertEqual(validated.price, 51.77)
        self.assertTrue(validated.in_stock)

if __name__ == "__main__":
    unittest.main()
