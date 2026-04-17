"""Interaction Recorder — passive CUA interaction monitor.

Records the sequence of observations, actions, and XPaths during
a CUA loop execution to produce interaction traces for the Model Generator.
"""

from __future__ import annotations

import logging
import os
import time
from pathlib import Path
from typing import TYPE_CHECKING, Any

from preact.config import RecorderConfig
from preact.schemas import ActionSpec, InteractionTrace, TraceStep

if TYPE_CHECKING:
    from preact.environment.base import ComputerEnvironment

logger = logging.getLogger(__name__)


class InteractionRecorder:
    """Records CUA interactions for later compilation into state machines.

    The recorder passively monitors interactions — it does not drive them.
    It is attached to the CUA Loop and records each step as it happens.
    """

    def __init__(
        self,
        env: ComputerEnvironment,
        config: RecorderConfig | None = None,
    ):
        self.env = env
        self.config = config or RecorderConfig()
        self._trace: InteractionTrace | None = None
        self._recording: bool = False
        self._screenshot_count: int = 0

    @property
    def is_recording(self) -> bool:
        return self._recording

    def start_recording(
        self,
        task_description: str,
        application_context: str = "",
    ) -> None:
        """Begin recording a new interaction trace."""
        self._trace = InteractionTrace(
            task_description=task_description,
            application_context=application_context,
            start_time=time.time(),
        )
        self._recording = True
        self._screenshot_count = 0
        logger.info("Recording started: %s", task_description)

    async def record_step(
        self,
        action: ActionSpec,
        llm_reasoning: str | None = None,
        target_xpath: str | None = None,
        element_info: dict[str, Any] | None = None,
        screenshot: bytes | None = None,
    ) -> None:
        """Record a single interaction step.

        Called by the CUA Loop after each action is executed.
        Uses pre-captured screenshot if provided, otherwise captures a new one.
        """
        if not self._recording or not self._trace:
            return

        screenshot_data = screenshot
        screenshot_path = None

        if self.config.save_screenshots:
            try:
                if screenshot_data is None:
                    screenshot_data = await self.env.screenshot()
                self._screenshot_count += 1
                screenshot_path = os.path.join(
                    self.config.screenshot_dir,
                    self._trace.trace_id,
                    f"step_{self._screenshot_count:04d}.png",
                )
                # Save screenshot to disk
                path = Path(screenshot_path)
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(screenshot_data)
            except Exception as e:
                logger.warning("Failed to capture screenshot: %s", e)

        page_url = None
        try:
            page_url = await self.env.get_page_url()
        except Exception:
            pass

        dom_snapshot = None
        if self.config.log_dom_snapshots:
            try:
                dom_snapshot = await self.env.get_dom_snapshot()
            except Exception:
                pass

        # Try to resolve XPath if not provided
        if not target_xpath and action.target:
            target_xpath = action.target

        step = TraceStep(
            action=action,
            target_xpath=target_xpath,
            element_info=element_info or {},
            llm_reasoning=llm_reasoning,
            page_url=page_url,
            screenshot_path=screenshot_path,
            screenshot_data=screenshot_data,
            dom_snapshot=dom_snapshot,
        )

        self._trace.steps.append(step)
        logger.debug(
            "Recorded step %d: %s",
            len(self._trace.steps),
            action.type.value,
        )

    def record_parameter(self, name: str, value: str) -> None:
        """Record a parameter used during the interaction."""
        if self._trace:
            self._trace.parameters_used[name] = value

    def stop_recording(self, success: bool = True) -> InteractionTrace:
        """Stop recording and return the completed trace.

        Args:
            success: Whether the task completed successfully.

        Returns:
            The completed InteractionTrace.
        """
        if not self._trace:
            raise RuntimeError("No recording in progress")

        self._trace.end_time = time.time()
        self._trace.success = success
        self._recording = False

        trace = self._trace
        self._trace = None

        logger.info(
            "Recording stopped: %d steps, success=%s",
            len(trace.steps),
            success,
        )
        return trace

    def discard_recording(self) -> None:
        """Discard the current recording without producing a trace."""
        self._recording = False
        self._trace = None
        logger.info("Recording discarded")
