"""
Fetch and cache cropped basemap images for named geographic regions.
 
Usage (from a notebook):
 
    import contextily as cx
    from region_maps import get_region_map
 
    extents = {"min_longitude": 166, "max_longitude": 179,
               "min_latitude": -49,  "max_latitude": -34,}
 
    path = get_region_map("New_Zealand", cx.providers.OpenStreetMap.Mapnik, extents)
 
Requires:
    pip install contextily matplotlib pyproj
    (or: uv add contextily matplotlib pyproj)
"""
 
from pathlib import Path
import contextily as cx
import matplotlib.pyplot as plt
from pyproj import Transformer
import ipywidgets as widgets
from IPython.display import display #, HTML
import matplotlib.image as mpimg
import math
import numpy as np
 
DEFAULT_IMAGES_DIR = Path("basemaps")
DEFAULT_DPI = 200
 
_TO_MERCATOR = Transformer.from_crs("EPSG:4326", "EPSG:3857", always_xy=True)
 
 
def _region_filename(region: str) -> str:
    """Normalize a region label (e.g. 'New_Zealand') to a lowercase filename stem."""
    return region.strip().lower().replace(" ", "_") + ".png"
 

_MERC_FULL_WIDTH = 2 * 20037508.342789244  # circumference of EPSG:3857, in meters

def save_region_map(
    region: str,
    provider,
    extents: dict,
    images_dir: Path | str = DEFAULT_IMAGES_DIR,
    dpi: int = DEFAULT_DPI,
) -> Path:
    images_dir = Path(images_dir)
    out_path = images_dir / _region_filename(region)

    xmin, ymin = extents["min_longitude"], extents["min_latitude"]
    xmax, ymax = extents["max_longitude"], extents["max_latitude"]

    crosses_dateline = xmin > xmax  # e.g. min=178, max=-177

    fig, ax = plt.subplots(figsize=(10, 10))

    if not crosses_dateline:
        img, extent = cx.bounds2img(xmin, ymin, xmax, ymax, source=provider, ll=True)
        crop_xmin, crop_ymin = _TO_MERCATOR.transform(xmin, ymin)
        crop_xmax, crop_ymax = _TO_MERCATOR.transform(xmax, ymax)
        ax.imshow(img, extent=extent)
        ax.set_xlim(crop_xmin, crop_xmax)
        ax.set_ylim(crop_ymin, crop_ymax)
    else:
        # Fetch the two sides of the date line separately, then stitch by
        # shifting the eastern-hemisphere-continuation side by a full world width
        # so it sits immediately right of the western side instead of wrapping.
        img_w, extent_w = cx.bounds2img(xmin, ymin, 180, ymax, source=provider, ll=True)
        img_e, extent_e = cx.bounds2img(-180, ymin, xmax, ymax, source=provider, ll=True)

        extent_e_shifted = (
            extent_e[0] + _MERC_FULL_WIDTH, extent_e[1] + _MERC_FULL_WIDTH,
            extent_e[2], extent_e[3],
        )

        ax.imshow(img_w, extent=extent_w)
        ax.imshow(img_e, extent=extent_e_shifted)

        crop_xmin, crop_ymin = _TO_MERCATOR.transform(xmin, ymin)
        crop_xmax, crop_ymax = _TO_MERCATOR.transform(xmax, ymax)
        crop_xmax += _MERC_FULL_WIDTH  # xmax came from the negative-longitude side

        ax.set_xlim(crop_xmin, crop_xmax)
        ax.set_ylim(min(crop_ymin, crop_ymax), max(crop_ymin, crop_ymax))

    ax.set_axis_off()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_path, dpi=dpi, bbox_inches="tight", pad_inches=0)
    plt.close(fig)

    return out_path


_MERC_MAX = 20037508.342789244
_MERC_FULL_WIDTH = 2 * _MERC_MAX

def _fetch_wrapped_basemap(xmin, ymin, xmax, ymax, source):
    """
    Fetch contextily tile image(s) for a Web Mercator bbox that may extend
    beyond the standard ±_MERC_MAX world range (e.g. after panning across
    the antimeridian). Tiles only exist in that standard range, so any
    portion outside it is fetched from its "wrapped" position and the
    resulting image shifted back into the caller's coordinate space.

    Returns a list of (img, extent) tuples, each ready to pass to ax.imshow.
    """
    def world_index(x):
        return math.floor((x + _MERC_MAX) / _MERC_FULL_WIDTH)

    k_min = world_index(xmin)
    k_max = world_index(xmax - 1e-6)  # avoid a boundary value spilling into the next world

    pieces = []
    for k in range(k_min, k_max + 1):
        world_left = -_MERC_MAX + k * _MERC_FULL_WIDTH
        world_right = _MERC_MAX + k * _MERC_FULL_WIDTH
        seg_xmin = max(xmin, world_left)
        seg_xmax = min(xmax, world_right)
        if seg_xmax <= seg_xmin:
            continue
        shift = k * _MERC_FULL_WIDTH
        img, extent = cx.bounds2img(seg_xmin - shift, ymin, seg_xmax - shift, ymax,
                                     source=source, ll=False)
        pieces.append((img, (extent[0] + shift, extent[1] + shift, extent[2], extent[3])))
    return pieces


def _wrap_lon(lon):
    """Wrap a longitude to (-180, 180]."""
    return ((lon + 180) % 360) - 180


def _square_mercator_extents(xmin, ymin, xmax, ymax):
    """
    Expand the smaller of (width, height) in a Web Mercator bbox so both
    match, keeping the same center. Ensures zoom/pan starting from this
    bbox stays square instead of inheriting an arbitrary aspect ratio.
    """
    width = xmax - xmin
    height = ymax - ymin
    side = max(width, height)
    cx_, cy_ = (xmin + xmax) / 2, (ymin + ymax) / 2
    return (cx_ - side / 2, cy_ - side / 2, cx_ + side / 2, cy_ + side / 2)


def plot_points_on_cx_basemap(df, extents, lat_col='latitude', lon_col='longitude',
                            basemap_source=None, figsize=(8, 8), point_kwargs=None,
                            zoom_factor=1.5, pan_fraction=0.25):
    to_3857 = Transformer.from_crs("EPSG:4326", "EPSG:3857", always_xy=True)
    to_4326 = Transformer.from_crs("EPSG:3857", "EPSG:4326", always_xy=True)

    crosses_dateline = extents['min_longitude'] > extents['max_longitude']

    # Points normally have lon in [-180, 180]. If the region straddles the
    # dateline, any point whose lon falls "east" of it (i.e. less than the
    # region's western edge) actually continues the view to the right, so
    # give it +360 to sit in the same continuous coordinate space.
    lons = df[lon_col].values.astype(float).copy()
    if crosses_dateline:
        lons = np.where(lons < extents['min_longitude'], lons + 360, lons)
        max_lon_cont = extents['max_longitude'] + 360
    else:
        max_lon_cont = extents['max_longitude']

    x, y = to_3857.transform(lons, df[lat_col].values)
    xmin, ymin = to_3857.transform(extents['min_longitude'], extents['min_latitude'])
    xmax, ymax = to_3857.transform(max_lon_cont, extents['max_latitude'])
    xmin, ymin, xmax, ymax = _square_mercator_extents(xmin, ymin, xmax, ymax)

    with plt.ioff():
        fig, ax = plt.subplots(figsize=figsize)
        fig.canvas.toolbar_visible = False   # pan/zoom/save icons above the plot
        fig.canvas.header_visible = False    # "Figure N" title above the plot
        fig.canvas.footer_visible = False    # hover coordinates below the plot
        fig.canvas.resizable = False         # drag-to-resize handle (optional)

    default_point_kwargs = dict(s=20, c='red', alpha=0.8, edgecolor='k', linewidth=0.5, zorder=3)
    if point_kwargs:
        default_point_kwargs.update(point_kwargs)
    ax.scatter(x, y, **default_point_kwargs)

    ax.set_xlim(xmin, xmax)
    ax.set_ylim(ymin, ymax)
    ax.set_axis_off()

    _basemap_state = {'artists': []}

    def refresh_basemap():
        for artist in _basemap_state['artists']:
            try:
                artist.remove()
            except Exception:
                pass
        cur_xmin, cur_xmax = ax.get_xlim()
        cur_ymin, cur_ymax = ax.get_ylim()
        _basemap_state['artists'] = [
            ax.imshow(img, extent=extent, zorder=1)
            for img, extent in _fetch_wrapped_basemap(cur_xmin, cur_ymin, cur_xmax, cur_ymax, basemap_source)
        ]
        fig.canvas.draw_idle()

    refresh_basemap()
    plt.tight_layout()

    def zoom(factor):
        cur_xmin, cur_xmax = ax.get_xlim()
        cur_ymin, cur_ymax = ax.get_ylim()
        cx_, cy_ = (cur_xmin + cur_xmax) / 2, (cur_ymin + cur_ymax) / 2
        new_w = (cur_xmax - cur_xmin) * factor
        new_h = (cur_ymax - cur_ymin) * factor
        ax.set_xlim(cx_ - new_w / 2, cx_ + new_w / 2)
        ax.set_ylim(cy_ - new_h / 2, cy_ + new_h / 2)
        refresh_basemap()

    def pan(dx_frac, dy_frac):
        cur_xmin, cur_xmax = ax.get_xlim()
        cur_ymin, cur_ymax = ax.get_ylim()
        dx = (cur_xmax - cur_xmin) * dx_frac
        dy = (cur_ymax - cur_ymin) * dy_frac
        ax.set_xlim(cur_xmin + dx, cur_xmax + dx)
        ax.set_ylim(cur_ymin + dy, cur_ymax + dy)
        refresh_basemap()

    btn_width = "120px"
    btn_height = "40px"
    btn_layout = widgets.Layout(width=btn_width, height=btn_height)

    btn_zoom_in = widgets.Button(description="Zoom In", icon="plus", layout=btn_layout)
    btn_zoom_out = widgets.Button(description="Zoom Out", icon="minus", layout=btn_layout)
    btn_up = widgets.Button(description="↑", layout=btn_layout)
    btn_down = widgets.Button(description="↓", layout=btn_layout)
    btn_left = widgets.Button(description="←", layout=btn_layout)
    btn_right = widgets.Button(description="→", layout=btn_layout)

    btn_zoom_in.on_click(lambda b: zoom(1 / zoom_factor))
    btn_zoom_out.on_click(lambda b: zoom(zoom_factor))
    btn_up.on_click(lambda b: pan(0, pan_fraction))
    btn_down.on_click(lambda b: pan(0, -pan_fraction))
    btn_left.on_click(lambda b: pan(-pan_fraction, 0))
    btn_right.on_click(lambda b: pan(pan_fraction, 0))

    zoom_row = widgets.HBox([btn_zoom_out, btn_zoom_in])
    lr_row = widgets.HBox([btn_left, btn_right], layout=widgets.Layout(gap="0px"))
    pan_grid = widgets.VBox(
        [btn_up, lr_row, btn_down],
        layout=widgets.Layout(align_items="center"),
    )

    controls = widgets.VBox(
        [zoom_row, pan_grid],
        layout=widgets.Layout(align_items="center", justify_content="center", margin="24px 24px 24px 24px", width="auto"),
    )

    fig.canvas.layout.width = f"{figsize[0]}in"
    fig.canvas.layout.flex = "0 0 auto"

    layout = widgets.HBox(
        [fig.canvas, controls],
        layout=widgets.Layout(align_items="flex-start"),
    )
    display(layout)


    def get_extents():
        cur_xmin, cur_xmax = ax.get_xlim()
        cur_ymin, cur_ymax = ax.get_ylim()
        lon_min_raw, lat_min = to_4326.transform(cur_xmin, cur_ymin)
        lon_max_raw, lat_max = to_4326.transform(cur_xmax, cur_ymax)
        return {
            'min_latitude': round(lat_min,2), 'max_latitude': round(lat_max,2),
            'min_longitude':round(_wrap_lon(lon_min_raw), 2), 'max_longitude':round( _wrap_lon(lon_max_raw),2),
            #'min_longitude':round(lon_min_raw, 2), 'max_longitude':round(lon_max_raw,2),
        }

    return fig, ax, get_extents


def plot_points_on_saved_basemap(map_path, extents, df, lat_col='latitude', lon_col='longitude',
                                   figsize=(3, 3), title=None, point_kwargs=None):
    """
    Static (non-interactive) plot of a previously-saved basemap PNG (from
    save_region_map) with lat/lon points overlaid, positioned using the same
    WGS84 extents dict that was used to create the PNG.

    Plots in EPSG:3857 (Web Mercator) internally, matching the projection the
    PNG was actually rendered in, so the image isn't visually distorted.

    Uses a fresh figure only — does not touch the global matplotlib backend,
    so it's safe to run alongside an existing %matplotlib widget interactive
    plot in the same notebook session.

    extents : dict with 'min_longitude', 'max_longitude', 'min_latitude',
              'max_latitude' (WGS84 degrees) — must match what was passed to
              save_region_map when map_path was created.
    """
    to_3857 = Transformer.from_crs("EPSG:4326", "EPSG:3857", always_xy=True)
    img = mpimg.imread(map_path)

    crosses_dateline = extents['min_longitude'] > extents['max_longitude']

    xmin, ymin = to_3857.transform(extents['min_longitude'], extents['min_latitude'])
    xmax, ymax = to_3857.transform(extents['max_longitude'], extents['max_latitude'])

    if crosses_dateline:
        xmax += _MERC_FULL_WIDTH  # shift the wrapped-around edge back into continuous space

    lons = df[lon_col].values.astype(float).copy()
    lats = df[lat_col].values
    x, y = to_3857.transform(lons, lats)
    if crosses_dateline:
        x = np.where(lons < extents['min_longitude'], x + _MERC_FULL_WIDTH, x)

    x, y = to_3857.transform(lons, df[lat_col].values)

    print(f'x diff: {xmax - xmin}, y diff: {ymax - ymin}, x/y ratio: {(xmax - xmin) / (ymax - ymin)}')

    fig, ax = plt.subplots(figsize=figsize)

    ax.imshow(img, extent=(xmin, xmax, ymin, ymax), origin='upper')

    default_point_kwargs = dict(s=20, c='red', alpha=0.8, edgecolor='k', linewidth=0.5, zorder=3)
    if point_kwargs:
        default_point_kwargs.update(point_kwargs)
    ax.scatter(x, y, **default_point_kwargs)

    ax.set_xlim(xmin, xmax)
    ax.set_ylim(ymin, ymax)
    ax.set_aspect('equal', adjustable='box')
    ax.set_axis_off()
    if title is not None:
        ax.set_title(title)
    plt.tight_layout()
    plt.show()

    return fig, ax


def validate_wgs84(df, lat_col='latitude', lon_col='longitude'):
    if lat_col not in df.columns or lon_col not in df.columns:
        raise ValueError(f"Missing expected columns: {lat_col!r}, {lon_col!r}")

    lat = df[lat_col]
    lon = df[lon_col]
    n = len(df)

    if n == 0:
        warnings_list = ["DataFrame is empty."]
        print(f"WARNING: {warnings_list[0]}")
        return {"valid": False, "n_valid": 0, "n_total": 0, "warnings": warnings_list}

    warnings_list = []

    lat_null = lat.isna()
    lon_null = lon.isna()

    if lat_null.all():
        warnings_list.append(f"'{lat_col}' is entirely empty (all NaN).")
    if lon_null.all():
        warnings_list.append(f"'{lon_col}' is entirely empty (all NaN).")

    n_lat_null = lat_null.sum()
    n_lon_null = lon_null.sum()
    if 0 < n_lat_null < n:
        warnings_list.append(f"'{lat_col}' has {n_lat_null} missing value(s) out of {n}.")
    if 0 < n_lon_null < n:
        warnings_list.append(f"'{lon_col}' has {n_lon_null} missing value(s) out of {n}.")

    lat_numeric = pd.to_numeric(lat, errors='coerce')
    lon_numeric = pd.to_numeric(lon, errors='coerce')

    bad_lat_dtype = lat_numeric.isna() & ~lat_null
    bad_lon_dtype = lon_numeric.isna() & ~lon_null
    if bad_lat_dtype.any():
        warnings_list.append(f"'{lat_col}' has {bad_lat_dtype.sum()} non-numeric value(s).")
    if bad_lon_dtype.any():
        warnings_list.append(f"'{lon_col}' has {bad_lon_dtype.sum()} non-numeric value(s).")

    valid_mask = lat_numeric.notna() & lon_numeric.notna()
    out_of_range_lat = valid_mask & ((lat_numeric < -90) | (lat_numeric > 90))
    out_of_range_lon = valid_mask & ((lon_numeric < -180) | (lon_numeric > 180))

    if out_of_range_lat.any():
        bad_vals = lat_numeric[out_of_range_lat].unique()[:5]
        warnings_list.append(
            f"'{lat_col}' has {out_of_range_lat.sum()} value(s) outside [-90, 90], e.g. {list(bad_vals)}."
        )
    if out_of_range_lon.any():
        bad_vals = lon_numeric[out_of_range_lon].unique()[:5]
        warnings_list.append(
            f"'{lon_col}' has {out_of_range_lon.sum()} value(s) outside [-180, 180], e.g. {list(bad_vals)}."
        )

    null_island = valid_mask & (lat_numeric == 0) & (lon_numeric == 0)
    if null_island.any():
        warnings_list.append(
            f"{null_island.sum()} row(s) have coordinates (0, 0) — "
            f"often a placeholder for missing GPS data rather than a real location."
        )

    n_valid = (valid_mask & ~out_of_range_lat & ~out_of_range_lon).sum()

    for w in warnings_list:
        print(f"WARNING: {w}")

    print(f"{n_valid}/{n} rows have valid WGS84 lat/lon values.")

    return {
        "valid": n_valid > 0 and len(warnings_list) == 0,
        "n_valid": n_valid,
        "n_total": n,
        "warnings": warnings_list,
    }


def populate_random_points(df, extents, lat_col='latitude', lon_col='longitude',
                            random_seed=None, inplace=False):
    """
    Fill lat/lon columns with random points uniformly sampled within `extents`.

    extents: dict with keys 'min_latitude', 'max_latitude', 'min_longitude', 'max_longitude'.
    inplace: if False (default), returns a modified copy; if True, mutates df directly.
    """
    required_keys = {'min_latitude', 'max_latitude', 'min_longitude', 'max_longitude'}
    missing_keys = required_keys - extents.keys()
    if missing_keys:
        raise ValueError(f"extents dict is missing key(s): {missing_keys}")

    target = df if inplace else df.copy()
    n = len(target)

    rng = np.random.default_rng(random_seed)
    target[lat_col] = rng.uniform(extents['min_latitude'], extents['max_latitude'], size=n)
    target[lon_col] = rng.uniform(extents['min_longitude'], extents['max_longitude'], size=n)

    print(f"Populated {n} row(s) with random points within extents {extents}.")

    return target