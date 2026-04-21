import os
os.environ["POLARS_UNKNOWN_EXTENSION_TYPE_BEHAVIOR"] = "load_as_storage"

import geopandas as gpd
from shapely import wkb
#import pyarrow
import polars as pl 

from plotnine import (
    ggplot, geom_map, coord_fixed, labs,
    theme_void, theme, element_text, element_rect)

from shiny.express import input, render, ui

ui.input_radio_buttons(  
    id = "param_ccaa",  
    label = "Comunidad Autónoma",  
    choices ={"14": "Murcia", "15": "Navarra"},
    inline = True
)  


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

def prep_municipios(ccaa_code:str) -> gpd.GeoDataFrame:
    # Filtra municipios de la CCAA seleccionada
    por_ccaa = (
        pl.scan_parquet(os.path.join("products", "geo", "municipios.parquet"))
        .filter(pl.col("CCAA_CODINE") == ccaa_code) 
        .collect()
    ).to_pandas()

    # Descodifica columna geometry (almacenada en WKB) para uso en gpd
    por_ccaa["geometry"] = por_ccaa["geometry"].apply(lambda x: wkb.loads(x))
    gdf = gpd.GeoDataFrame(por_ccaa, geometry="geometry", crs=CRC_spherical)

    return gdf

@render.plot
def plot_municipios():
    param_ccaa = input.param_ccaa()
    muni_gdf = prep_municipios(param_ccaa)

    return (
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
