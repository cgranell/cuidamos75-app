import geopandas as gpd
import numpy as np
import pandas as pd
import plotly.express as px
import polars as pl
from plotnine import (
    aes,
    coord_fixed,
    geom_map,
    #geom_text,
    ggplot,
    labs,
    scale_fill_brewer,
    scale_fill_manual,
)
from polars import selectors as cs
from pypalettes import load_palette

# https://plotly.com/python/discrete-color/
COLOR_PALETTE = px.colors.qualitative.Dark24

# https://pypi.org/project/pypalettes/
# Python Color Palette Finder: https://python-graph-gallery.com/color-palette-finder/
CONTEXT_PALETTE = load_palette("Autumn", repeat=5)

def get_domain_colormap(df: pl.DataFrame, domain_col: str = "DOMINIO") -> dict:
    """
    Returns a consistent color mapping for all distinct domains.
    Colors are assigned alphabetically to ensure consistency across plots.
    """
    
    domains = sorted(df[domain_col].drop_nulls().unique().to_list())
    return {
        domain: COLOR_PALETTE[i]
        for i, domain in enumerate(domains)
    }


def get_class_colormap(df: pl.DataFrame, class_col: str = "CLASE") -> dict:
    """
    Returns a consistent color mapping for all distinct classes.
    Colors are assigned alphabetically to ensure consistency across plots.
    """
    
    classes = sorted(df[class_col].drop_nulls().unique().to_list())
    print(f"number of clases {len(classes)}")
    return {
        cls: CONTEXT_PALETTE[i]
        for i, cls in enumerate(classes)
    }


def plotly_heatmap_dominios(
    df: pl.DataFrame,
    geom_var: str = "MUNI_DESC",
    cmap: str = "YlOrRd",
    log_scale: bool = True):

    if df is None or df.is_empty():
        # Create an empty px.imshow with a "no data" message
        fig = px.imshow(
            [[0]],
            color_continuous_scale=cmap,
            aspect="auto",
        )
        fig.update_traces(
            hoverinfo="skip",
        )
        fig.update_layout(
            xaxis={"visible": False},
            yaxis={"visible": False},
            annotations=[
                {
                    "text": "Sin datos disponibles",
                    "xref": "paper", "yref": "paper",
                    "x": 0.5, "y": 0.5,
                    "showarrow": False,
                    "font": {"size": 16, "color": "gray"},
                }
            ],
        )
        return fig

    # Separate labels and numeric data
    # issue is that empty strings or nulls (no muni desc) cause misaligned or broken labels. 
    # Replace them with a placeholder:
    labels = (
           df[geom_var]
            .fill_null("(Sin nombre)")
            .cast(pl.String)
            .replace("", "(Sin nombre)")
            .to_list()
    )

    numeric_df = df.drop(geom_var)
    # Sort columns alphabetically for consistent x-axis order
    numeric_df = numeric_df.select(sorted(numeric_df.columns))

    # log scale: ln(1+x)
    plot_df = numeric_df.select(cs.numeric().log1p()) if log_scale else numeric_df.select(cs.numeric())

    # Convert to numpy for plotly
    z = plot_df.to_numpy()
    z_text = numeric_df.to_numpy()  # raw values for annotation

    fig = px.imshow(
        z,
        x=plot_df.columns,
        y=labels,
        color_continuous_scale=cmap,
        range_color=[z.min(), z.max()],  # ensures low=yellow, high=red
        aspect="auto",
        labels={"color": "Casos totales (escala log)" if log_scale else "Casos totales"},
        text_auto=False,  # we supply custom text below
    )

    # Annotate with raw (non-log) values
    fig.update_traces(
        text=z_text,
        texttemplate="%{text:.0f}",
        textfont_size=7,
    )

    fig.update_layout(
        xaxis={"tickangle": 45, "tickfont_size": 8, "side": "bottom"},
        yaxis={"tickfont_size": 8, "autorange": "reversed"},  # top-to-bottom row order
        coloraxis_colorbar={"title_side": "right"}
        #margin=dict(l=120, r=40, t=40, b=120),
    )

    return fig


def plotly_donut_clases(
    df: pl.DataFrame,
    message: str, # "municipio" o "área de salud" para el mensaje de "haz clic en..." cuando no hay datos
    cmap: dict,
    var_categorical: str = "CLASE",
    var_numeric: str = "CLASE_TOTAL"):
    
    if df is None or df.is_empty():
        fig = px.pie(names=[], values=[], hole=0.55)
        fig.update_layout(
            annotations=[{"text": f"Haz clic en {message} <br>para ver la(s) clase(s) por dominio prevalente",
            "x": 0.5, "y": 0.5, "showarrow": False, "font": {"size": 13}}],
            margin={"t": 30, "b": 10, "l": 10, "r": 10},
        )
        return fig
    
    
    fig = px.pie(
        df.to_pandas(),
        names=var_categorical,
        values=var_numeric,
        hole=0.55,
        color=var_categorical,
        color_discrete_map=cmap,   # keep colors stable across municipios
    )

    fig.update_traces(
        textposition="outside",
        textinfo="percent+label",
        sort=False,                 # don't reorder slices -> stable colors
        hovertemplate="<b>%{label}</b><br>%{value} (%{percent})<extra></extra>",
    )
    fig.update_layout(
        showlegend=False,            # labels are on the slices; legend is redundant
        #margin=dict(t=40, b=10, l=10, r=10),
        annotations=[{"text": f"{int(df[var_numeric].sum())}<br>casos",
                        "x": 0.5, "y": 0.5, "showarrow": False, "font": {"size": 15}}],
    )
    return fig


def fermenter_labels(breaks, fmt="{:,.0f}"):
    """
    Build scale_fill_fermenter-style range labels for N breaks -> N+1 bins,
    matching the ±Inf outer-bin convention.
    """
    formatted = [fmt.format(b) for b in breaks]
    labels = [f"< {formatted[0]}"]
    labels += [f"{formatted[i]}–{formatted[i+1]}" for i in range(len(formatted) - 1)]
    labels.append(f"> {formatted[-1]}")
    return labels

def p9_ineatlas_mean_age(
    gdf: gpd.GeoDataFrame,
    color_na: str,
    base_theme: str):

    median_age = 48.2
    gap_in_years = 2
    bins = median_age + gap_in_years * np.arange(-3, 4) 
    # pd.cut() treats the bin edges as hard limits, 
    # anything outside [min(bins), max(bins)] gets NaN, which then renders as na_value
    bin_edges = np.concatenate(([-np.inf], bins, [np.inf]))  # 9 edges -> 8 bins
    age_labels = fermenter_labels(bins, fmt="{:,.1f}")
    
    # plotnine has no scale_fill_fermenter equivalent, so bin mean_age manually
    # to reproduce the same discrete/binned legend behavior
    gdf["mean_age_bin"] = pd.cut(
        gdf["mean_age"],
        bins=bin_edges,           # same numeric breakpoints as your R `bins` vector
        labels=age_labels,
        include_lowest=True,
    )

    return (
        ggplot()
        
        + geom_map(
            data=gdf,
            mapping=aes(fill="mean_age_bin"),
            color="none")
        + scale_fill_brewer(
            type="div",
            palette="RdBu",
            direction=-1,        # red = older, blue = younger
            name="Edad media (años)",
            na_value=color_na,
        )

        + coord_fixed(ratio=1, expand=True)
        + base_theme
    )




def p9_ineatlas_pop(
    gdf: gpd.GeoDataFrame,
    color_na: str,
    base_theme: str):

    bins = np.array([500, 1000, 5000, 10000, 50000, 100000])  # 6 breaks -> 7 bins
    bin_edges = np.concatenate(([-np.inf], np.log10(bins), [np.inf]))

    population_log = np.log10(gdf["population"])
    pop_labels = fermenter_labels(bins, fmt="{:,.0f}")

    gdf["population_bin"] = pd.cut(
        population_log,
        bins=bin_edges,
        labels=pop_labels,
        include_lowest=True,
    )

    return (
        ggplot()
        
        + geom_map(
            data=gdf,
            mapping=aes(fill="population_bin"),
            color="none")
        + scale_fill_brewer(
            type="seq",
            palette="YlGnBu",
            direction=1,        #  # dark = more populated
            name="Población",
            na_value=color_na,
        )

        + coord_fixed(ratio=1, expand=True)
        + base_theme
    )


def p9_ineatlas_pop_density(
    gdf: gpd.GeoDataFrame,
    color_na: str,
    base_theme: str):

    # 6 breaks -> 7 bins, log-spaced round numbers
    bins = np.array([10, 50, 100, 500, 1000, 5000])  # 6 breaks -> 7 bins
    bin_edges = np.concatenate(([-np.inf], np.log10(bins), [np.inf]))

    pop_density_log = np.log10(gdf["pop_density"])
    pop__density_labels = fermenter_labels(bins, fmt="{:,.0f}")

    gdf["pop_density_bin"] = pd.cut(
        pop_density_log,
        bins=bin_edges,
        labels=pop__density_labels,
        include_lowest=True,
    )

    return (
        ggplot()
        
        + geom_map(
            data=gdf,
            mapping=aes(fill="pop_density_bin"),
            color="none")
        + scale_fill_brewer(
            type="seq",
            palette="YlGnBu",
            direction=1,        #  # dark = more populated
            name="Densidad de población\n(hab/km²)",
            na_value=color_na,
        )

        + coord_fixed(ratio=1, expand=True)
        + base_theme
    )

def p9_ineatlas_over65(
    gdf: gpd.GeoDataFrame,
    color_na: str,
    base_theme: str):

    ref = 20  # national share of 65+, or weighted.mean(demographics_mun$pct_over65, w = demographics_mun$population)

    # 6 breaks -> 7 bins, 
    bins = ref + np.array([-15, -10, -5, 0, 5, 10, 15])
    bin_edges = np.concatenate(([-np.inf], bins, [np.inf]))  # 9 edges -> 8 bins
    over65_labels = fermenter_labels(bins, fmt="{:,.0f}")
    
    # plotnine has no scale_fill_fermenter equivalent, so bin mean_age manually
    # to reproduce the same discrete/binned legend behavior
    gdf["pct_over65_bin"] = pd.cut(
        gdf["pct_over65"],
        bins=bin_edges, 
        labels=over65_labels,
        include_lowest=True,
    )

    return (
        ggplot()
        
        + geom_map(
            data=gdf,
            mapping=aes(fill="pct_over65_bin"),
            color="none")
        + scale_fill_brewer(
            type="div",
            palette="RdBu",
            direction=-1,        # red = older, blue = younger
            name="Población de 65+ (%)",
            na_value=color_na,
        )

        + coord_fixed(ratio=1, expand=True)
        + base_theme
    )


"""
def leaflet_map_dominio_prevalente(
    gdf: gpd.GeoDataFrame,
    geom_var: str = "AS_DESC",
    domain_col: str = "DOMINIO_PREVALENTE") -> Map: 

    # Mapa coropleta por área de salut (with leaflet, categorical cloropeth)
    # leaflet needs WGS84 lon/lat, but our geodata is already in that CRS (EPSG:4326), so we can use it directly
    # We need to convert the geodataframe to GeoJSON format for use in leaflet                
    selected_gdf_json = json.loads(gdf.to_json())
                
    # categorical fill: replaces scale_fill_manual(values=..., na_value=...)
    def style_callback(feature):
        dom = feature["properties"].get(domain_col)
        color = COLOR_NA if dom is None else MASTER_COLORMAP_DOMINIO.get(dom, COLOR_NA)
        return {
            "fillColor": color,
            "color": "gray",     # was color="gray"
            "weight": 0.3,       # was size=0.3 (line width)
            "fillOpacity": 0.60,
        }

    layer = GeoJSON (
        data=selected_gdf_json,
        style_callback=style_callback,
        hover_style={"weight": 1.2, "color": "black"}, # hovered municipality/as outlines itself 
    )

    # centre on the data extent
    minx, miny, maxx, maxy = gdf.total_bounds
    center = ((miny + maxy) / 2, (minx + maxx) / 2)   # (lat, lon)

    m = Map(
        center=center,
        zoom=9,
        basemap=basemaps.CartoDB.Positron, 
        scroll_wheel_zoom=True)
    m.add(layer)

    m.fit_bounds([[miny, minx], [maxy, maxx]])

    # floating info box on the map
    info = HTML("<i>Pasa el ratón sobre un área de salud</i>")
    info.layout.margin = "0 0 0 0"
    m.add(WidgetControl(widget=info, position="topright"))

    def describe(feature, **kwargs):
        props = feature["properties"]
        geom_desc = props.get(geom_var)
        dom_prev = props.get(domain_col)
        dom_prev = dom_prev if dom_prev is not None else "Sin datos"
        info.value = (f"<b>{geom_desc}</b>: {dom_prev}")

    layer.on_hover(describe)   

    return m
"""


