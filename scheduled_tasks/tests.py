import base64
import unittest

from .github_markdown_service import GitHubMarkdownService


class FakeResponse:
    def __init__(self, payload, status_code=200):
        self.payload = payload
        self.status_code = status_code

    def json(self):
        return self.payload


class FakeGitHubGet:
    def __call__(self, url, headers=None, params=None, timeout=20):
        _ = (headers, params, timeout)
        if "/git/trees/" in url:
            return FakeResponse({
                "tree": [
                    {"path": "README.md", "type": "blob", "size": 100, "sha": "sha1"},
                    {"path": "notes/a.md", "type": "blob", "size": 200, "sha": "sha2"},
                    {"path": "notes/raw.txt", "type": "blob", "size": 50, "sha": "sha3"},
                    {"path": "notes", "type": "tree", "sha": "sha4"},
                ]
            })
        if url.endswith("/contents"):
            return FakeResponse([
                {"name": "notes", "path": "notes", "type": "dir", "size": 0, "sha": "sha4", "html_url": "https://example.com/notes"},
                {"name": "README.md", "path": "README.md", "type": "file", "size": 100, "sha": "sha1", "html_url": "https://example.com/readme", "download_url": "https://example.com/raw"},
            ])
        if url.endswith("/contents/README.md"):
            content = base64.b64encode("# Title\n\ncontent".encode("utf-8")).decode("utf-8")
            return FakeResponse({
                "name": "README.md",
                "path": "README.md",
                "type": "file",
                "size": 16,
                "sha": "sha1",
                "content": content,
                "html_url": "https://example.com/readme",
                "download_url": "https://example.com/raw",
            })
        return FakeResponse({}, status_code=404)


class GitHubMarkdownServiceTests(unittest.TestCase):
    def setUp(self):
        self.service = GitHubMarkdownService(
            repo="https://github.com/huang1125677925/mybook",
            branch="main",
            token="test-token",
            request_get=FakeGitHubGet(),
        )

    def test_list_directory_marks_markdown_files(self):
        result = self.service.list_directory("")

        self.assertEqual(result["repo"], "huang1125677925/mybook")
        self.assertEqual(result["count"], 2)
        readme = [item for item in result["items"] if item["path"] == "README.md"][0]
        self.assertTrue(readme["is_markdown"])

    def test_list_markdown_files_filters_recursive_tree(self):
        result = self.service.list_markdown_files(prefix="notes", recursive=True)

        self.assertEqual(result["count"], 1)
        self.assertEqual(result["files"][0]["path"], "notes/a.md")

    def test_get_markdown_content_decodes_base64(self):
        result = self.service.get_markdown_content("README.md")

        self.assertEqual(result["content"], "# Title\n\ncontent")
        self.assertFalse(result["truncated"])

    def test_rejects_unsafe_path(self):
        with self.assertRaises(ValueError):
            self.service.get_markdown_content("../README.md")
