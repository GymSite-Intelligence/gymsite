from tools.osm_isocronas import parse_isochrone_geojson

_FC = {
    "type": "FeatureCollection",
    "features": [
        {
            "type": "Feature",
            "properties": {"contour": 5},
            "geometry": {
                "type": "Polygon",
                "coordinates": [[
                    [-38.49, -3.74], [-38.48, -3.74], [-38.48, -3.75],
                    [-38.49, -3.75], [-38.49, -3.74],
                ]],
            },
        },
        {
            "type": "Feature",
            "properties": {"value": 600},
            "geometry": {
                "type": "Polygon",
                "coordinates": [[
                    [-38.50, -3.73], [-38.47, -3.73], [-38.47, -3.76],
                    [-38.50, -3.76], [-38.50, -3.73],
                ]],
            },
        },
        {
            "type": "Feature",
            "properties": {"contour": 15},
            "geometry": {
                "type": "Polygon",
                "coordinates": [[
                    [-38.51, -3.72], [-38.46, -3.72], [-38.46, -3.77],
                    [-38.51, -3.77], [-38.51, -3.72],
                ]],
            },
        },
    ],
}


def test_parse_valhalla_e_ors_minutos():
    out = parse_isochrone_geojson(_FC)
    assert set(out) == {"m5", "m10", "m15"}
    assert out["m5"][0] == [-3.74, -38.49]
    assert out["m10"][0] == [-3.73, -38.50]
    assert len(out["m15"]) >= 4


def test_parse_multipolygon_pega_anel_maior():
    fc = {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "properties": {"contour": 5},
                "geometry": {
                    "type": "MultiPolygon",
                    "coordinates": [
                        [[
                            [-38.49, -3.74], [-38.489, -3.74],
                            [-38.489, -3.741], [-38.49, -3.741],
                            [-38.49, -3.74],
                        ]],
                        [[
                            [-38.50, -3.73], [-38.485, -3.73], [-38.47, -3.73],
                            [-38.47, -3.745], [-38.47, -3.76],
                            [-38.485, -3.76], [-38.50, -3.76],
                            [-38.50, -3.745], [-38.50, -3.73],
                        ]],
                    ],
                },
            },
        ],
    }
    out = parse_isochrone_geojson(fc)
    assert out["m5"][0] == [-3.73, -38.50]
