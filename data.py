from shapely import wkb
import geopandas as gpd
import polars as pl 

from pathlib import Path
from faicons import icon_svg

from plotnine import (
    theme_void, theme, element_text, element_rect)

app_path = Path(__file__).parent
AS_FILE = app_path / "products" / "geo" / "as.parquet"
MUNICIPIOS_FILE = app_path / "products" / "geo" / "municipios.parquet"
NANDA_PERIODOS_FILE = app_path / "products" / "nanda_periodos.parquet"

CRC_PROJECTED = "EPSG:3857" # Web Mercator
CRC_SPHERICAL = "EPSG:4326" # WGS84: lat/lon values

ICONS = {
    "participantes": icon_svg("users", "solid"),
    "municipios": icon_svg("city"),
    "areas-salud": icon_svg("house-medical"),
}

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


# Data preparation functions
def geodata_municipios() -> gpd.GeoDataFrame:
    """
    Carga un GeoDataFrame de municipios.
    """
    df = (
        pl.scan_parquet(MUNICIPIOS_FILE)
        .collect()
    ).to_pandas()

    # Descodifica columna geometry (almacenada en WKB) para uso en gpd
    df["geometry"] = df["geometry"].apply(lambda x: wkb.loads(x))
    gdf = gpd.GeoDataFrame(df, geometry="geometry", crs=CRC_SPHERICAL)

    return gdf

def geodata_areas_salud() -> gpd.GeoDataFrame:
    """
    Carga un GeoDataFrame de áreas de salud.
    """
    df = (
        pl.scan_parquet(AS_FILE)
        .collect()
    ).to_pandas()

    # Descodifica columna geometry (almacenada en WKB) para uso en gpd
    df["geometry"] = df["geometry"].apply(lambda x: wkb.loads(x))
    gdf = gpd.GeoDataFrame(df, geometry="geometry", crs=CRC_SPHERICAL)

    return gdf


def nanda_periodos_data() -> pl.DataFrame:
    return (
        pl.scan_parquet(NANDA_PERIODOS_FILE)
        .filter(
            pl.col("TIPO_DIAGNOSTICO") == "Disfuncionalidad"
        )
        .drop("TIPO_DIAGNOSTICO")
        .collect()
    )

municipios = geodata_municipios()
areas_salud = geodata_areas_salud()
nanda_periodos = nanda_periodos_data()

        