"""ActionEngine Crawling Agent — untargeted app exploration.

Reimplements the crawling phase from the ActionEngine paper:
explores a GUI application broadly to build a state-machine graph
BEFORE any specific task is executed.
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class CrawlState:
    """A state discovered during crawling."""

    state_id: str
    url: str = ""
    dom_hash: str = ""
    interactive_elements: list[dict[str, Any]] = field(default_factory=list)
    screenshot_data: bytes | None = None

    def __hash__(self):
        return hash(self.state_id)


@dataclass
class CrawlTransition:
    """A transition discovered during crawling."""

    from_state: str
    to_state: str
    action: str  # "click", "type", etc.
    target_xpath: str
    element_text: str = ""


@dataclass
class CrawlGraph:
    """The state-machine graph built by crawling."""

    states: dict[str, CrawlState] = field(default_factory=dict)
    transitions: list[CrawlTransition] = field(default_factory=list)

    @property
    def state_count(self) -> int:
        return len(self.states)

    @property
    def transition_count(self) -> int:
        return len(self.transitions)


class AppCrawler:
    """Untargeted app exploration to build a state-machine graph.

    This is ActionEngine's approach: explore the app broadly,
    clicking on interactive elements and recording state changes.
    """

    def __init__(
        self,
        env: Any,
        max_states: int = 20,
        max_actions_per_state: int = 5,
    ):
        self.env = env
        self.max_states = max_states
        self.max_actions_per_state = max_actions_per_state

    async def crawl(self) -> CrawlGraph:
        """Crawl the application and build a state-machine graph."""
        graph = CrawlGraph()
        visited_states: set[str] = set()
        state_queue: list[str] = []

        # Capture initial state
        initial_state = await self._capture_state("initial")
        graph.states[initial_state.state_id] = initial_state
        state_queue.append(initial_state.state_id)

        while state_queue and len(graph.states) < self.max_states:
            current_id = state_queue.pop(0)
            if current_id in visited_states:
                continue
            visited_states.add(current_id)

            current_state = graph.states[current_id]
            logger.info(
                "Crawling state %s (%d elements)",
                current_id,
                len(current_state.interactive_elements),
            )

            # Try clicking each interactive element
            for i, element in enumerate(
                current_state.interactive_elements[: self.max_actions_per_state]
            ):
                xpath = element.get("xpath", "")
                if not xpath:
                    continue

                try:
                    # Save state for restoration
                    prev_url = await self.env.get_page_url()

                    # Execute action
                    await self.env.click(xpath)
                    await asyncio.sleep(0.5)

                    # Capture new state
                    new_url = await self.env.get_page_url()
                    new_state_id = f"state_{len(graph.states)}"
                    new_state = await self._capture_state(new_state_id)

                    # Check if this is a genuinely new state
                    is_new = new_state.dom_hash not in {
                        s.dom_hash for s in graph.states.values()
                    }

                    if is_new:
                        graph.states[new_state_id] = new_state
                        state_queue.append(new_state_id)
                        target_id = new_state_id
                    else:
                        # Find existing state with same hash
                        target_id = current_id
                        for sid, s in graph.states.items():
                            if s.dom_hash == new_state.dom_hash:
                                target_id = sid
                                break

                    graph.transitions.append(
                        CrawlTransition(
                            from_state=current_id,
                            to_state=target_id,
                            action="click",
                            target_xpath=xpath,
                            element_text=element.get("text", ""),
                        )
                    )

                    # Navigate back if URL changed
                    if new_url != prev_url:
                        await self.env.go_back()
                        await asyncio.sleep(0.3)

                except Exception as e:
                    logger.debug("Crawl action failed: %s", e)

        logger.info(
            "Crawling complete: %d states, %d transitions",
            graph.state_count,
            graph.transition_count,
        )
        return graph

    async def _capture_state(self, state_id: str) -> CrawlState:
        """Capture the current state of the application."""
        url = await self.env.get_page_url()

        # Get interactive elements
        elements = await self.env.evaluate_js("""() => {
            const interactives = document.querySelectorAll(
                'a, button, input, select, textarea, [role="button"], [onclick], [tabindex]'
            );
            return Array.from(interactives).slice(0, 30).map((el, i) => {
                function getXPath(element) {
                    if (element.id) return `//*[@id="${element.id}"]`;
                    const parent = element.parentElement;
                    if (!parent) return '/' + element.tagName.toLowerCase();
                    const siblings = Array.from(parent.children)
                        .filter(c => c.tagName === element.tagName);
                    const idx = siblings.indexOf(element) + 1;
                    const suffix = siblings.length > 1 ? `[${idx}]` : '';
                    return getXPath(parent) + '/' + element.tagName.toLowerCase() + suffix;
                }
                return {
                    xpath: getXPath(el),
                    tag: el.tagName.toLowerCase(),
                    text: (el.textContent || '').trim().slice(0, 100),
                    type: el.type || '',
                    visible: el.offsetParent !== null,
                };
            }).filter(e => e.visible);
        }""")

        # Create a simple hash from the DOM structure
        dom_text = await self.env.evaluate_js(
            "() => document.body.innerText.slice(0, 500)"
        )
        dom_hash = str(hash(f"{url}:{dom_text[:200]}"))

        return CrawlState(
            state_id=state_id,
            url=url,
            dom_hash=dom_hash,
            interactive_elements=elements or [],
        )
