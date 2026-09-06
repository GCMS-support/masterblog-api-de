import json
import sys
import tempfile
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "backend"))
import backend_app as api


class MasterblogApiTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.original_posts_file = api.POSTS_FILE
        api.POSTS_FILE = Path(self.temp_dir.name) / "posts.json"
        api.app.config.update(TESTING=True)
        self.client = api.app.test_client()

    def tearDown(self):
        api.POSTS_FILE = self.original_posts_file
        self.temp_dir.cleanup()

    def test_list_initializes_storage_and_gets_one_post(self):
        response = self.client.get("/api/posts")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.get_json()), 2)
        self.assertTrue(api.POSTS_FILE.exists())
        one = self.client.get("/api/posts/1")
        self.assertEqual(one.status_code, 200)
        self.assertEqual(one.get_json()["author"], "Alice")
        self.assertEqual(self.client.get("/api/posts/99").status_code, 404)

    def test_create_uses_defaults_and_persists(self):
        response = self.client.post(
            "/api/posts",
            json={"title": "New", "content": "Persistent"},
        )
        self.assertEqual(response.status_code, 201)
        created = response.get_json()
        self.assertEqual(created["id"], 3)
        self.assertEqual(created["author"], "Anonymous")
        self.assertRegex(created["date"], r"^\d{4}-\d{2}-\d{2}$")
        with api.POSTS_FILE.open(encoding="utf-8") as file:
            self.assertEqual(json.load(file)[-1], created)

    def test_create_rejects_bad_payloads(self):
        self.assertEqual(self.client.post("/api/posts").status_code, 400)
        self.assertEqual(self.client.post("/api/posts", json=[]).status_code, 400)
        self.assertEqual(self.client.post("/api/posts", json={"title": "Only"}).status_code, 400)
        response = self.client.post(
            "/api/posts",
            json={"title": "Bad date", "content": "No", "date": "03/02/2024"},
        )
        self.assertEqual(response.status_code, 400)

    def test_update_is_partial_and_persists(self):
        response = self.client.put(
            "/api/posts/1",
            json={"title": "Changed", "author": "  Chris  ", "date": "2024-02-29"},
        )
        self.assertEqual(response.status_code, 200)
        updated = response.get_json()
        self.assertEqual(updated["title"], "Changed")
        self.assertEqual(updated["author"], "Chris")
        self.assertEqual(updated["content"], "This is the first post.")
        self.assertEqual(api.load_posts()[0], updated)
        self.assertEqual(self.client.put("/api/posts/99", json={"title": "X"}).status_code, 404)
        self.assertEqual(self.client.put("/api/posts/1", json={"author": ""}).status_code, 400)

    def test_delete_persists_and_returns_404_for_unknown_id(self):
        response = self.client.delete("/api/posts/1")
        self.assertEqual(response.status_code, 200)
        self.assertEqual([post["id"] for post in api.load_posts()], [2])
        self.assertEqual(self.client.delete("/api/posts/1").status_code, 404)

    def test_search_supports_legacy_and_combined_list_query(self):
        by_title = self.client.get("/api/posts/search?title=FIRST")
        self.assertEqual([post["id"] for post in by_title.get_json()], [1])
        by_author = self.client.get("/api/posts/search?search=bob")
        self.assertEqual([post["id"] for post in by_author.get_json()], [2])
        combined = self.client.get("/api/posts?search=post&sort=date&direction=desc")
        self.assertEqual([post["id"] for post in combined.get_json()], [2, 1])

    def test_sorting_validates_options(self):
        ascending = self.client.get("/api/posts?sort=title")
        self.assertEqual([post["id"] for post in ascending.get_json()], [1, 2])
        descending = self.client.get("/api/posts?sort=author&direction=desc")
        self.assertEqual([post["id"] for post in descending.get_json()], [2, 1])
        self.assertEqual(self.client.get("/api/posts?sort=id").status_code, 400)
        self.assertEqual(self.client.get("/api/posts?direction=sideways").status_code, 400)

    def test_invalid_storage_returns_json_error(self):
        api.POSTS_FILE.write_text("{broken", encoding="utf-8")
        response = self.client.get("/api/posts")
        self.assertEqual(response.status_code, 500)
        self.assertIn("error", response.get_json())
        api.POSTS_FILE.write_text('[{"id": 1}]', encoding="utf-8")
        self.assertEqual(self.client.get("/api/posts").status_code, 500)

    def test_swagger_documentation_is_available(self):
        spec = self.client.get("/static/masterblog.json")
        try:
            self.assertEqual(spec.status_code, 200)
            self.assertIn("/api/posts/{post_id}", spec.get_json()["paths"])
        finally:
            spec.close()
        docs = self.client.get("/api/docs/")
        try:
            self.assertEqual(docs.status_code, 200)
            self.assertIn(b"swagger-ui", docs.data)
        finally:
            docs.close()


class FrontendSmokeTests(unittest.TestCase):
    def test_template_and_javascript_include_extended_features(self):
        html = (PROJECT_ROOT / "frontend" / "templates" / "index.html").read_text(encoding="utf-8")
        javascript = (PROJECT_ROOT / "frontend" / "static" / "main.js").read_text(encoding="utf-8")
        for marker in ("post-author", "post-date", "search-query", "sort-field"):
            self.assertIn(marker, html)
        self.assertIn("URLSearchParams", javascript)
        self.assertIn("textContent = post.title", javascript)


if __name__ == "__main__":
    unittest.main()
