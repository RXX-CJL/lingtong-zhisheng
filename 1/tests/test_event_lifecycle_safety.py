# -*- coding: utf-8 -*-
"""Non-destructive regression tests for event lifecycle safety contracts."""
import os
import sys
import time
import threading
import unittest

API_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'api'))
if API_DIR not in sys.path:
    sys.path.insert(0, API_DIR)

from traffic_event_engine import EventState, TrafficEvent, VALID_TRANSITIONS, wall_time_to_datetime
from realtime_detector import RealtimeViolationDetector


class TestEventLifecycleSafety(unittest.TestCase):
    def test_wall_time_is_serialized_separately_from_video_relative_time(self):
        event = TrafficEvent(
            event_id='evt_test_wall_clock',
            event_type='red_light',
            track_id=1,
            trigger_time=12.5,
            wall_time=1_700_000_000,
        )
        data = event.to_dict()
        self.assertEqual(data['trigger_time'], 12.5)
        self.assertEqual(data['wall_time'], 1_700_000_000)
        self.assertEqual(wall_time_to_datetime(data['wall_time']).timestamp(), 1_700_000_000)

    def test_missing_or_invalid_wall_time_is_not_converted(self):
        self.assertIsNone(wall_time_to_datetime(None))
        self.assertIsNone(wall_time_to_datetime(''))
        self.assertIsNone(wall_time_to_datetime('not-a-timestamp'))

    def test_stop_waits_for_pending_evidence_before_clearing_buffer(self):
        class DummyBuffer:
            def __init__(self):
                self.cleared = False

            def clear(self):
                self.cleared = True

        class DummyLoop:
            @staticmethod
            def is_running():
                return False

        detector = RealtimeViolationDetector.__new__(RealtimeViolationDetector)
        detector.lock = threading.RLock()
        detector.running = True
        detector._accept_new_events = True
        detector._event_engine_process_lock = threading.Lock()
        detector.cap = None
        detector.current_frame = None
        detector.last_detection_result = None
        detector.frame_cache = {}
        detector.active_events = {'evt_pending': object()}
        detector.frame_buffer = DummyBuffer()
        detector.event_loop = DummyLoop()
        detector._event_evidence_condition = threading.Condition()
        detector._pending_event_evidence = {'evt_pending'}

        def finish_evidence():
            time.sleep(0.05)
            detector._mark_event_evidence_complete('evt_pending')

        worker = threading.Thread(target=finish_evidence)
        worker.start()
        result = detector.stop()
        worker.join(timeout=2)

        self.assertTrue(result['success'])
        self.assertTrue(detector.frame_buffer.cleared)
        self.assertIn('evt_pending', detector.active_events)
        self.assertFalse(detector._pending_event_evidence)

    def test_cloud_review_failure_can_transition_to_manual_review(self):
        self.assertIn(EventState.MANUAL_REVIEW, VALID_TRANSITIONS[EventState.PENDING_AI])


if __name__ == '__main__':
    unittest.main()
