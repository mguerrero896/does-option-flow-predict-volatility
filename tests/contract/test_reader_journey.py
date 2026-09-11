"""Reader schematics retain reproducible bytes, readable labels and public routes."""

import xml.etree.ElementTree as ET

from docs.figures.public_refresh.render_reader_journey import (
    OUT,
    forecast_timeline,
    repository_route,
)


def test_reader_journey():
    for name, render in (
        ("forecast_timeline.svg", forecast_timeline),
        ("repository_route.svg", repository_route),
    ):
        data = render()
        assert (OUT / name).read_bytes() == data
        root = ET.fromstring(data)
        assert root.attrib["role"] == "img"
        assert root.find("{http://www.w3.org/2000/svg}desc").text
        labels = root.findall(".//{http://www.w3.org/2000/svg}text")
        assert labels and all(float(node.attrib["font-size"]) >= 20 for node in labels)
        assert b"marker-end" in data
        assert not any(suffix in data for suffix in (b".py", b".csv", b".md"))
