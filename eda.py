
import os
os.environ["POLARS_UNKNOWN_EXTENSION_TYPE_BEHAVIOR"] = "load_as_storage"
#import pandas as pd
import geopandas as gpd
from shapely import wkb
import pyarrow
import polars as pl 

from plotnine import (
    ggplot, geom_map, coord_fixed, labs,
    theme_void, theme, element_text, element_rect)


CRC_projected = "EPSG:3857" # Web Mercator
CRC_spherical = "EPSG:4326" # WGS84: lat/lon values

BASE_THEME_VOID = (
    theme_void()
    + theme(
        plot_background=element_rect(fill="white"),
        plot_title=element_text(size=12, weight="bold", margin={"b": 4}),
        plot_subtitle=element_text(size=10, color="#5F5E5A", margin={"b": 8}),
        plot_caption=element_text(size=8, color="#888780", margin={"t": 6}),
        legend_title=element_text(size=8),
        legend_text=element_text(size=7),
        #figure_size=(10, 7),
        aspect_ratio=1
    )
)

#param_periodo = "PRE-PANDEMIA"  # "INTRA-PANDEMIA, "POST-PANDENIA"
param_ccaa = "14"

por_ccaa = (
    pl.scan_parquet(os.path.join("products", "geo", "municipios.parquet"))
    .filter(pl.col("CCAA_CODINE") == param_ccaa) # Filtra municipios de la CCAA seleccionada
    .collect()
).to_pandas()

# Descodifica columna geometry (almacenada en WKB) para uso en gpd
por_ccaa["geometry"] = por_ccaa["geometry"].apply(lambda x: wkb.loads(x))
muni_gdf = gpd.GeoDataFrame(por_ccaa, geometry="geometry", crs=CRC_spherical)

p = (
    ggplot(muni_gdf)
    + geom_map(
        color="grey",
        fill="white",
        size=0.3
    )
    + coord_fixed(ratio=1, expand=True)
    + labs(
        title="Municipios"
    )
    + BASE_THEME_VOID
)

p