"""Geometry transformations for a reviewed conceptual single-floor domain."""
from shapely.geometry import Polygon, GeometryCollection
from shapely.ops import unary_union


def polygons(geom):
    if geom.geom_type == 'Polygon':
        return [geom]
    return [p for g in getattr(geom, 'geoms', []) for p in polygons(g)]


def envelope(parts, exclusions=None, radius=0):
    union = unary_union(parts)
    if radius:
        union = union.buffer(radius, join_style=2).buffer(-radius, join_style=2).union(union)
    # Only reviewed exclusions retain holes; internal partition slits are removed.
    filled = unary_union([Polygon(p.exterior) for p in polygons(union)])
    if exclusions is not None and not exclusions.is_empty:
        filled = filled.difference(exclusions)
    if filled.is_empty or not filled.is_valid:
        raise ValueError('Boundary domain is empty or invalid')
    return filled


def make_frame(domain):
    xmin, ymin, xmax, ymax = domain.bounds
    length = max(xmax - xmin, ymax - ymin)
    if length <= 0:
        raise ValueError('Degenerate coordinate frame')
    return {'origin_px': [xmin, ymax], 'long_side_px': length,
            'extent_normalized': [(xmax-xmin)/length, (ymax-ymin)/length],
            'source_y_direction': 'down', 'normalized_y_direction': 'up',
            'meters_per_pixel': None}


def normalize_points(points, frame):
    x0, y0 = frame['origin_px']
    length = frame['long_side_px']
    return [[(x-x0)/length, (y0-y)/length] for x, y in points]


def denormalize_points(points, frame):
    x0, y0 = frame['origin_px']
    length = frame['long_side_px']
    return [[x*length+x0, y0-y*length] for x, y in points]


def rings(geom, frame=None):
    def points(seq):
        p = [list(q) for q in seq[:-1]]
        return normalize_points(p, frame) if frame else p
    return [{'outer': points(list(p.exterior.coords)),
             'holes': [points(list(r.coords)) for r in p.interiors]} for p in polygons(geom)]


def domain_from_rings(parts):
    return unary_union([Polygon(p['outer'], p.get('holes', [])) for p in parts])
