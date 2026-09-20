from sizzle.targets import PRESETS, REFERENCE, check_duration, resolve


def test_presets_resolve_by_name_aspect_and_size():
    assert resolve("reels").height == 1920
    assert resolve("16:9").width == 1920
    assert resolve("800x600").height == 600


def test_fps_override_is_applied():
    assert resolve("tiktok", 60).fps == 60


def test_short_form_reserves_room_for_platform_furniture():
    for name in ("reels", "tiktok", "shorts"):
        target = PRESETS[name]
        assert target.caption_y < 1 - target.safe.bottom
        assert target.content_bottom < target.caption_y
        assert target.content_top > target.bar_y


def test_landscape_keeps_the_full_width():
    assert PRESETS["youtube"].content_width > 0.9


def test_reference_frame_maps_to_itself():
    assert abs(REFERENCE.remap_y(0.453) - 0.453) < 1e-9


def test_other_targets_stay_inside_their_band():
    for target in PRESETS.values():
        for y in (0.3, 0.453, 0.6):
            mapped = target.remap_y(y)
            assert target.content_top - 0.08 <= mapped <= target.content_bottom + 0.08


def test_duration_limit_warns_only_when_exceeded():
    assert check_duration(PRESETS["shorts"], 45) is None
    assert "exceeds" in check_duration(PRESETS["shorts"], 75)
    assert check_duration(PRESETS["youtube"], 3600) is None
