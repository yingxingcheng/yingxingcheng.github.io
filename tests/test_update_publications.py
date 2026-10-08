import copy
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

import requests

import update_publications as updater

DOI = "10.1234/new"


def metadata(doi=DOI, **overrides):
    result = {
        "DOI": doi,
        "type": "journal-article",
        "title": ["A new publication"],
        "container-title": ["Example Journal"],
        "author": [
            {"given": "YingXing", "family": "Cheng", "ORCID": f"https://orcid.org/{updater.ORCID}"}
        ],
        "published": {"date-parts": [[2026, 8, 1]]},
        "volume": "3",
        "article-number": "123",
    }
    result.update(overrides)
    return result


def content():
    citation = updater.crossref_to_pub(metadata("10.1234/old"), "10.1234/old")
    citation["title"] = "Curated \\(\\omega\\) title"
    citation["year"] = "2025"
    return {
        lang: {"sections": {"publications": {"items": [copy.deepcopy(citation)]}}}
        for lang in ("en", "zh")
    }


def response(payload=None, error=None):
    result = Mock()
    result.raise_for_status.side_effect = error
    result.json.return_value = payload
    return result


def orcid_work(doi, relationship="self", work_type="journal-article"):
    return {
        "work-summary": [
            {
                "type": work_type,
                "external-ids": {
                    "external-id": [
                        {
                            "external-id-type": "doi",
                            "external-id-value": doi,
                            "external-id-relationship": relationship,
                        }
                    ]
                },
            }
        ]
    }


class SourcesTest(unittest.TestCase):
    def test_normalize_doi_variants(self):
        for value in (
            "10.1234/ABC",
            " DOI:10.1234/abc ",
            "https://doi.org/10.1234/ABC",
            "http://dx.doi.org/10.1234/abc",
            "https://doi.org/10.1234%2Fabc",
        ):
            with self.subTest(value=value):
                self.assertEqual(updater.normalize_doi(value), "10.1234/abc")
        for value in (
            None,
            "",
            "https://evil.test/10.1234/abc",
            "10.1234/a b",
            "not-a-doi",
            "javascript:alert(1)",
        ):
            self.assertIsNone(updater.normalize_doi(value))

    def test_orcid_deduplicates_and_ignores_related_or_non_articles(self):
        session = Mock()
        session.get.return_value = response(
            {
                "group": [
                    orcid_work(DOI),
                    orcid_work("https://doi.org/10.1234/NEW"),
                    orcid_work("10.1234/related", "part-of"),
                    orcid_work("10.1234/data", work_type="data-set"),
                ]
            }
        )
        self.assertEqual(updater.fetch_orcid_dois(session), {DOI})

    def test_orcid_malformed_is_not_empty_success(self):
        session = Mock()
        for payload in ({}, {"group": None}, {"group": [orcid_work("bogus")]}):
            session.get.return_value = response(payload)
            with self.assertRaises(updater.PublicationError):
                updater.fetch_orcid_dois(session)

    def test_crossref_requires_exact_author_orcid_not_name(self):
        session = Mock()
        unrelated = metadata("10.1234/unrelated", author=[{"given": "YingXing", "family": "Cheng"}])
        wrong_orcid = metadata(
            "10.1234/wrong",
            author=[{"family": "Cheng", "ORCID": "https://orcid.org/0000-0000-0000-0000"}],
        )
        session.get.return_value = response(
            {"message": {"items": [metadata(), unrelated, wrong_orcid]}}
        )
        self.assertEqual(set(updater.fetch_crossref_works(session)), {DOI})
        self.assertIn(f"orcid:{updater.ORCID}", session.get.call_args.kwargs["params"]["filter"])

    def test_crossref_pagination(self):
        session = Mock()
        session.get.side_effect = [
            response({"message": {"items": [metadata()] * 1000, "next-cursor": "next-page"}}),
            response({"message": {"items": [metadata("10.1234/last")]}}),
        ]
        self.assertEqual(set(updater.fetch_crossref_works(session)), {DOI, "10.1234/last"})
        self.assertEqual(session.get.call_args.kwargs["params"]["cursor"], "next-page")

    def test_pagination_loop_fails(self):
        session = Mock()
        session.get.return_value = response(
            {"message": {"items": [metadata()] * 1000, "next-cursor": "same"}}
        )
        with self.assertRaises(updater.PublicationError):
            updater.fetch_crossref_works(session)

    def test_http_and_invalid_json_fail_loudly(self):
        session = Mock()
        session.get.return_value = response(error=requests.HTTPError("429 Too Many Requests"))
        with self.assertRaises(updater.PublicationError):
            updater.get_json(session, "https://example.org")
        session.get.return_value = response()
        session.get.return_value.json.side_effect = ValueError("invalid JSON")
        with self.assertRaises(updater.PublicationError):
            updater.get_json(session, "https://example.org")

    def test_retry_policy(self):
        with updater.make_session() as session:
            retries = session.get_adapter("https://").max_retries
            self.assertEqual(retries.total, 3)
            self.assertIn(429, retries.status_forcelist)
            self.assertEqual(retries.allowed_methods, {"GET"})

    def test_crossref_metadata_doi_must_match(self):
        session = Mock()
        session.get.return_value = response({"message": metadata("10.1234/wrong")})
        with self.assertRaises(updater.PublicationError):
            updater.fetch_crossref(session, DOI)

    def test_metadata_is_plain_text_and_has_required_fields(self):
        pub = updater.crossref_to_pub(
            metadata(
                title=["An <i>interesting</i>\n paper"],
                **{"container-title": ["Crystal Growth &amp; Design"]},
            ),
            DOI,
        )
        self.assertEqual(pub["title"], "An interesting paper")
        self.assertEqual(pub["journal"], "Crystal Growth & Design")
        self.assertEqual(pub["pages"], "123")
        self.assertEqual(pub["source"], "crossref")
        for overrides in ({"title": []}, {"author": []}, {"published": {}}):
            with self.assertRaises(updater.PublicationError):
                updater.crossref_to_pub(metadata(**overrides), DOI)

    def test_invalid_metadata_shapes_and_non_articles_fail(self):
        for overrides in (
            {"title": "A complete title"},
            {"container-title": "Journal"},
            {"container-title": []},
            {"type": "dataset"},
        ):
            with self.subTest(overrides=overrides), self.assertRaises(updater.PublicationError):
                updater.crossref_to_pub(metadata(**overrides), DOI)

    def test_orcid_id_must_be_canonical(self):
        self.assertFalse(
            updater.has_author_orcid(
                metadata(author=[{"ORCID": f"https://evil.test/{updater.ORCID}"}])
            )
        )
        self.assertTrue(updater.has_author_orcid(metadata(author=[{"ORCID": updater.ORCID}])))

    def test_missing_orcid_relationship_is_not_self(self):
        work = orcid_work(DOI)
        del work["work-summary"][0]["external-ids"]["external-id"][0]["external-id-relationship"]
        session = Mock()
        session.get.return_value = response({"group": [work]})
        self.assertEqual(updater.fetch_orcid_dois(session), set())

    def test_malformed_orcid_groups_fail(self):
        session = Mock()
        for group in ({}, {"work-summary": [{}]}):
            session.get.return_value = response({"group": [group]})
            with self.subTest(group=group), self.assertRaises(updater.PublicationError):
                updater.fetch_orcid_dois(session)

    def test_empty_cleaned_authors_fail(self):
        with self.assertRaises(updater.PublicationError):
            updater.crossref_to_pub(metadata(author=[{"name": "<i></i>"}] * 3), DOI)

    def test_date_fallback_and_organization_author(self):
        pub = updater.crossref_to_pub(
            metadata(
                published={},
                **{
                    "published-online": {"date-parts": [[2024]]},
                    "author": [{"name": "A Research Consortium"}],
                },
            ),
            DOI,
        )
        self.assertEqual(pub["year"], "2024")
        self.assertEqual(pub["authors"], "A Research Consortium")


class UpdateTest(unittest.TestCase):
    @patch.object(updater, "fetch_crossref_works", return_value={DOI: metadata()})
    @patch.object(updater, "fetch_orcid_dois", return_value={DOI, "10.1234/old"})
    def test_addition_in_both_languages_preserves_curated_and_is_idempotent(self, *_):
        original = content()
        snapshot = copy.deepcopy(original)
        result, counts, _ = updater.update_content(original, Mock())
        self.assertEqual(original, snapshot)
        self.assertEqual(counts, {"en": 1, "zh": 1})
        for lang in ("en", "zh"):
            pubs = result[lang]["sections"]["publications"]["items"]
            self.assertEqual(len(pubs), 2)
            self.assertEqual(pubs[0]["link"], f"https://doi.org/{DOI}")
            self.assertEqual(pubs[1], snapshot[lang]["sections"]["publications"]["items"][0])
        again, counts, _ = updater.update_content(result, Mock())
        self.assertEqual(again, result)
        self.assertEqual(counts, {"en": 0, "zh": 0})

    @patch.object(updater, "fetch_crossref_works", return_value={DOI: metadata()})
    @patch.object(updater, "fetch_orcid_dois", return_value={DOI})
    def test_missing_language_is_backfilled_without_overwriting_other(self, *_):
        original = content()
        custom = updater.crossref_to_pub(metadata(), DOI)
        custom["title"] = "Hand-edited English title"
        original["en"]["sections"]["publications"]["items"].append(custom)
        result, counts, _ = updater.update_content(original, Mock())
        self.assertEqual(counts, {"en": 0, "zh": 1})
        self.assertEqual(result["en"], original["en"])

    @patch.object(updater, "fetch_crossref", side_effect=updater.PublicationError("503"))
    @patch.object(updater, "fetch_crossref_works", return_value={DOI: metadata()})
    @patch.object(updater, "fetch_orcid_dois", return_value={DOI, "10.1234/zzz"})
    def test_partial_metadata_failure_does_not_mutate_content(self, *_):
        original = content()
        snapshot = copy.deepcopy(original)
        with self.assertRaises(updater.PublicationError):
            updater.update_content(original, Mock())
        self.assertEqual(original, snapshot)

    @patch.object(
        updater, "fetch_crossref_works", side_effect=updater.PublicationError("source unavailable")
    )
    @patch.object(updater, "fetch_orcid_dois", return_value={DOI})
    def test_incomplete_discovery_fails(self, *_):
        with self.assertRaises(updater.PublicationError):
            updater.update_content(content(), Mock())

    def run_main(self, result, check_only=False):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        root = Path(directory.name)
        file = root / "content.json"
        status = root / "status.json"
        original_bytes = json.dumps(content(), indent=2) + "\n"
        file.write_text(original_bytes)
        args = ["--content", str(file), "--status", str(status)]
        if check_only:
            args.append("--check-only")
        with patch.object(updater, "update_content", side_effect=result):
            code = updater.main(args)
        return code, file.read_text(), status, original_bytes

    def test_no_changes_leaves_content_bytes_untouched_and_records_success(self):
        code, actual, status, original = self.run_main(
            lambda *_: (content(), {"en": 0, "zh": 0}, {"orcid": 1, "crossref": 1})
        )
        self.assertEqual(code, 0)
        self.assertEqual(actual, original)
        self.assertIn("last_successful_check", json.loads(status.read_text()))

    def test_check_only_never_writes_files(self):
        code, actual, status, original = self.run_main(
            lambda *_: ({}, {"en": 1, "zh": 1}, {"orcid": 1, "crossref": 1}), check_only=True
        )
        self.assertEqual(code, 0)
        self.assertEqual(actual, original)
        self.assertFalse(status.exists())

    def test_failed_check_exits_nonzero_and_writes_nothing(self):
        code, actual, status, original = self.run_main(updater.PublicationError("timeout"))
        self.assertEqual(code, 1)
        self.assertEqual(actual, original)
        self.assertFalse(status.exists())


if __name__ == "__main__":
    unittest.main()
