import sys
import types

import pytest

from app.retrieval.models import BGEM3Embedder, BGEReranker


class _RecordingModel:
    """Stands in for BGEM3FlagModel / FlagReranker: just remembers its kwargs."""

    def __init__(self, model_name, **kwargs):
        self.model_name = model_name
        self.kwargs = kwargs


@pytest.fixture
def fake_flag_embedding(monkeypatch):
    module = types.ModuleType("FlagEmbedding")
    module.BGEM3FlagModel = _RecordingModel
    module.FlagReranker = _RecordingModel
    monkeypatch.setitem(sys.modules, "FlagEmbedding", module)
    return module


def test_bgem3_embedder_cpu_device_forces_fp32(fake_flag_embedding):
    embedder = BGEM3Embedder(device="cpu")
    assert embedder._model.kwargs == {"use_fp16": False, "devices": "cpu"}


def test_bgereranker_cpu_device_forces_fp32(fake_flag_embedding):
    reranker = BGEReranker(device="cpu")
    assert reranker._model.kwargs == {"use_fp16": False, "devices": "cpu"}


def test_bgem3_embedder_default_device_is_cpu_and_forces_fp32(fake_flag_embedding):
    # DEFAULT_DEVICE (app.config) is "cpu" unless IFLA_DEVICE overrides it: a plain
    # construction must not accidentally run on GPU and cook this laptop.
    embedder = BGEM3Embedder(use_fp16=True)
    assert embedder._model.kwargs == {"use_fp16": False, "devices": "cpu"}


def test_bgereranker_default_device_is_cpu_and_forces_fp32(fake_flag_embedding):
    reranker = BGEReranker(use_fp16=True)
    assert reranker._model.kwargs == {"use_fp16": False, "devices": "cpu"}


def test_bgem3_embedder_explicit_cuda_still_works(fake_flag_embedding):
    embedder = BGEM3Embedder(device="cuda")
    assert embedder._model.kwargs == {"use_fp16": True, "devices": "cuda"}


def test_bgereranker_explicit_cuda_still_works(fake_flag_embedding):
    reranker = BGEReranker(device="cuda")
    assert reranker._model.kwargs == {"use_fp16": True, "devices": "cuda"}
