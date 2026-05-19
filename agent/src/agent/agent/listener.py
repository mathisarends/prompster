# TODO: diese grundgerüst hier als hauptinterface für ui updates nutzen:

# from __future__ import annotations
# import logging
# from collections.abc import Sequence

# from typing import TYPE_CHECKING

# from vizron.agent.views import ActivitySegment
# from vizron.events import EventBus
# from vizron.events.views import (
#     ActivitySegmentView,
#     ActivitySegmentsReadyEvent,
#     AgentActionExecutedEvent,
#     AgentDoneEvent,
#     AgentStepDecidedEvent,
#     HistoryCompactedEvent,
#     HistoryCompactionStartedEvent,
#     NavigationMetric,
#     NavigationTimingDetectedEvent,
#     PageLoadedAfterNavigationEvent,
#     ScreencastStartEvent,
#     VideoCuttingFinishedEvent,
#     VideoCuttingStartedEvent,
#     VideoRecordingStoppedEvent,
#     VideoRecordingFinishedEvent,
# )

# if TYPE_CHECKING:
#     from vizron.tools.views import Action, ActionResult

# logger = logging.getLogger(__name__)


# class AgentListener:
#     async def on_navigate(self, new_url: str) -> None:
#         pass

#     async def on_screencast_started(self) -> None:
#         pass

#     async def on_video_recording_stopped(self) -> None:
#         """Recording halted, postprocessing begins."""

#     async def on_video_cutting_started(self) -> None:
#         pass

#     async def on_video_cutting_finished(self) -> None:
#         pass

#     async def on_video_recording_finished(self, video_path: str) -> None:
#         """Fully encoded, cut, and written to disk."""

#     async def on_step_decided(
#         self,
#         think_aloud: str | None,
#         actions: list[Action],
#         screenshot: bytes | None = None,
#         current_url: str | None = None,
#     ) -> None:
#         pass

#     async def on_action_executed(self, actions: list[Action]) -> None:
#         pass

#     async def on_done(self, action_history: list[list[ActionResult]]) -> None:
#         pass

#     async def on_history_compaction_started(
#         self,
#         step_number: int,
#     ) -> None:
#         pass

#     async def on_history_compacted(
#         self,
#         step_number: int,
#     ) -> None:
#         pass

#     async def on_navigation_timing_detected(
#         self,
#         metric: NavigationMetric,
#         duration_ms: int,
#         url: str,
#     ) -> None:
#         pass

#     async def on_activity_segments_ready(
#         self,
#         segments: list[ActivitySegment],
#     ) -> None:
#         """Called after video recording stopped with a gapless timeline.

#         Segments cover the full observed timeline from 0.0 up to the last
#         known segment end. Inserted gaps are marked with ``is_active=False``.
#         """
#         pass


# class AgentListenerBridge:
#     def __init__(
#         self,
#         event_bus: EventBus,
#         listener: AgentListener,
#         recording_output_path: str | None = None,
#     ) -> None:
#         self._event_bus = event_bus
#         self._listener = listener
#         self._register(recording_output_path)

#     def _register(self, recording_output_path: str | None) -> None:
#         self._event_bus.subscribe(
#             PageLoadedAfterNavigationEvent,
#             lambda e: self._listener.on_navigate(e.result.final_url),
#         )
#         self._event_bus.subscribe(
#             ScreencastStartEvent,
#             lambda _: self._listener.on_screencast_started(),
#         )
#         self._event_bus.subscribe(
#             VideoRecordingStoppedEvent,
#             lambda _: self._listener.on_video_recording_stopped(),
#         )
#         self._event_bus.subscribe(
#             ActivitySegmentsReadyEvent,
#             lambda e: self._listener.on_activity_segments_ready(
#                 segments=self._build_gapless_activity_timeline(e.segments)
#             ),
#         )
#         self._event_bus.subscribe(
#             VideoRecordingFinishedEvent,
#             lambda e: self._listener.on_video_recording_finished(
#                 video_path=e.recorded_video_path
#             ),
#         )
#         self._event_bus.subscribe(
#             VideoCuttingStartedEvent,
#             lambda _: self._listener.on_video_cutting_started(),
#         )
#         self._event_bus.subscribe(
#             VideoCuttingFinishedEvent,
#             lambda _: self._listener.on_video_cutting_finished(),
#         )
#         self._event_bus.subscribe(
#             AgentStepDecidedEvent,
#             lambda e: self._listener.on_step_decided(
#                 think_aloud=e.think_aloud,
#                 actions=e.actions,
#                 screenshot=e.screenshot,
#                 current_url=e.current_url,
#             ),
#         )
#         self._event_bus.subscribe(
#             AgentActionExecutedEvent,
#             lambda e: self._listener.on_action_executed(actions=e.actions),
#         )
#         self._event_bus.subscribe(
#             AgentDoneEvent,
#             lambda e: self._listener.on_done(action_history=e.action_history),
#         )
#         self._event_bus.subscribe(
#             HistoryCompactionStartedEvent,
#             lambda e: self._listener.on_history_compaction_started(
#                 step_number=e.step_number,
#             ),
#         )
#         self._event_bus.subscribe(
#             NavigationTimingDetectedEvent,
#             lambda e: self._listener.on_navigation_timing_detected(
#                 metric=e.metric,
#                 duration_ms=e.duration_ms,
#                 url=e.url,
#             ),
#         )
#         self._event_bus.subscribe(
#             HistoryCompactedEvent,
#             lambda e: self._listener.on_history_compacted(
#                 step_number=e.step_number,
#             ),
#         )

#         if recording_output_path is None and self._has_video_callback_overrides():
#             logger.warning(
#                 "Video lifecycle listener is subscribed, but "
#                 "recording_output_path is not configured."
#             )

#     def _has_video_callback_overrides(self) -> bool:
#         callbacks = [
#             (
#                 self._listener.on_video_recording_stopped,
#                 AgentListener.on_video_recording_stopped,
#             ),
#             (
#                 self._listener.on_video_recording_finished,
#                 AgentListener.on_video_recording_finished,
#             ),
#             (
#                 self._listener.on_activity_segments_ready,
#                 AgentListener.on_activity_segments_ready,
#             ),
#             (
#                 self._listener.on_video_cutting_started,
#                 AgentListener.on_video_cutting_started,
#             ),
#             (
#                 self._listener.on_video_cutting_finished,
#                 AgentListener.on_video_cutting_finished,
#             ),
#         ]

#         return any(
#             getattr(callback, "__func__", callback) is not base_callback
#             for callback, base_callback in callbacks
#         )

#     def _build_gapless_activity_timeline(
#         self,
#         active_segments: Sequence[ActivitySegmentView],
#     ) -> list[ActivitySegment]:
#         normalized: list[ActivitySegmentView] = []
#         for segment in active_segments:
#             start_seconds = max(0.0, segment.start_seconds)
#             end_seconds = max(start_seconds, segment.end_seconds)
#             duration_seconds = end_seconds - start_seconds
#             if duration_seconds <= 0:
#                 continue

#             normalized.append(
#                 ActivitySegmentView(
#                     start_seconds=start_seconds,
#                     end_seconds=end_seconds,
#                     duration_seconds=duration_seconds,
#                 )
#             )

#         normalized.sort(key=lambda segment: segment.start_seconds)

#         timeline: list[ActivitySegment] = []
#         cursor = 0.0

#         for segment in normalized:
#             if segment.start_seconds > cursor:
#                 timeline.append(
#                     ActivitySegment(
#                         start_seconds=round(cursor, 3),
#                         end_seconds=round(segment.start_seconds, 3),
#                         duration_seconds=round(segment.start_seconds - cursor, 3),
#                         is_active=False,
#                     )
#                 )

#             active_start = max(cursor, segment.start_seconds)
#             if segment.end_seconds > active_start:
#                 timeline.append(
#                     ActivitySegment(
#                         start_seconds=round(active_start, 3),
#                         end_seconds=round(segment.end_seconds, 3),
#                         duration_seconds=round(segment.end_seconds - active_start, 3),
#                         is_active=True,
#                     )
#                 )

#             cursor = max(cursor, segment.end_seconds)

#         return timeline
