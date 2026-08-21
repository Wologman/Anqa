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
 
DEFAULT_IMAGES_DIR = Path("basemaps")
DEFAULT_DPI = 200
 
_TO_MERCATOR = Transformer.from_crs("EPSG:4326", "EPSG:3857", always_xy=True)
 
 
def _region_filename(region: str) -> str:
    """Normalize a region label (e.g. 'New_Zealand') to a lowercase filename stem."""
    return region.strip().lower().replace(" ", "_") + ".png"
 
 
def save_region_map(
    region: str,
    provider,
    extents: dict,
    images_dir: Path | str = DEFAULT_IMAGES_DIR,
    dpi: int = DEFAULT_DPI,
) -> Path:
    """
    Return the path to a cropped basemap PNG for `region`, fetching and
    caching it first if it doesn't already exist.
 
    Parameters
    ----------
    region : str
        Region name, e.g. "New_Zealand". Used (lowercased) as the output
        filename and as the lookup key into `extents`.
    provider : contextily tile provider
        e.g. cx.providers.OpenStreetMap.Mapnik
    extents : dict
        Mapping of region name -> {"min_longitude", "max_longitude",
        "min_latitude", "max_latitude"} in WGS84 degrees.
    images_dir : Path or str
        Directory to check for an existing PNG / save a new one into.
    dpi : int
        Output resolution for the saved PNG.
 
    Returns
    -------
    Path to the (existing or newly created) PNG file.
    """
    images_dir = Path(images_dir)
    out_path = images_dir / _region_filename(region)

    xmin, ymin = extents["min_longitude"], extents["min_latitude"]
    xmax, ymax = extents["max_longitude"], extents["max_latitude"]
     
    img, extent = cx.bounds2img(
        xmin, ymin, xmax, ymax,
        source=provider,
        ll=True,  # bounds are in lon/lat (EPSG:4326)
    )
    
    # bounds2img returns whole tiles, so the image covers a bit more than the
    # requested bbox. `extent` always comes back in EPSG:3857 regardless of
    # ll=True, so tightening the crop to the exact requested edges needs the
    # bbox reprojected to that same CRS.
    crop_xmin, crop_ymin = _TO_MERCATOR.transform(xmin, ymin)
    crop_xmax, crop_ymax = _TO_MERCATOR.transform(xmax, ymax)
    
    fig, ax = plt.subplots(figsize=(10, 10))
    ax.imshow(img, extent=extent)
    ax.set_xlim(crop_xmin, crop_xmax)
    ax.set_ylim(crop_ymin, crop_ymax)
    ax.set_axis_off()
    
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_path, dpi=dpi, bbox_inches="tight", pad_inches=0)
    plt.close(fig)

    return out_path