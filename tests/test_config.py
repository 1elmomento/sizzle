import pytest

from sizzle.config import load


def test_targets_and_beats_are_read(project):
    config = load(project)
    assert [t.name for t in config.targets] == ["reels", "x"]
    assert config.active.name == "reels"
    assert [b.key for b in config.beats] == ["hook", "reveal", "outro"]


def test_scene_specific_keys_land_in_data(project):
    config = load(project)
    assert config.beats[0].data["line"][0]["text"] == "Hello"


def test_for_target_switches_the_frame_without_touching_the_rest(project):
    config = load(project)
    landscape = config.for_target(config.targets[1])
    assert (landscape.width, landscape.height) == (1920, 1080)
    assert landscape.beats is config.beats


def test_a_missing_config_is_reported(tmp_path):
    with pytest.raises(SystemExit):
        load(tmp_path)
