"""Regression cases for the token interchange contract and CSS adapter."""
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
spec = importlib.util.spec_from_file_location("token_contract_api", ROOT / "scripts/reference-ui.py")
api = importlib.util.module_from_spec(spec)
spec.loader.exec_module(api)
import gallery


class TokenContractTest(unittest.TestCase):
    def test_all_standard_value_types_have_positive_examples(self):
        color = {"colorSpace": "srgb", "components": [0, 0, 0], "alpha": 0.72}
        size = {"value": 1, "unit": "px"}
        duration = {"value": 100, "unit": "ms"}
        values = {"color": color, "dimension": size, "fontFamily": ["system-ui"], "fontWeight": 400,
            "duration": duration, "cubicBezier": [0, 0, 1, 1], "number": 1, "strokeStyle": "solid",
            "border": {"color": color, "width": size, "style": "solid"},
            "transition": {"duration": duration, "delay": duration, "timingFunction": [0, 0, 1, 1]},
            "shadow": {"color": color, "offsetX": size, "offsetY": size, "blur": size, "spread": size},
            "gradient": [{"color": color, "position": 0}, {"color": color, "position": 1}],
            "typography": {"fontFamily": ["system-ui"], "fontSize": size, "fontWeight": 400,
                           "letterSpacing": size, "lineHeight": 1.5}}
        self.assertEqual(api.validate_tokens({kind: {"$type": kind, "$value": value}
                                             for kind, value in values.items()}), 13)

    def test_modified_schema_cannot_report_a_pass(self):
        module = api.token_contract_module()
        module.schema_validator.cache_clear()
        self.addCleanup(module.schema_validator.cache_clear)
        with tempfile.TemporaryDirectory() as temporary:
            changed = Path(temporary) / "schema.json"
            changed.write_text('{}', encoding="utf-8")
            with patch.object(module, "SCHEMA", changed):
                with self.assertRaisesRegex(api.UserError, "schema hash"):
                    api.validate_tokens({})

    def test_malformed_values_rejected_by_type(self):
        cases = [
            ("color", "#ffffff"),
            ("color", {"colorSpace": "srgb", "components": ["red", 0, 0]}),
            ("dimension", "12px"),
            ("dimension", {"value": 12, "unit": "ms"}),
            ("duration", {"value": 12, "unit": "px"}),
            ("number", True),
            ("fontWeight", 5000),
            ("fontFamily", 12),
        ]
        for kind, value in cases:
            with self.subTest(kind=kind, value=value):
                with self.assertRaises(api.UserError):
                    api.validate_tokens({"bad": {"$type": kind, "$value": value}})

    def test_inherited_and_resolved_values_are_checked(self):
        cases = [
            {"group": {"$type": "number", "bad": {"$value": False}}},
            {"family": {"$type": "fontFamily", "$value": ["Example", "{n}"]},
             "n": {"$type": "number", "$value": 12}},
            {"shadow": {"$type": "shadow", "$value": {"color": "{n}", "offsetX": {"value": 0, "unit": "px"},
                "offsetY": {"value": 0, "unit": "px"}, "blur": {"value": 0, "unit": "px"},
                "spread": {"value": 0, "unit": "px"}}}, "n": {"$type": "number", "$value": 1}},
        ]
        for document in cases:
            with self.subTest(document=document):
                with self.assertRaises(api.UserError):
                    api.validate_tokens(document)

    def test_metadata_and_unknown_features_cannot_disappear(self):
        cases = [
            {"native": {"$type": "number", "$value": 17, "unit": "pt"}},
            {"group": {"$root": {"$type": "number", "$value": 1},
                       "other": {"$type": "number", "$value": 2}}},
            {"group": {"$extends": "{base}"}},
            {"ref": {"$type": "number", "$ref": "#/base/$value"}},
            {"bad": {"$type": "number", "$value": 1, "$typo": True}},
        ]
        for document in cases:
            with self.subTest(document=document):
                with self.assertRaises(api.UserError):
                    api.validate_tokens(document)

    def test_valid_typed_aliases_and_native_metadata_preserve_count(self):
        document = {
            "number": {"$type": "number", "$value": 17,
                       "$extensions": {"org.example.native": {"unit": "pt"}}},
            "alias": {"$value": "{number}"},
            "color": {"$type": "color", "$value": {
                "colorSpace": "srgb", "components": [0, 0, 0], "alpha": 0.72}},
            "family": {"$type": "fontFamily", "$value": ["Example", "system-ui", "sans-serif"]},
        }
        before = json.dumps(document)
        with patch("socket.create_connection", side_effect=AssertionError("Network access during validation")):
            self.assertEqual(api.validate_tokens(document), 4)
        self.assertEqual(json.dumps(document), before)

    def test_css_generic_families_stay_keywords(self):
        document = {"font": {"$type": "fontFamily",
            "$value": ["Helvetica Neue", "system-ui", "sans-serif", "ui-rounded"],
            "$extensions": {"reference-ui": {"css_name": "--font"}}}}
        css = gallery.token_css(document, api)
        self.assertIn('--font:"Helvetica Neue",system-ui,sans-serif,ui-rounded;', css)

    def test_css_export_rejects_malformed_opted_in_values(self):
        document = {"space": {"$type": "dimension", "$value": {"value": True, "unit": "ms"},
            "$extensions": {"reference-ui": {"css_name": "--space"}}}}
        with self.assertRaises(api.UserError):
            gallery.token_css(document, api)

    def test_css_export_preserves_resolved_values_and_alpha(self):
        document = {"base": {"$type": "fontFamily", "$value": ["Example", "sans-serif"]},
            "font": {"$value": "{base}",
                     "$extensions": {"reference-ui": {"css_name": "--font"}}},
            "source": {"$type": "color", "$value": {"colorSpace": "srgb", "components": [0, 0, 0], "alpha": 0.72}},
            "color": {"$value": "{source}", "$extensions": {"reference-ui": {"css_name": "--color"}}}}
        css = gallery.token_css(document, api)
        self.assertIn('--font:"Example",sans-serif;', css)
        self.assertIn('--color:color(srgb 0 0 0 / 0.72);', css)

    def test_css_adapter_rejects_ambiguous_extension_data(self):
        for extension in [[], {"css_name": []}, {"css_name": "--x", "theme": []}]:
            document = {"number": {"$type": "number", "$value": 1,
                                    "$extensions": {"reference-ui": extension}}}
            with self.subTest(extension=extension):
                with self.assertRaises(api.UserError):
                    gallery.token_css(document, api)
        duplicate = {name: {"$type": "number", "$value": 1,
                           "$extensions": {"reference-ui": {"css_name": "--same"}}}
                     for name in ("first", "second")}
        with self.assertRaisesRegex(api.UserError, "Duplicate CSS"):
            gallery.token_css(duplicate, api)

    def test_alias_graph_failures_remain_errors(self):
        for document in [
            {"a": {"$type": "number", "$value": "{missing}"}},
            {"a": {"$value": "{b}"}, "b": {"$value": "{a}"}},
            {"n": {"$type": "number", "$value": 1},
             "a": {"$type": "fontWeight", "$value": "{n}"}},
        ]:
            with self.subTest(document=document):
                with self.assertRaises(api.UserError):
                    api.validate_tokens(document)


if __name__ == "__main__":
    unittest.main()
