import polars as pl

from pressure_geometry.coordinates import add_normalized_pressure_geometry


def test_coordinate_normalization_aligns_downfield_pressure_across_play_directions() -> None:
    frames = pl.DataFrame(
        {
            "playDirection": ["right", "left"],
            "qb_x": [50.0, 50.0],
            "qb_y": [25.0, 25.0],
            "rusher_x": [55.0, 45.0],
            "rusher_y": [25.0, 25.0],
        }
    )

    result = add_normalized_pressure_geometry(frames)

    assert result["normalized_relative_x"].to_list() == [5.0, 5.0]
    assert result["pressure_angle"].to_list() == [0.0, 0.0]
