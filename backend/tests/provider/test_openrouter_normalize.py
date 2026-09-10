"""Unit tests for the catalog normalization functions (spec §9.1).

Fixtures below are trimmed copies of real payload shapes observed live from
`GET https://openrouter.ai/api/v1/models` and
`GET https://openrouter.ai/api/v1/videos/models` on 2026-09-11 (not
fabricated field names) -- but the normalization itself is exercised as a
pure-function unit test, not a live call.
"""

from app.providers.openrouter import normalize_text_model, normalize_video_model


def test_normalize_text_model_with_tools_gets_operator_role():
    raw = {
        "id": "anthropic/claude-fable-5.1",
        "architecture": {
            "input_modalities": ["text", "image", "file"],
            "output_modalities": ["text"],
        },
        "supported_parameters": ["tools", "response_format", "structured_outputs"],
        "pricing": {"prompt": "0.00001", "completion": "0.00005"},
    }
    model = normalize_text_model(raw)

    assert model.id == "anthropic/claude-fable-5.1"
    assert set(model.roles) == {"director", "reviewer", "operator"}
    assert model.input_modalities == ["text", "image", "file"]
    assert model.output_modalities == ["text"]
    assert model.supports_tools is True
    assert model.pricing == {"prompt": "0.00001", "completion": "0.00005"}
    assert model.capability_status == "unverified"


def test_normalize_text_model_without_tools_has_no_operator_role():
    raw = {
        "id": "inclusionai/ling-3.0-flash-vl:free",
        "architecture": {"input_modalities": ["text", "image"], "output_modalities": ["text"]},
        "supported_parameters": ["max_tokens", "temperature"],
        "pricing": {"prompt": "0", "completion": "0"},
    }
    model = normalize_text_model(raw)

    assert set(model.roles) == {"director", "reviewer"}
    assert model.supports_tools is False


def test_normalize_text_model_missing_supported_parameters_is_unknown_not_false():
    raw = {
        "id": "some/model",
        "architecture": {"input_modalities": ["text"], "output_modalities": ["text"]},
        "pricing": {},
    }
    model = normalize_text_model(raw)
    assert model.supports_tools is None, "unknown must stay None, never default to False"


def test_normalize_video_model_maps_real_field_names():
    raw = {
        "id": "black-forest-labs/flux-video-edit",
        "name": "Black Forest Labs: FLUX Video Edit",
        "supported_resolutions": None,
        "supported_aspect_ratios": None,
        "supported_sizes": None,
        "supported_durations": None,
        "supported_frame_images": None,
        "generate_audio": False,
        "pricing_skus": {"cents_per_second_output": "3"},
    }
    model = normalize_video_model(raw)

    assert model.id == "black-forest-labs/flux-video-edit"
    assert model.roles == ["video"]
    assert model.output_modalities == ["video"]
    assert model.supported_durations_s == []
    assert model.supported_ratios == []
    assert model.supported_resolutions == []
    assert model.supports_reference_images is None, "null in catalog must stay unknown"
    assert model.supports_native_audio is False, "catalog explicitly reported false"
    assert model.pricing == {"cents_per_second_output": "3"}
    assert model.capability_status == "unverified"


def test_normalize_video_model_with_known_durations_and_ratios():
    raw = {
        "id": "google/veo-3.1",
        "supported_durations": [4, 6, 8],
        "supported_aspect_ratios": ["16:9", "9:16", "1:1"],
        "supported_resolutions": ["720p", "1080p"],
        "supported_frame_images": [{"frame_type": "first_frame"}],
        "generate_audio": True,
        "pricing_skus": {"cents_per_second_output": "10"},
    }
    model = normalize_video_model(raw)

    assert model.supported_durations_s == [4.0, 6.0, 8.0]
    assert model.supported_ratios == ["16:9", "9:16", "1:1"]
    assert model.supported_resolutions == ["720p", "1080p"]
    assert model.supports_reference_images is True
    assert model.supports_native_audio is True
    assert model.capability_status == "unverified", "must never auto-verify from a rich catalog entry"
