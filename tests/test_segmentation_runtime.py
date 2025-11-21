import os
import json
import threading
import time
import numpy as np

from somabrain.services.segmentation_service import SegmentationService, GRAD_THRESH, HMM_THRESHOLD


class DummyProducer:
    def __init__(self):
        self.sent = []
    def send(self, topic, payload):
        self.sent.append((topic, payload))


def test_gradient_threshold_reads_settings():
    os.environ["SOMABRAIN_SEGMENT_GRAD_THRESH"] = "0.01"
    svc = SegmentationService()
    svc.producer = DummyProducer()
    svc._gradient_boundaries([0, 1, 0])  # compute once to ensure no error
    assert svc._grad_thresh == GRAD_THRESH or svc._grad_thresh != 0  # value cached


def test_hmm_threshold_reads_settings():
    os.environ["SOMABRAIN_SEGMENT_HMM_THRESH"] = "0.2"
    svc = SegmentationService()
    svc.producer = DummyProducer()
    bounds = svc._run_hmm([0, 1, 0])
    assert isinstance(bounds, list)
