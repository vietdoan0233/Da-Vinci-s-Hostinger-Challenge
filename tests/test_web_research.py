import os
import sys
from types import SimpleNamespace
import unittest
from unittest.mock import call, patch, Mock

from app import web_research


class WebResearchTests(unittest.TestCase):
    def test_live_search_and_scrape_are_source_linked(self):
        scraped = (
            "# Report\n\nThe published figures were revised after the first release. "
            "The agency says the updated dataset includes additional regions and a "
            "different reporting window, which changes the comparison."
        )

        def oxylabs(endpoint, payload, timeout=45):
            if endpoint == "search":
                return {
                    "results": [
                        {"title": "First report", "url": "https://one.example/report", "outline": "Search outline"},
                        {"title": "Duplicate domain", "url": "https://www.one.example/other"},
                        {"title": "Second report", "url": "https://two.example/report"},
                    ]
                }
            return {"results": [{"markdown": scraped}]}

        extraction = {
            "quote": "The agency revised its figures",
            "claim": "The agency changed its published figures.",
            "search_query": "agency revised published figures",
        }
        summary = {
            "summary": {"text": "The agency updated the figures and explained why.", "source_ids": ["S1", "S999"]},
            "perspectives": [
                {"label": "qualifies", "text": "The comparison uses a different reporting window.", "source_ids": ["S2"]},
                {"label": "challenges", "text": "Invented citation.", "source_ids": ["S999"]},
            ],
            "uncertainties": [
                {"text": "The pages do not show whether the revision affects every region.", "source_ids": ["S1"]}
            ],
        }

        with patch.object(web_research, "_chat_json", side_effect=[extraction, summary]), \
             patch.object(web_research, "_oxylabs_post", side_effect=oxylabs) as request:
            result = web_research.analyze("The agency revised its figures yesterday.")

        self.assertEqual(result["status"], "ready")
        self.assertEqual([source["id"] for source in result["sources"]], ["S1", "S2"])
        self.assertTrue(all(source["scraped"] for source in result["sources"]))
        self.assertEqual(result["summary"]["source_ids"], ["S1"])
        self.assertEqual(len(result["perspectives"]), 1)
        self.assertEqual(result["perspectives"][0]["source_ids"], ["S2"])
        self.assertEqual(request.call_args_list[0], call(
            "search",
            {"query": "agency revised published figures", "max_results": web_research.MAX_SEARCH_RESULTS},
        ))
        self.assertEqual(request.call_count, 3)  # one search and two full-page reads
        self.assertNotIn("_content", result["sources"][0])

    def test_unverifiable_quote_stops_before_live_search(self):
        with patch.object(web_research, "_chat_json", return_value={
            "quote": "A quote that is not in the post",
            "claim": "A claim",
            "search_query": "some query",
        }), patch.object(web_research, "_oxylabs_post") as request:
            result = web_research.analyze("The supplied post contains another statement.")

        self.assertEqual(result["status"], "no_checkable_claim")
        self.assertIsNone(result["claim"])
        request.assert_not_called()

    def test_skeletal_page_retries_once_with_javascript_rendering(self):
        source = {
            "id": "S1", "url": "https://news.example/report", "title": "Report",
            "domain": "news.example", "excerpt": "", "scraped": False, "_content": "",
        }
        with patch.object(web_research, "_oxylabs_post", side_effect=[
            {"results": [{"markdown": "shell"}]},
            {"results": [{"markdown": "A rendered public report with enough content to read, compare with other pages, and summarize clearly for the reader."}]},
        ]) as request:
            web_research._scrape_source(source, "public report")

        self.assertTrue(source["scraped"])
        self.assertEqual(request.call_args_list[1], call(
            "scrape",
            {"url": source["url"], "output": ["markdown"], "run_js": True},
            timeout=150,
        ))

    def test_transport_retries_server_errors_but_maps_bad_key_without_retry(self):
        class Response:
            def __init__(self, status_code, data):
                self.status_code = status_code
                self._data = data

            def json(self):
                return self._data

        httpx_stub = SimpleNamespace(
            post=Mock(side_effect=[Response(503, {}), Response(200, {"state": "done"})]),
            HTTPError=type("HTTPError", (Exception,), {}),
        )
        with patch.dict(sys.modules, {"httpx": httpx_stub}), \
             patch.dict(os.environ, {"OXYLABS_WEB_API_KEY": "test-key"}), \
             patch.object(web_research.time, "sleep"):
            result = web_research._oxylabs_post("search", {"query": "test"})

        self.assertEqual(result, {"state": "done"})
        self.assertEqual(httpx_stub.post.call_count, 2)
        self.assertEqual(
            httpx_stub.post.call_args.kwargs["headers"]["Authorization"],
            "Bearer test-key",
        )

        bad_key_httpx = SimpleNamespace(
            post=Mock(return_value=Response(401, {})),
            HTTPError=type("HTTPError", (Exception,), {}),
        )
        with patch.dict(sys.modules, {"httpx": bad_key_httpx}), \
             patch.dict(os.environ, {"OXYLABS_WEB_API_KEY": "bad-key"}):
            with self.assertRaisesRegex(web_research.ResearchError, "rejected"):
                web_research._oxylabs_post("search", {"query": "test"})
        self.assertEqual(bad_key_httpx.post.call_count, 1)

    def test_only_public_https_source_urls_are_eligible(self):
        self.assertTrue(web_research._public_https_url("https://news.example/story"))
        self.assertFalse(web_research._public_https_url("http://news.example/story"))
        self.assertFalse(web_research._public_https_url("https://127.0.0.1/private"))
        self.assertFalse(web_research._public_https_url("https://localhost/private"))
        self.assertFalse(web_research._public_https_url("https://person:secret@news.example/story"))


if __name__ == "__main__":
    unittest.main()
