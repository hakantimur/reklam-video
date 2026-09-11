"""Mock-only tests: fakes the video/speech provider adapters and
`technical_qc.run_technical_qc` entirely, to prove the generation service's
own logic (prompt caching on Shot, submit/poll/download sequencing, budget
timeout, Asset/Take persistence) independent of any real provider call."""

from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from app.media import technical_qc
from app.models.creative import Revision, Shot, Take
from app.providers.base import VideoPollResult, VideoValidationResult
from app.services import generation as generation_service
from app.services import projects as projects_service
from app.services.errors import BlockedError, ValidationAppError


def _setup_shot(session, *, source_type="ai_generated", voice_text=None) -> tuple[str, str]:
    project = projects_service.create_project(session, name="Uretim Testi")
    projects_service.put_brief(
        session, project.id, audience="t", single_message="t", objective="install",
        style_id="s", language="tr", target_frames=600, fps_num=30, fps_den=1,
        placement_id="p", budget_microusd=1, product_name="Synova", description="Hafiza oyunu", cta="c",
    )
    brief = projects_service.get_latest_brief(session, project.id)
    revision = Revision(
        project_id=project.id, brief_id=brief.id, sequence_no=1, status="draft",
        timeline_json={}, content_hash="x", created_at=datetime.now(timezone.utc),
    )
    session.add(revision)
    session.flush()
    shot = Shot(
        revision_id=revision.id, order_index=0, source_type=source_type, purpose="Hook et",
        target_frames=90, voice_text=voice_text,
    )
    session.add(shot)
    session.commit()
    return project.id, shot.id


class _FakeVideoProvider:
    def __init__(self, tmp_path: Path, *, states=("completed",), models=None):
        self.tmp_path = tmp_path
        self._states = list(states)
        self._models = models or []
        self.submit_calls: list = []

    def list_models(self):
        return self._models

    def validate_request(self, request):
        return VideoValidationResult(ok=True, resolved_duration_s=request.duration_s)

    def submit(self, request, *, idempotency_key):
        self.submit_calls.append((request, idempotency_key))
        return "remote-job-1"

    def poll(self, remote_id):
        state = self._states.pop(0) if len(self._states) > 1 else self._states[0]
        if state == "completed":
            return VideoPollResult(remote_id=remote_id, state="completed", download_url="http://example/x.mp4")
        if state == "failed":
            return VideoPollResult(remote_id=remote_id, state="failed", error="model_error")
        return VideoPollResult(remote_id=remote_id, state=state)

    def download(self, remote_id, destination):
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(b"fake-generated-mp4")
        return destination


@pytest.fixture(autouse=True)
def _fake_technical_qc(monkeypatch):
    report = technical_qc.TechnicalQCReport(
        probe=technical_qc.MediaProbe(
            duration_s=3.0, width=1080, height=1920, has_video=True, has_audio=False,
            video_codec="h264", audio_codec=None,
        ),
        decodes_cleanly=True,
        checks={"probe": "pass", "decode": "pass", "scene_detect": "pass", "blank_or_frozen": "pass"},
    )
    monkeypatch.setattr(generation_service.technical_qc, "run_technical_qc", lambda path: report)
    return report


def _fake_text_provider(prompt="A colorful phone showing a memory game"):
    provider = MagicMock()
    provider.generate_structured.return_value = {"video_prompt": prompt}
    return provider


def test_generate_ai_scene_take_persists_asset_and_prompt(db_session, tmp_path):
    project_id, shot_id = _setup_shot(db_session)
    video_provider = _FakeVideoProvider(tmp_path)

    take = generation_service.generate_ai_scene_take(
        db_session, project_id, shot_id,
        text_provider=_fake_text_provider(), text_model="test/model",
        video_provider=video_provider, video_model="test/video-model",
        poll_interval_s=0.01, max_wait_s=1.0,
    )

    assert take.status == "pending"
    assert take.attempt == 1
    shot = db_session.get(Shot, shot_id)
    assert shot.generation_prompt == "A colorful phone showing a memory game"
    assert len(video_provider.submit_calls) == 1


def test_generate_ai_scene_take_requests_the_nearest_supported_duration(db_session, tmp_path):
    """Spec §9.3: when the shot's exact duration (here 3.0s from the
    default 90-frame target) isn't one of the model's own supported
    durations, request the nearest one that is >= the target — never a
    shorter one — and let the timeline's own `Sequence durationInFrames`
    (unrelated to this service) trim it down at render time."""

    from app.schemas.provider import ProviderModel

    project_id, shot_id = _setup_shot(db_session)
    model = ProviderModel(id="test/video-model", supported_durations_s=[4.0, 6.0, 8.0])
    video_provider = _FakeVideoProvider(tmp_path, models=[model])

    generation_service.generate_ai_scene_take(
        db_session, project_id, shot_id,
        text_provider=_fake_text_provider(), text_model="test/model",
        video_provider=video_provider, video_model="test/video-model",
        poll_interval_s=0.01, max_wait_s=1.0,
    )

    request, _ = video_provider.submit_calls[0]
    assert request.duration_s == 4.0  # nearest supported duration >= 3.0s, not 3.0s itself


def test_generate_ai_scene_take_uses_the_exact_duration_when_it_is_already_supported(db_session, tmp_path):
    from app.schemas.provider import ProviderModel

    project_id, shot_id = _setup_shot(db_session)  # target_frames=90 -> 3.0s
    model = ProviderModel(id="test/video-model", supported_durations_s=[3.0, 6.0])
    video_provider = _FakeVideoProvider(tmp_path, models=[model])

    generation_service.generate_ai_scene_take(
        db_session, project_id, shot_id,
        text_provider=_fake_text_provider(), text_model="test/model",
        video_provider=video_provider, video_model="test/video-model",
        poll_interval_s=0.01, max_wait_s=1.0,
    )

    request, _ = video_provider.submit_calls[0]
    assert request.duration_s == 3.0


def test_generate_ai_scene_take_falls_back_to_target_when_catalog_lookup_fails(db_session, tmp_path):
    """A broken/unavailable model catalog must not block generation —
    fall back to requesting the shot's own exact duration, same as
    before this behavior existed."""

    project_id, shot_id = _setup_shot(db_session)
    video_provider = _FakeVideoProvider(tmp_path)  # list_models() returns [] -> no matching model

    generation_service.generate_ai_scene_take(
        db_session, project_id, shot_id,
        text_provider=_fake_text_provider(), text_model="test/model",
        video_provider=video_provider, video_model="test/video-model",
        poll_interval_s=0.01, max_wait_s=1.0,
    )

    request, _ = video_provider.submit_calls[0]
    assert request.duration_s == 3.0


def test_generate_ai_scene_take_reuses_existing_prompt(db_session, tmp_path):
    project_id, shot_id = _setup_shot(db_session)
    shot = db_session.get(Shot, shot_id)
    shot.generation_prompt = "Already decided prompt"
    db_session.commit()

    text_provider = _fake_text_provider()
    generation_service.generate_ai_scene_take(
        db_session, project_id, shot_id,
        text_provider=text_provider, text_model="test/model",
        video_provider=_FakeVideoProvider(tmp_path), video_model="test/video-model",
        poll_interval_s=0.01, max_wait_s=1.0,
    )

    text_provider.generate_structured.assert_not_called()


def test_generate_ai_scene_take_raises_blocked_on_provider_failure(db_session, tmp_path):
    project_id, shot_id = _setup_shot(db_session)
    video_provider = _FakeVideoProvider(tmp_path, states=("failed",))

    with pytest.raises(BlockedError):
        generation_service.generate_ai_scene_take(
            db_session, project_id, shot_id,
            text_provider=_fake_text_provider(), text_model="m",
            video_provider=video_provider, video_model="m",
            poll_interval_s=0.01, max_wait_s=1.0,
        )


def test_generate_ai_scene_rejects_non_ai_generated_shot(db_session, tmp_path):
    project_id, shot_id = _setup_shot(db_session, source_type="gameplay")

    with pytest.raises(ValidationAppError):
        generation_service.generate_ai_scene_take(
            db_session, project_id, shot_id,
            text_provider=_fake_text_provider(), text_model="m",
            video_provider=_FakeVideoProvider(tmp_path), video_model="m",
        )


class _FakeSpeechProvider:
    def __init__(self, audio_bytes=b"fake-mp3-bytes"):
        self.audio_bytes = audio_bytes
        self.calls: list = []

    def list_voices(self):
        return []

    def synthesize(self, text, voice_id, language, style=None):
        self.calls.append((text, voice_id, language))
        return self.audio_bytes


def test_generate_voice_asset_persists_audio(monkeypatch, db_session):
    project_id, shot_id = _setup_shot(db_session, source_type="composed", voice_text="Şimdi indir!")
    provider = _FakeSpeechProvider()
    monkeypatch.setattr(
        generation_service.technical_qc,
        "probe_media",
        lambda path: technical_qc.MediaProbe(
            duration_s=4.46, width=None, height=None, has_video=False, has_audio=True,
            video_codec=None, audio_codec="mp3",
        ),
    )

    asset = generation_service.generate_voice_asset(
        db_session, project_id, shot_id, speech_provider=provider, voice_id="voice-1"
    )

    assert asset.type == "audio"
    assert asset.byte_size == len(provider.audio_bytes)
    assert asset.duration_us == 4_460_000
    assert asset.metadata_json["role"] == "voice_over"
    assert provider.calls == [("Şimdi indir!", "voice-1", "tr")]


def test_generate_voice_asset_duration_is_none_when_probe_fails(monkeypatch, db_session):
    project_id, shot_id = _setup_shot(db_session, source_type="composed", voice_text="Şimdi indir!")

    def fake_probe(path):
        raise technical_qc.ToolMissingError("ffprobe_failed: garbage input")

    monkeypatch.setattr(generation_service.technical_qc, "probe_media", fake_probe)

    asset = generation_service.generate_voice_asset(
        db_session, project_id, shot_id, speech_provider=_FakeSpeechProvider(), voice_id="voice-1"
    )

    assert asset.duration_us is None


def test_generate_voice_asset_requires_voice_text(db_session):
    project_id, shot_id = _setup_shot(db_session, source_type="composed", voice_text=None)

    with pytest.raises(ValidationAppError):
        generation_service.generate_voice_asset(
            db_session, project_id, shot_id, speech_provider=_FakeSpeechProvider(), voice_id="voice-1"
        )
