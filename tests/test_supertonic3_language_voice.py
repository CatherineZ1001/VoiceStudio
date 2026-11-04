"""Supertonic-3 language names and preset voices (#2938).

Two bugs, one root: Supertonic-3 bypassed the shared language and request
plumbing every other engine uses.

* The UI sends picker names ("Portuguese"), and the sidecar kept their first
  two letters: 14 languages became invalid codes ("po") and two silently
  became a different language ("Estonian" -> "es" Spanish, "Slovak" -> "sl"
  Slovenian).
* ``/generate`` had no ``voice`` field, so every take used the default M1.

None of these tests start the sidecar or touch the network.
"""
from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest
from fastapi import HTTPException

from engines.supertonic3 import constants
from engines.supertonic3.backend import Supertonic3Backend
from services.subprocess_backend import SubprocessBackend


def _picker_name(code: str) -> str:
    """The language picker's label for an ISO code, as the UI sends it."""
    from omnivoice.utils.lang_map import LANG_NAME_TO_ID

    if code == "ar":  # the picker's label; the map files it under ISO 639-3 "arb"
        return "Standard Arabic"
    names = [name for name, iso in LANG_NAME_TO_ID.items() if iso == code]
    assert names, f"no picker name maps to {code!r}"
    return names[0].title()


@pytest.fixture
def forwarded(monkeypatch):
    """Capture what Supertonic3Backend.generate sends to the sidecar."""
    seen: dict = {}

    def fake_generate(self, text, **kw):
        seen.clear()
        seen.update(kw)
        return None

    monkeypatch.setattr(SubprocessBackend, "generate", fake_generate)
    return seen


@pytest.fixture
def sidecar():
    """Load sidecar.py as a module, the way its own venv runs it."""
    path = Path(constants.__file__).with_name("sidecar.py")
    spec = importlib.util.spec_from_file_location("_st3_sidecar_2938", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


# ── Bug 1: language names ─────────────────────────────────────────────────


def test_declares_the_sdks_language_set():
    assert Supertonic3Backend().supported_languages == constants.SUPPORTED_LANGUAGES
    assert len(constants.SUPPORTED_LANGUAGES) == 31


@pytest.mark.parametrize("code", constants.SUPPORTED_LANGUAGES)
def test_every_picker_name_reaches_the_sdk_as_its_own_code(forwarded, code):
    Supertonic3Backend().generate("hi", language=_picker_name(code))
    assert forwarded["lang"] == code


@pytest.mark.parametrize(
    ("picked", "expected"),
    [
        ("Portuguese", "pt"),  # was "po": invalid
        ("German", "de"),      # was "ge": invalid
        ("Estonian", "et"),    # was "es": spoke Spanish
        ("Slovak", "sk"),      # was "sl": spoke Slovenian
        ("Arabic", "ar"),      # the short name API clients send
        ("pt", "pt"),          # ISO codes from API clients still work
        ("pt-BR", "pt"),       # region tags resolve to their base language
    ],
)
def test_reported_languages(forwarded, picked, expected):
    Supertonic3Backend().generate("hi", language=picked)
    assert forwarded["lang"] == expected


@pytest.mark.parametrize("auto", [None, "", "Auto", "auto"])
def test_auto_leaves_the_language_to_the_sdk(forwarded, sidecar, auto):
    Supertonic3Backend().generate("hi", language=auto)
    assert forwarded["lang"] is None
    assert sidecar._normalize_lang(forwarded["lang"]) == "na"


def test_unsupported_language_is_refused_by_name(forwarded):
    with pytest.raises(ValueError, match="doesn't support language='Chinese'"):
        Supertonic3Backend().generate("hi", language="Chinese")
    assert forwarded == {}


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("pt", "pt"),
        ("PT_br", "pt"),
        ("Portuguese", "portuguese"),  # never truncated into another code
        ("Estonian", "estonian"),
        ("auto", "na"),
        (None, "na"),
    ],
)
def test_sidecar_never_guesses_a_code(sidecar, raw, expected):
    assert sidecar._normalize_lang(raw) == expected


def test_language_picker_offers_only_supertonic_languages():
    from services.tts_backend import language_options

    names = language_options("supertonic3")
    assert names is not None
    assert {"portuguese", "estonian", "slovak", "standard arabic"} <= set(names)
    assert "chinese" not in names


# ── Bug 2: preset voices ──────────────────────────────────────────────────


def test_advertises_its_presets():
    from services.tts_backend import list_backends

    entry = next(e for e in list_backends() if e["id"] == "supertonic3")
    assert entry["voice_presets"] == constants.VOICE_PRESETS


@pytest.mark.parametrize("voice", constants.VOICE_PRESETS)
def test_chosen_voice_reaches_the_sidecar(forwarded, voice):
    Supertonic3Backend().generate("hi", voice=voice)
    assert forwarded["voice"] == voice


def test_generate_route_accepts_a_preset_and_refuses_an_unknown_one():
    from api.routers.generation import _resolve_preset_voice

    assert _resolve_preset_voice(Supertonic3Backend, "F3") == "F3"
    assert _resolve_preset_voice(Supertonic3Backend, None) is None
    assert _resolve_preset_voice(Supertonic3Backend, " ") is None
    with pytest.raises(HTTPException) as refused:
        _resolve_preset_voice(Supertonic3Backend, "Z9")
    assert refused.value.status_code == 400
    assert "M1" in refused.value.detail


def test_voice_is_only_forwarded_to_engines_with_presets():
    from api.routers.generation import _preset_voice_kwargs, _resolve_preset_voice
    from services.tts_backend import get_backend_class

    omnivoice = get_backend_class("omnivoice")
    # An engine without presets ignores the field rather than failing.
    assert _resolve_preset_voice(omnivoice, "F3") is None
    assert _preset_voice_kwargs(omnivoice, "F3") == {}
    assert _preset_voice_kwargs(Supertonic3Backend, "F3") == {"voice": "F3"}
    assert _preset_voice_kwargs(Supertonic3Backend, None) == {}
