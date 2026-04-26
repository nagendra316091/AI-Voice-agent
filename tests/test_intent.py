"""Unit tests for the intent recogniser."""
from __future__ import annotations

import pytest

from modules.nlp.intent_recognizer import IntentRecognizer


@pytest.fixture()
def nlp() -> IntentRecognizer:
    return IntentRecognizer()


# ---- Math ----------------------------------------------------------------

def test_multiply_with_digits(nlp: IntentRecognizer) -> None:
    i = nlp.recognize("multiply 72000 and 32")
    assert i.name == "math"
    assert i.entities == {"op": "multiply", "a": 72000.0, "b": 32.0}


def test_multiply_with_words(nlp: IntentRecognizer) -> None:
    i = nlp.recognize("multiply seventy two thousand by thirty two")
    assert i.name == "math"
    assert i.entities == {"op": "multiply", "a": 72000.0, "b": 32.0}


def test_add(nlp: IntentRecognizer) -> None:
    assert nlp.recognize("add 5 and 7").entities == {"op": "add", "a": 5.0, "b": 7.0}


# ---- Open ----------------------------------------------------------------

@pytest.mark.parametrize("utter,target", [
    ("open calculator", "calculator"),
    ("open chrome", "chrome"),
    ("launch notepad", "notepad"),
    ("open youtube", "youtube"),
    ("open documents folder", "documents"),
    ("go to github", "github"),
])
def test_open(nlp: IntentRecognizer, utter: str, target: str) -> None:
    i = nlp.recognize(utter)
    assert i.name == "open"
    assert i.entities["target"] == target


# ---- Search --------------------------------------------------------------

def test_search_google(nlp: IntentRecognizer) -> None:
    i = nlp.recognize("search for python tutorials")
    assert i.name == "search_web"
    assert i.entities["query"] == "python tutorials"


def test_search_youtube(nlp: IntentRecognizer) -> None:
    i = nlp.recognize("play on youtube lofi beats")
    assert i.name == "search_youtube"
    assert i.entities["query"] == "lofi beats"


# ---- System --------------------------------------------------------------

@pytest.mark.parametrize("utter,name", [
    ("what time is it", "time"),
    ("what's the date", "date"),
    ("take a screenshot", "screenshot"),
    ("lock my computer", "lock"),
    ("shut down my pc", "shutdown"),
    ("restart my laptop", "restart"),
    ("volume up", "volume_up"),
    ("volume down", "volume_down"),
    ("mute", "mute_volume"),
    ("minimize all windows", "minimize_all"),
    ("close window", "close_window"),
    ("switch window", "switch_window"),
    ("next track", "media_next"),
    ("previous song", "media_prev"),
    ("pause music", "media_play_pause"),
    ("goodbye", "exit"),
    ("help", "help"),
])
def test_simple_intents(nlp: IntentRecognizer, utter: str, name: str) -> None:
    assert nlp.recognize(utter).name == name


def test_volume_set(nlp: IntentRecognizer) -> None:
    i = nlp.recognize("set volume to 50")
    assert i.name == "volume_set"
    assert i.entities == {"level": 50}


def test_type_text(nlp: IntentRecognizer) -> None:
    i = nlp.recognize("type hello world")
    assert i.name == "type_text"
    assert i.entities == {"text": "hello world"}


def test_say(nlp: IntentRecognizer) -> None:
    i = nlp.recognize("say good morning")
    assert i.name == "say"
    assert i.entities == {"text": "good morning"}


def test_unknown(nlp: IntentRecognizer) -> None:
    assert nlp.recognize("the quick brown fox").name == "unknown"
