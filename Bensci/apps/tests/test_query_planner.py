from __future__ import annotations

import unittest
from unittest.mock import patch

from apps.services.query_planner import QueryPlan, build_provider_queries, plan_natural_language_query


class QueryPlannerProviderQueryTests(unittest.TestCase):
    def test_structured_passthrough_is_rewritten_per_provider(self) -> None:
        query = "TITLE-ABS-KEY(TAP AND microkinetic) AND NOT review[Title/Abstract]"
        plan = QueryPlan(
            raw_input=query,
            must_terms=[],
            should_terms=[],
            exclude_terms=[],
            phrases=[],
            used_ai=False,
            passthrough_query=query,
        )

        queries = build_provider_queries(plan, ["elsevier", "pubmed", "crossref", "openalex", "arxiv"])

        self.assertEqual(queries["elsevier"].query_field, "query")
        self.assertIn("TITLE-ABS-KEY(TAP)", queries["elsevier"].compiled_query)
        self.assertIn("TITLE-ABS-KEY(microkinetic)", queries["elsevier"].compiled_query)
        self.assertIn("NOT TITLE-ABS-KEY(review)", queries["elsevier"].compiled_query)

        self.assertEqual(queries["pubmed"].query_field, "term")
        self.assertIn("TAP[Title/Abstract]", queries["pubmed"].compiled_query)
        self.assertIn("microkinetic[Title/Abstract]", queries["pubmed"].compiled_query)
        self.assertIn("NOT review[Title/Abstract]", queries["pubmed"].compiled_query)

        self.assertEqual(queries["crossref"].query_field, "query.bibliographic")
        self.assertNotIn("TITLE-ABS-KEY", queries["crossref"].compiled_query)
        self.assertNotIn("[Title/Abstract]", queries["crossref"].compiled_query)
        self.assertIn("TAP", queries["crossref"].compiled_query)
        self.assertIn("microkinetic", queries["crossref"].compiled_query)

        self.assertEqual(queries["openalex"].query_field, "filter")
        self.assertIn("title_and_abstract.search:", queries["openalex"].compiled_query)
        self.assertNotIn("TITLE-ABS-KEY", queries["openalex"].compiled_query)
        self.assertNotIn("[Title/Abstract]", queries["openalex"].compiled_query)

        self.assertEqual(queries["arxiv"].query_field, "search_query")
        self.assertIn("ti:TAP", queries["arxiv"].compiled_query)
        self.assertIn("abs:TAP", queries["arxiv"].compiled_query)
        self.assertIn("ti:microkinetic", queries["arxiv"].compiled_query)
        self.assertIn("ANDNOT", queries["arxiv"].compiled_query)
        self.assertNotIn("AND NOT", queries["arxiv"].compiled_query)

    def test_context_terms_add_domain_scope_for_sparse_material_query(self) -> None:
        plan = QueryPlan(
            raw_input="U3O8",
            must_terms=["U3O8"],
            should_terms=[],
            exclude_terms=[],
            phrases=["U3O8"],
            used_ai=True,
            passthrough_query=None,
        )

        queries = build_provider_queries(
            plan,
            ["crossref", "openalex", "springer", "elsevier", "pubmed", "arxiv"],
            context_texts=[
                "查找采用 TAP 方法在 环境催化 领域研究 VOCs 反应，涉及 U3O8 催化体系的相关文献",
                "Environment catalysis",
                "VOCs",
            ],
        )

        self.assertEqual(queries["crossref"].domain_scope_name, "context_scope")
        self.assertIn('"temporal analysis of products"', queries["crossref"].compiled_query)
        self.assertIn("TAP", queries["crossref"].compiled_query)
        self.assertIn("catalysis", queries["crossref"].compiled_query)
        self.assertNotIn("TITLE-ABS-KEY", queries["crossref"].compiled_query)

        self.assertEqual(queries["openalex"].query_field, "filter")
        self.assertIn("title_and_abstract.search:", queries["openalex"].compiled_query)
        self.assertIn("TAP", queries["openalex"].compiled_query)
        self.assertNotIn("[Title/Abstract]", queries["openalex"].compiled_query)

        self.assertEqual(queries["springer"].query_field, "q")
        self.assertIn("catalysis", queries["springer"].compiled_query)
        self.assertNotIn("TITLE-ABS-KEY", queries["springer"].compiled_query)

        self.assertEqual(queries["elsevier"].query_field, "query")
        self.assertIn("TITLE-ABS-KEY(U3O8)", queries["elsevier"].compiled_query)
        self.assertIn("TITLE-ABS-KEY(TAP)", queries["elsevier"].compiled_query)
        self.assertIn("TITLE-ABS-KEY(catalysis)", queries["elsevier"].compiled_query)

        self.assertEqual(queries["pubmed"].query_field, "term")
        self.assertIn("U3O8[Title/Abstract]", queries["pubmed"].compiled_query)
        self.assertIn("TAP[Title/Abstract]", queries["pubmed"].compiled_query)
        self.assertIn("catalysis[Title/Abstract]", queries["pubmed"].compiled_query)

        self.assertEqual(queries["arxiv"].query_field, "search_query")
        self.assertIn("ti:U3O8", queries["arxiv"].compiled_query)
        self.assertIn("abs:U3O8", queries["arxiv"].compiled_query)
        self.assertIn("ti:TAP", queries["arxiv"].compiled_query)
        self.assertIn("abs:TAP", queries["arxiv"].compiled_query)

    def test_domain_objective_guided_ai_plan_compiles_without_structured_scope_profiles(self) -> None:
        with patch(
            "apps.services.query_planner._ai_plan",
            return_value=QueryPlan(
                raw_input="U3O8",
                must_terms=["U3O8"],
                should_terms=["TAP", "catalysis", "microkinetic"],
                exclude_terms=[],
                phrases=["U3O8"],
                used_ai=True,
                passthrough_query=None,
                domain_objective=(
                    "Focus on TAP-related literature in environmental catalysis and energy catalysis, "
                    "especially studies on catalytic microkinetics and reaction mechanisms."
                ),
            ),
        ):
            plan = plan_natural_language_query(
                "U3O8",
                domain_objective=(
                    "Focus on TAP-related literature in environmental catalysis and energy catalysis, "
                    "especially studies on catalytic microkinetics and reaction mechanisms."
                ),
            )

        queries = build_provider_queries(plan, ["elsevier", "pubmed", "crossref", "openalex", "arxiv"])

        self.assertEqual(plan.domain_objective, (
            "Focus on TAP-related literature in environmental catalysis and energy catalysis, "
            "especially studies on catalytic microkinetics and reaction mechanisms."
        ))
        self.assertTrue(plan.used_ai)
        self.assertEqual(plan.must_terms, ["U3O8"])
        self.assertEqual(plan.should_terms, ["TAP", "catalysis", "microkinetic"])
        self.assertEqual(queries["elsevier"].domain_scope_name, "")
        self.assertIn("TITLE-ABS-KEY(U3O8)", queries["elsevier"].compiled_query)
        self.assertIn("TITLE-ABS-KEY(TAP)", queries["elsevier"].compiled_query)
        self.assertIn("TITLE-ABS-KEY(catalysis)", queries["elsevier"].compiled_query)

        self.assertEqual(queries["pubmed"].query_field, "term")
        self.assertIn("U3O8[Title/Abstract]", queries["pubmed"].compiled_query)
        self.assertIn("TAP[Title/Abstract]", queries["pubmed"].compiled_query)

        self.assertEqual(queries["crossref"].domain_scope_name, "")
        self.assertIn("microkinetic", queries["crossref"].compiled_query)

        self.assertEqual(queries["openalex"].query_field, "filter")
        self.assertIn("title_and_abstract.search:", queries["openalex"].compiled_query)
        self.assertIn("TAP", queries["openalex"].compiled_query)

        self.assertEqual(queries["arxiv"].query_field, "search_query")
        self.assertIn("ti:TAP", queries["arxiv"].compiled_query)
        self.assertIn("abs:TAP", queries["arxiv"].compiled_query)


if __name__ == "__main__":
    unittest.main()
