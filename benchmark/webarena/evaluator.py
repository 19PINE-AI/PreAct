"""WebArena-compatible async evaluator.

Adapts the official WebArena evaluation harness (StringEvaluator,
URLEvaluator, HTMLContentEvaluator) to work with our async Playwright
environment. Uses the same matching logic as the upstream code.
"""

from __future__ import annotations

import html
import json
import logging
import re
import urllib.parse
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


class AsyncStringEvaluator:
    """String match evaluator — checks agent answer against reference."""

    @staticmethod
    def clean_answer(answer: str) -> str:
        answer = answer.strip()
        if answer.startswith("'") and answer.endswith("'"):
            answer = answer[1:-1]
        elif answer.startswith('"') and answer.endswith('"'):
            answer = answer[1:-1]
        return answer.lower()

    @staticmethod
    def exact_match(ref: str, pred: str) -> float:
        return float(
            AsyncStringEvaluator.clean_answer(pred)
            == AsyncStringEvaluator.clean_answer(ref)
        )

    @staticmethod
    def must_include(ref: str, pred: str, tokenize: bool = False) -> float:
        clean_ref = AsyncStringEvaluator.clean_answer(ref)
        clean_pred = AsyncStringEvaluator.clean_answer(pred)
        if tokenize and len(clean_ref) == 1:
            tok_pred = clean_pred.split()
            return float(clean_ref in tok_pred)
        return float(clean_ref in clean_pred)

    async def evaluate(
        self, config: dict, agent_answer: str
    ) -> float:
        pred = self.clean_answer(agent_answer)
        score = 1.0

        ref_answers = config["eval"].get("reference_answers", {})
        if not ref_answers:
            return 0.0

        for approach, value in ref_answers.items():
            if approach == "exact_match":
                score *= self.exact_match(ref=value, pred=pred)
            elif approach == "must_include":
                if isinstance(value, list):
                    for must_value in value:
                        score *= self.must_include(
                            ref=must_value, pred=pred,
                            tokenize=(len(value) == 1),
                        )
                else:
                    score *= self.must_include(ref=value, pred=pred)
            elif approach == "fuzzy_match":
                # For fuzzy match, do a relaxed string comparison
                # (avoid requiring OpenAI GPT-4 judge)
                if value == "N/A":
                    score *= self.exact_match(ref=value, pred=pred)
                elif isinstance(value, list):
                    for reference in value:
                        score *= self._relaxed_fuzzy(ref=reference, pred=pred)
                else:
                    score *= self._relaxed_fuzzy(ref=value, pred=pred)

        return score

    @staticmethod
    def _relaxed_fuzzy(ref: str, pred: str) -> float:
        """Relaxed fuzzy match without requiring LLM judge."""
        clean_ref = AsyncStringEvaluator.clean_answer(ref)
        clean_pred = AsyncStringEvaluator.clean_answer(pred)
        if clean_ref in clean_pred:
            return 1.0
        # Word overlap check
        ref_words = set(clean_ref.split())
        pred_words = set(clean_pred.split())
        if not ref_words:
            return 0.0
        overlap = len(ref_words & pred_words) / len(ref_words)
        return float(overlap >= 0.8)


class AsyncURLEvaluator:
    """URL match evaluator — checks current page URL against reference."""

    async def evaluate(
        self, config: dict, env: Any
    ) -> float:
        try:
            current_url = await env.get_page_url()
        except Exception:
            return 0.0

        ref_url_str = config["eval"].get("reference_url", "")
        if not ref_url_str:
            return 0.0

        current_url = current_url.rstrip("/")
        ref_urls = ref_url_str.split(" |OR| ")
        ref_urls = [u.rstrip("/") for u in ref_urls]

        matching_rule = config["eval"].get("url_note", "GOLD in PRED")
        if matching_rule == "GOLD in PRED":
            # Parse reference URLs
            ref_base_paths = []
            ref_queries: dict[str, set[str]] = {}
            for url in ref_urls:
                parsed = urllib.parse.urlparse(url)
                ref_base_paths.append(parsed.netloc + parsed.path)
                for k, v in urllib.parse.parse_qs(parsed.query).items():
                    ref_queries.setdefault(k, set()).update(v)

            # Parse current URL
            parsed_pred = urllib.parse.urlparse(current_url)
            pred_base = parsed_pred.netloc + parsed_pred.path
            pred_query = urllib.parse.parse_qs(parsed_pred.query)

            base_score = float(
                any(ref_bp in pred_base for ref_bp in ref_base_paths)
            )
            query_score = 1.0
            for k, possible_values in ref_queries.items():
                query_score *= float(
                    any(
                        pv in pred_query.get(k, [])
                        for pv in possible_values
                    )
                )
            return base_score * query_score

        return 0.0


class AsyncHTMLContentEvaluator:
    """HTML content evaluator — navigates to URLs and checks DOM elements.

    This is the most complex evaluator. It uses JS locators to extract
    page content and check against reference values.
    """

    def __init__(self, hostname: str = "localhost"):
        self._hostname = hostname

    async def evaluate(
        self, config: dict, env: Any
    ) -> float:
        targets = config["eval"].get("program_html", [])
        if not targets:
            return 1.0

        score = 1.0
        for target in targets:
            target_url: str = target["url"]

            # Resolve URL placeholders
            target_url = self._resolve_url(target_url, env)

            # Handle func: URLs
            if target_url.startswith("func"):
                try:
                    current_url = await env.get_page_url()
                    func_expr = target_url.split("func:")[1]
                    func_expr = func_expr.replace("__last_url__", current_url)
                    target_url = eval(func_expr)
                except Exception as e:
                    logger.warning("Failed to resolve func URL: %s", e)
                    score *= 0.0
                    continue

            locator: str = target["locator"]

            # Navigate to target URL if needed
            if target_url != "last":
                try:
                    await env.navigate(target_url)
                    await env.wait_ms(3000)
                except Exception as e:
                    logger.warning("Failed to navigate to %s: %s", target_url, e)
                    score *= 0.0
                    continue

            # Extract element content
            selected_element = ""
            if not locator.strip():
                try:
                    selected_element = await env.evaluate_js(
                        "() => document.body.innerHTML"
                    )
                except Exception:
                    pass
            elif locator.startswith("document.") or locator.startswith(
                "[...document."
            ):
                # Run prep actions if any
                if "prep_actions" in target:
                    for prep_action in target["prep_actions"]:
                        try:
                            await env.evaluate_js(f"() => {prep_action}")
                        except Exception:
                            pass
                try:
                    selected_element = str(
                        await env.evaluate_js(f"() => {locator}")
                    )
                    if not selected_element:
                        selected_element = ""
                except Exception:
                    selected_element = ""
            elif locator.startswith("func:"):
                # Helper function evaluation — handle common shopping functions
                selected_element = await self._eval_func_locator(
                    locator, env
                )
            else:
                logger.warning("Unknown locator: %s", locator)
                score *= 0.0
                continue

            selected_element = html.unescape(selected_element)

            # Check required contents
            required = target["required_contents"]
            if "exact_match" in required:
                cur_score = AsyncStringEvaluator.exact_match(
                    ref=required["exact_match"], pred=selected_element
                )
                score *= float(cur_score)
            elif "must_include" in required:
                must_include = required["must_include"]
                if isinstance(must_include, list):
                    for content in must_include:
                        content_or = content.split(" |OR| ")
                        cur_score = any(
                            AsyncStringEvaluator.must_include(
                                ref=c, pred=selected_element, tokenize=False
                            )
                            for c in content_or
                        )
                        score *= float(cur_score)
                else:
                    score *= float(
                        AsyncStringEvaluator.must_include(
                            ref=must_include, pred=selected_element
                        )
                    )

        return score

    def _resolve_url(self, url: str, env: Any) -> str:
        """Replace WebArena URL placeholders with actual URLs."""
        replacements = {
            "__SHOPPING_ADMIN__": f"http://{self._hostname}:7780",
            "__SHOPPING__": f"http://{self._hostname}:7770",
        }
        for placeholder, real_url in replacements.items():
            url = url.replace(placeholder, real_url)
        return url

    async def _eval_func_locator(
        self, locator: str, env: Any
    ) -> str:
        """Evaluate func: locators (shopping helper functions)."""
        func_str = locator.split("func:")[1]

        # Handle common Magento API helper functions
        if "shopping_get_sku_latest_review_author" in func_str:
            sku = re.search(r"'([^']+)'", func_str)
            if sku:
                return await self._shopping_get_review_author(sku.group(1))
        elif "shopping_get_sku_latest_review_rating" in func_str:
            sku = re.search(r"'([^']+)'", func_str)
            if sku:
                return await self._shopping_get_review_rating(sku.group(1))
        elif "shopping_get_latest_order_url" in func_str:
            return await self._shopping_get_latest_order_url()

        logger.warning("Unhandled func locator: %s", func_str)
        return ""

    async def _shopping_get_auth_token(self) -> str:
        """Get Magento admin API token."""
        import aiohttp
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"http://{self._hostname}:7770/rest/default/V1/integration/admin/token",
                json={"username": "admin", "password": "admin123"},
                headers={"content-type": "application/json"},
            ) as resp:
                return await resp.json()

    async def _shopping_get_review_author(self, sku: str) -> str:
        import aiohttp
        token = await self._shopping_get_auth_token()
        async with aiohttp.ClientSession() as session:
            async with session.get(
                f"http://{self._hostname}:7770/rest/V1/products/{sku}/reviews",
                headers={"Authorization": f"Bearer {token}"},
            ) as resp:
                reviews = await resp.json()
                if reviews:
                    return reviews[-1].get("nickname", "")
                return ""

    async def _shopping_get_review_rating(self, sku: str) -> str:
        import aiohttp
        token = await self._shopping_get_auth_token()
        async with aiohttp.ClientSession() as session:
            async with session.get(
                f"http://{self._hostname}:7770/rest/V1/products/{sku}/reviews",
                headers={"Authorization": f"Bearer {token}"},
            ) as resp:
                reviews = await resp.json()
                if reviews:
                    return str(reviews[-1]["ratings"][0]["percent"])
                return ""

    async def _shopping_get_latest_order_url(self) -> str:
        import aiohttp
        token = await self._shopping_get_auth_token()
        async with aiohttp.ClientSession() as session:
            params = {
                "searchCriteria[sortOrders][0][field]": "created_at",
                "searchCriteria[sortOrders][0][direction]": "DESC",
                "searchCriteria[pageSize]": "1",
            }
            async with session.get(
                f"http://{self._hostname}:7770/rest/V1/orders",
                params=params,
                headers={"Authorization": f"Bearer {token}"},
            ) as resp:
                data = await resp.json()
                order_id = int(data["items"][0]["increment_id"])
                return f"http://{self._hostname}:7770/sales/order/view/order_id/{order_id}/"


async def evaluate_webarena_task(
    config: dict,
    env: Any,
    agent_answer: str = "",
    hostname: str = "localhost",
) -> dict:
    """Run all evaluators for a WebArena task.

    Args:
        config: WebArena task config with eval criteria.
        env: Browser environment (async Playwright).
        agent_answer: Agent's text answer (for string_match tasks).
        hostname: Server hostname for URL resolution.

    Returns:
        Dict with score (0.0 or 1.0), and per-evaluator details.
    """
    eval_types = config["eval"].get("eval_types", [])
    if not eval_types:
        return {"score": 0.0, "details": {}}

    score = 1.0
    details = {}

    for eval_type in eval_types:
        if eval_type == "string_match":
            evaluator = AsyncStringEvaluator()
            cur_score = await evaluator.evaluate(config, agent_answer)
            details["string_match"] = cur_score
            score *= cur_score

        elif eval_type == "url_match":
            evaluator = AsyncURLEvaluator()
            cur_score = await evaluator.evaluate(config, env)
            details["url_match"] = cur_score
            score *= cur_score

        elif eval_type == "program_html":
            evaluator = AsyncHTMLContentEvaluator(hostname)
            cur_score = await evaluator.evaluate(config, env)
            details["program_html"] = cur_score
            score *= cur_score

    return {"score": score, "details": details}
