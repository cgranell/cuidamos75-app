from pathlib import Path

import geopandas as gpd
import polars as pl
from faicons import icon_svg
from plotnine import element_rect, element_text, theme, theme_void
from shapely import wkb

from plots import get_class_colormap, get_domain_colormap

app_path = Path(__file__).parent
AS_FILE = app_path / "products" / "as.parquet"
MUNICIPIOS_FILE = app_path / "products" / "municipios.parquet"
NANDA_PERIODOS_FILE = app_path / "products" / "nanda_periodos.parquet"
POBLACION_FILE = app_path / "products" / "poblacion.parquet"
INEATLAS_FILE = app_path / "products" / "ineAtlas_demographics_mun.parquet"

CRC_PROJECTED = "EPSG:3857" # Web Mercator
CRC_SPHERICAL = "EPSG:4326" # WGS84: lat/lon values

ICONS = {
    "participantes": icon_svg("users", "solid"),
    "municipios": icon_svg("city"),
    "areas-salud": icon_svg("house-medical"),
    "info": icon_svg("circle-info"),
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
        #aspect_ratio=1
    )
)


THEME_LEGEND_BOTTOM = (
    theme(
        legend_position="bottom",
        legend_direction="vertical",
        legend_title=element_text(size=8),
        legend_text=element_text(size=7),
        legend_key_size=8,
    )
)

# Data preparation functions

def geodata_ineatlas() -> gpd.GeoDataFrame:
    """
    Carga un GeoDataFrame de ineAtlas.
    """
    df = (
        pl.scan_parquet(INEATLAS_FILE)
        .collect()
    ).to_pandas()

    # Descodifica columna geometry (almacenada en WKB) para uso en gpd
    df["geometry"] = df["geometry"].apply(lambda x: wkb.loads(x))
    gdf = gpd.GeoDataFrame(df, geometry="geometry", crs=4258)  # ETRS89, matches source
    
    return gdf


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
    gdf = gdf.set_crs(3857, allow_override=True).to_crs(4326)
    
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
    gdf = gdf.set_crs(3857, allow_override=True).to_crs(4326)
    
    return gdf


def nanda_periodos_data() -> pl.DataFrame:
    return (
        pl.scan_parquet(NANDA_PERIODOS_FILE)
        .filter(
            pl.col("TIPO_DIAGNOSTICO") == "Disfuncionalidad"
        )
        #.with_columns( #TODO: revisar tipos de datos en fuente (parquet)
        #    pl.col("PACIENTE_ID").cast(pl.String)
        #)
        .drop("TIPO_DIAGNOSTICO")
        .collect()
    )

def participantes_data() -> pl.DataFrame:
    return (
        pl.scan_parquet(POBLACION_FILE)
        .select(
            pl.col("CCAA_CODINE"),
            pl.col("PACIENTE_ID"),
            pl.col("PACIENTE_CP"),
            pl.col("MUNI_CODINE"),
            pl.col("MUNI_DESC"),
            pl.col("AS_ID"),
            pl.col("AS_DESC")
        )
        #.with_columns( #TODO: revisar tipos de datos en fuente (parquet)
        #    pl.col("PACIENTE_ID").cast(pl.String),
        #    pl.col("AS_ID").cast(pl.Int64)
        #)
        .collect()
    )

municipios = geodata_municipios()
areas_salud = geodata_areas_salud()
nanda_periodos = nanda_periodos_data()
participantes = participantes_data()
ineatlas = geodata_ineatlas()


# Build once from your base data (not filtered) so colors are stable
MASTER_COLORMAP_DOMINIO = get_domain_colormap(nanda_periodos, domain_col="DOMINIO_LABEL")
MASTER_COLORMAP_CLASES = get_class_colormap(nanda_periodos, class_col="CLASE")
COLOR_NA = "#cccccc"
        