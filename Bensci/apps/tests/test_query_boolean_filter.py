from __future__ import annotations

import unittest

from apps.services.query_planner import QueryPlan, build_query_boolean_filter


class QueryBooleanFilterTests(unittest.TestCase):
    def test_structured_query_uses_strict_boolean_matching(self) -> None:
        query = '("temporal analysis of products" OR TAP) AND ("Au/SBA-15")'
        plan = QueryPlan(
            raw_input=query,
            must_terms=[],
            should_terms=[],
            exclude_terms=[],
            phrases=[],
            used_ai=False,
            passthrough_query=query,
        )

        query_filter = build_query_boolean_filter(plan)

        self.assertIsNotNone(query_filter)
        assert query_filter is not None
        self.assertTrue(query_filter.matches("TAP pulse experiment on Au/SBA-15 catalyst"))
        self.assertTrue(
            query_filter.matches("Temporal analysis of products over an Au/SBA-15 catalyst")
        )
        self.assertFalse(query_filter.matches("TAP pulse experiment on gold catalyst"))
        self.assertFalse(query_filter.matches("Au/SBA-15 catalyst preparation study"))

    def test_ai_plan_terms_become_default_boolean_filter(self) -> None:
        plan = QueryPlan(
            raw_input="tap microkinetic but not review",
            must_terms=["microkinetic"],
            should_terms=["TAP", "temporal analysis of products"],
            exclude_terms=["review"],
            phrases=[],
            used_ai=True,
            passthrough_query=None,
        )

        query_filter = build_query_boolean_filter(plan)

        self.assertIsNotNone(query_filter)
        assert query_filter is not None
        self.assertTrue(query_filter.matches("Microkinetic TAP reactor study"))
        self.assertTrue(query_filter.matches("Microkinetic temporal analysis of products study"))
        self.assertFalse(query_filter.matches("TAP reactor study"))
        self.assertFalse(query_filter.matches("Microkinetic TAP review"))

    def test_plain_passthrough_text_does_not_force_unstructured_filter(self) -> None:
        plan = QueryPlan(
            raw_input="帮我找近五年 TAP 催化相关文献",
            must_terms=[],
            should_terms=[],
            exclude_terms=[],
            phrases=[],
            used_ai=False,
            passthrough_query="帮我找近五年 TAP 催化相关文献",
        )

        self.assertIsNone(build_query_boolean_filter(plan))

    def test_single_keyword_query_becomes_default_filter(self) -> None:
        plan = QueryPlan(
            raw_input="TAP",
            must_terms=[],
            should_terms=[],
            exclude_terms=[],
            phrases=[],
            used_ai=False,
            passthrough_query="TAP",
        )

        query_filter = build_query_boolean_filter(plan)

        self.assertIsNotNone(query_filter)
        assert query_filter is not None
        self.assertTrue(query_filter.matches("TAP reactor kinetics"))
        self.assertFalse(query_filter.matches("microkinetic reactor kinetics"))

    def test_field_wrapped_structured_query_ignores_wrapper_tokens(self) -> None:
        query = 'TITLE-ABS-KEY(TAP AND microkinetic) AND NOT review[Title/Abstract]'
        plan = QueryPlan(
            raw_input=query,
            must_terms=[],
            should_terms=[],
            exclude_terms=[],
            phrases=[],
            used_ai=False,
            passthrough_query=query,
        )

        query_filter = build_query_boolean_filter(plan)

        self.assertIsNotNone(query_filter)
        assert query_filter is not None
        self.assertTrue(query_filter.matches("TAP microkinetic reactor study"))
        self.assertFalse(query_filter.matches("TAP reactor study"))
        self.assertFalse(query_filter.matches("TAP microkinetic review"))


if __name__ == "__main__":
    unittest.main()
