from sizzle.config import load
from sizzle.timing import Timeline


def test_lines_are_placed_after_their_gaps(project):
    timeline = Timeline(load(project))
    assert timeline["hook"].vo == 0.5
    assert timeline["reveal"].vo == 0.5 + 1.5 + 0.25
    assert timeline.end > timeline["outro"].vo_end


def test_first_scene_starts_at_zero_and_scenes_are_contiguous(project):
    timeline = Timeline(load(project))
    assert timeline.order[0].start == 0.0
    for earlier, later in zip(timeline.order, timeline.order[1:]):
        assert earlier.end == later.start


def test_impact_is_the_marked_scene(project):
    timeline = Timeline(load(project))
    assert timeline.impact == timeline["reveal"].start


def test_word_times_run_in_order_inside_the_line(project):
    timeline = Timeline(load(project))
    times = [t for _word, t in timeline.words("hook")]
    assert times == sorted(times)
    assert timeline["hook"].vo <= times[0]
    assert times[-1] < timeline["hook"].vo_end


def test_cues_accept_words_indexes_seconds_and_offsets(project):
    timeline = Timeline(load(project))
    assert timeline.cue("hook", "two") == timeline.word("hook", 1)
    assert timeline.cue("hook", 1) == timeline.word("hook", 1)
    assert timeline.cue("hook", 0.4) == timeline["hook"].start + 0.4
    assert timeline.cue("hook", "end") == timeline["hook"].end
    assert abs(timeline.cue("hook", "two-0.1") - (timeline.word("hook", 1) - 0.1)) < 1e-9
