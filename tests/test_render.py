from sizzle.config import load
from sizzle.render import Reel


def test_every_target_renders_a_frame_of_the_right_size(project):
    config = load(project)
    for target in config.targets:
        reel = Reel(config.for_target(target))
        image = reel.frame(reel.timeline.end * 0.5)
        assert (image.width(), image.height()) == (target.width, target.height)


def test_frames_across_the_whole_video_are_not_blank(project):
    config = load(project)
    reel = Reel(config)
    for share in (0.05, 0.3, 0.6, 0.95):
        image = reel.frame(reel.timeline.end * share)
        colours = {image.pixel(x, y) for x in range(0, image.width(), 97)
                   for y in range(0, image.height(), 97)}
        assert len(colours) > 1


def test_a_scene_type_that_does_not_exist_is_reported(project):
    config = load(project)
    config.beats[0].type = "nonsense"
    try:
        Reel(config)
    except SystemExit as error:
        assert "nonsense" in str(error)
    else:
        raise AssertionError("expected an error naming the unknown scene type")
