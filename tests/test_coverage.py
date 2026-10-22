from itertools import permutations

import pytest

from endstone_antiphantom.coverage import Chunk, PlayerCoverage, covers, decide

DIM = ("world", "Overworld")
CENTER = Chunk(DIM, 0, 0)
TOTALS = {4: 57, 5: 81, 6: 109, 7: 141, 8: 177, 9: 217, 10: 261, 11: 309, 12: 361}


@pytest.mark.parametrize("distance,total", TOTALS.items())
def test_complete_footprint_against_independent_row_fixture(distance, total):
    # Independent oracle: truncated diamond rows, with width 3 at top/bottom.
    # Half-widths from z=-D..D are 1,2,...,D,D,D,...,2,1.
    half_widths = list(range(1, distance)) + [distance] * 3 + list(range(distance - 1, 0, -1))
    expected = {
        (x, z)
        for z, half_width in zip(range(-distance, distance + 1), half_widths, strict=True)
        for x in range(-half_width, half_width + 1)
    }
    assert len(expected) == total
    actual = {
        (x, z)
        for x in range(-distance - 2, distance + 3)
        for z in range(-distance - 2, distance + 3)
        if covers(CENTER, Chunk(DIM, x, z), distance)
    }
    assert actual == expected


@pytest.mark.parametrize("distance", range(4, 13))
def test_signed_swapped_boundary_fixtures(distance):
    fixtures = [
        (distance, 0, True), (distance, 1, True), (distance - 1, 2, True),
        (distance + 1, 0, False), (distance, 2, False), (distance - 1, 3, False),
        (distance, distance, False),
    ]
    for x, z, expected in fixtures:
        for a, b in [(x, z), (z, x)]:
            for sx in [-1, 1]:
                for sz in [-1, 1]:
                    assert covers(CENTER, Chunk(DIM, sx * a, sz * b), distance) is expected


@pytest.mark.parametrize("coordinate,chunk", [
    (-32.00001, -3), (-32, -2), (-16.00001, -2), (-16, -1), (-0.00001, -1),
    (0, 0), (15.99999, 0), (16, 1), (31.99999, 1), (32, 2),
])
def test_floor_in_both_axes(coordinate, chunk):
    assert Chunk.at(DIM, coordinate, coordinate) == Chunk(DIM, chunk, chunk)


def test_translation_and_dimensions():
    assert covers(Chunk(DIM, -20, 8), Chunk(DIM, -24, 9), 4)
    assert not covers(Chunk(("world", "Nether"), 0, 0), CENTER, 4)
    assert not covers(Chunk(("other-world", "Overworld"), 0, 0), CENTER, 4)
    assert not covers(Chunk(("world", "custom-one"), 0, 0), Chunk(("world", "custom-two"), 0, 0), 4)


def test_overlap_and_iteration_order():
    players = [
        PlayerCoverage("关闭者", CENTER, False),
        PlayerCoverage("开启者", Chunk(DIM, 4, 1), True),
        PlayerCoverage("远处", Chunk(DIM, 4, 2), True),
        PlayerCoverage("异维度", Chunk(("world", "Nether"), 0, 0), True),
    ]
    for order in permutations(players):
        decision = decide(CENTER, iter(order), 4)
        assert not decision.blocked
        assert decision.covered_count == 2
        assert decision.enabled_names == ("开启者",)
    assert decide(CENTER, players[:1], 4).blocked
    assert not decide(CENTER, players[2:], 4).blocked
    assert not decide(CENTER, [], 4).blocked


def test_multiple_enabled_names_do_not_change_decision():
    players = [PlayerCoverage("A", CENTER, True), PlayerCoverage("B", CENTER, True)]
    for order in permutations(players):
        result = decide(CENTER, order, 4)
        assert set(result.enabled_names) == {"A", "B"}
        assert not result.blocked
