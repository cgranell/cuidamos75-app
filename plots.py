import plotly.express as px
import polars as pl
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


