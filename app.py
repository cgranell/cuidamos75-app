import os
os.environ["POLARS_UNKNOWN_EXTENSION_TYPE_BEHAVIOR"] = "load_as_storage"

#import geopandas as gpd
#import pyarrow
import polars as pl 

from plots import (
    plotly_heatmap_dominios, 
    plotly_donut_clases,
    CONTEXT_PALETTE
)

# Load data and compute static values/constants that will be used in the app
from data import (
    ICONS, 
    BASE_THEME_VOID,
    THEME_LEGEND_BOTTOM,
    MASTER_COLORMAP_DOMINIO, MASTER_COLORMAP_CLASES, COLOR_NA, 
    municipios,
    areas_salud,
    nanda_periodos,
    participantes
)

from plotnine import (
    ggplot, geom_map, geom_text, 
    coord_fixed, aes, labs,
    scale_fill_manual)#, scale_fill_brewer)

from shiny import reactive
from shiny.express import input, ui, render
from shinywidgets import render_plotly, render_widget
from ipyleaflet import Map, GeoJSON, WidgetControl, Choropleth, basemaps
from ipywidgets import HTML

import json

from branca.colormap import linear

#param_periodo = "PRE-PANDEMIA"  # "INTRA-PANDEMIA, "POST-PANDENIA"

# Add page title and sidebar inputs
ui.page_opts(title = "Cuidamos +75", fillable = True)


with ui.sidebar():
    ui.markdown(
            """
            Prototipo de visualización de datos de prevalencia de diagnósticos NANDA en personas mayores de 75 años, basado en datos del proyecto [Cuidamos+75](https://cuidamos75.com/).
            """     
        )
    ui.input_radio_buttons(  
        id = "param_ccaa",  
        label = "Región o provincia:",  
        #choices ={"14": "Murcia", "15": "Navarra"},
        choices ={"14": "Murcia"},
        inline = False
    )  

    ui.input_select(  
        id = "param_periodo",  
        label = "Periodo:",  
        choices ={
            "PRE-PANDEMIA": "Pre-pandemia (2018-2019)", 
            "INTRA-PANDEMIA": "Intra-pandemia (2020-2021)",
            "POST-PANDEMIA": "Post-pandemia (2022-2023)"}
    )  


# Add navigation panels with content
with ui.nav_panel("Contexto"):
    with ui.layout_columns(col_widths=(6, 3, 3)):
    
        with ui.value_box(showcase=ICONS["participantes"]):
            "Participantes (periodo - CCAA)"
            @render.text
            def total_participantes():                 
                selected_periodo = input.param_periodo()

                total_por_ccaa = participantes.height
                total_por_periodo = (
                    nanda_periodos
                    .filter(
                        pl.col("PERIODO_TIPO") == selected_periodo,
                        pl.col("TIENE_PERIODO")
                    )
                    .select(pl.col("PACIENTE_ID").n_unique().alias("n"))
                    .to_dicts()[0]["n"] # pull the value
                )
                return f"{total_por_periodo:,} - {total_por_ccaa:,}"

        with ui.value_box(showcase=ICONS["municipios"]):
            "Municipios"
            @render.text
            def total_municipios():
                return municipios_data().shape[0]

        with ui.value_box(showcase=ICONS["areas-salud"]):
            "Áreas de salud"
            @render.text
            def total_areas_salud():
                return areas_salud_data().shape[0]
    
    with ui.layout_columns(fillable=True):
        with ui.card(full_screen=True):
            ui.card_header("Municipios y áreas de salud")
            
            @render.plot
            def plot_municipios_as():

                return (
                    ggplot()
                    
                    + geom_map(
                        data=areas_salud_data(),
                        mapping=aes(fill="AS_DESC"),
                        color="black",
                        alpha=0.3,
                        size=0.2,
                        show_legend=True
                    )
                    + geom_map(
                        data=municipios_data(),
                        color="#cccccc",
                        fill=None,
                        size=0.2
                    )
                    #+ scale_fill_brewer(
                    #    type="qual", palette="Paired", na_value=COLOR_NA)
                    + scale_fill_manual(CONTEXT_PALETTE, na_value=COLOR_NA)
                    + labs(fill="Áreas de salud")
                    + coord_fixed(ratio=1, expand=True)
                    + BASE_THEME_VOID
                )

################################################
#
# Dominio prevalente (Áreas de salud)
#
################################################
with ui.nav_panel("Dominio prevalente (Áreas de salud)"):

    with ui.layout_columns(col_widths=(7, 5)):

        ##### PANEL IZQUIERDO
        with ui.card(full_screen=True):
            with ui.card_header():
                "Todos los dominios por área de salud (heatmap)"
                with ui.toolbar(align="right"):
                    ui.toolbar_input_button(
                        id="info_heatmap_as",
                        label="Info",
                        icon=ICONS["info"],
                        tooltip="Color según escala log: Amarillo (baja prevalencia) → Naranja → Rojo (alta prevalencia). Números en cada celda son conteo de casos, ignorando escala log."
                    )
        
            @render_plotly
            def heatmap_as_dominio_prevalente():

                df = (
                    selected()
                    .group_by(
                        pl.col("AS_DESC"), 
                        pl.col("DOMINIO_LABEL"))
                    .agg(pl.len().alias("DOMINIO_TOTAL"))
                    .pivot(index="AS_DESC", on="DOMINIO_LABEL", values="DOMINIO_TOTAL")
                    .fill_null(0)
                    .sort("AS_DESC", descending=False)
                )

                return plotly_heatmap_dominios(df, geom_var="AS_DESC", log_scale=True)

        with ui.layout_column_wrap(width=(1 / 1)):
        #with ui.layout_columns(col_widths=12, row_heights=(2,1)):  
            ##### PANEL DERECHO SUPERIOR
            with ui.card(full_screen=True):
                ui.card_header("Dominio prevalente por área de salud")

                #@render.plot
                @render_widget
                def plot_as_dominio_prevalente():

                    # Prepara geodataframe
                    selected_gdf = (
                        areas_salud_data().merge(
                            por_as_dominio_prevalente_pl().to_pandas(), 
                            on="AS_ID", 
                            how="inner") 
                            #left para mantener todas las AS, incluso las que no tienen casos registrados (que aparecerán con DOMINIO_PREVALENTE nulo)
                    )

                    # Mapa coropleta por área de salut (with leaflet, categorical cloropeth)
                    # leaflet needs WGS84 lon/lat, but our geodata is already in that CRS (EPSG:4326), so we can use it directly
                    # We need to convert the geodataframe to GeoJSON format for use in leaflet                
                    selected_gdf_json = json.loads(selected_gdf.to_json())
                                
                    # categorical fill: replaces scale_fill_manual(values=..., na_value=...)
                    def style_callback(feature):
                        dom = feature["properties"].get("DOMINIO_PREVALENTE")
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
                    minx, miny, maxx, maxy = selected_gdf.total_bounds
                    center = ((miny + maxy) / 2, (minx + maxx) / 2)   # (lat, lon)

                    m = Map(
                        center=center,
                        zoom=8,
                        basemap=basemaps.CartoDB.Positron, 
                        scroll_wheel_zoom=True)
                    m.add(layer)

                    m.fit_bounds([[miny, minx], [maxy, maxx]])

                    # floating info box on the map
                    info = HTML("Pasa el ratón sobre un área de salud")
                    info.layout.margin = "0 0 0 0"
                    m.add(WidgetControl(widget=info, position="topright"))

                    def describe(feature, **kwargs):
                        props = feature["properties"]
                        geom_desc = props.get("AS_DESC")
                        dom_prev = props.get("DOMINIO_PREVALENTE")
                        dom_prev = dom_prev if dom_prev is not None else "Sin datos"
                        info.value = (f"<b>{geom_desc}</b>: {dom_prev}")

                    def on_click_select(feature, **kwargs):
                        props = feature["properties"]
                        geom_id = props.get("AS_ID")
                        geom_desc = props.get("AS_DESC")   
                        dom_prev = props.get("DOMINIO_PREVALENTE") 
                        selected_as_id.set(geom_id)
                        selected_as_desc.set(geom_desc)
                        selected_dominio_prev.set(dom_prev)

                    layer.on_hover(describe)
                    layer.on_click(on_click_select)  # used to link with other panels, e.g. show prevalent classes in the selected AS

                    return m


                    # Mapa coropleta por área de salud  (plotnine)
                    # return (
                    #    ggplot(selected_gdf)
                    #    + geom_map(
                    #        mapping=aes(fill="DOMINIO_PREVALENTE"),
                    #        color="gray",
                    #        size=0.3
                    #    )
                    #    + geom_text(
                    #        aes(
                    #            x="CENTER_LON",
                    #            y="CENTER_LAT",
                    #            label="AS_DESC"),
                    #        size=6)
                    #    + scale_fill_manual(
                    #        values=MASTER_COLORMAP_DOMINIO,
                    #        na_value=COLOR_NA
                    #    )
                    #    + labs(fill="Dominio Prevalente")
                    #    + coord_fixed(ratio=1, expand=True)
                    #    + BASE_THEME_VOID
                    #    + THEME_LEGEND_BOTTOM
                    #)



            ##### PANEL DERECHO INFERIOR
            with ui.card(full_screen=True):
                with ui.card_header():
                    "Clases en dominio prevalente por área de salud"
                    with ui.toolbar(align="right"):
                        ui.toolbar_input_button(
                            id="info_donut_as",
                            label="Info",
                            icon=ICONS["info"],
                            tooltip="Casos corresponde al número en la celda del área de salud y dominio en el heatmap."
                        )

                @render_widget
                def donut_clases_por_as():
                    return (
                        plotly_donut_clases(
                            por_as_seleccionada_clases_pl(), 
                            message="una área de salud", 
                            cmap=MASTER_COLORMAP_CLASES)
                        )

                with ui.card_footer():
                    @render.ui
                    def donut_footer_as():
                        selected_as = selected_as_desc.get()
                        selected_dominio = selected_dominio_prev.get()
                        if selected_as is None:
                            return ui.HTML("Sin selección.")
                        else:
                            return ui.HTML(f"<b>{selected_as}</b>: {selected_dominio}")

                

################################################
#
# Dominio prevalente (Municipios)
#
################################################

with ui.nav_panel("Dominio prevalente (Municipios)"):

    with ui.layout_columns(col_widths=(7, 5)):
        ##### PANEL IZQUIERDO
        with ui.card(full_screen=True):    
            with ui.card_header():
                "Todos los dominios por municipio (heatmap)"
                with ui.toolbar(align="right"):
                    ui.toolbar_input_button(
                        id="info_heatmap_municipio",
                        label="Info",
                        icon=ICONS["info"],
                        tooltip="Color según escala log: Amarillo (baja prevalencia) → Naranja → Rojo (alta prevalencia). Números en cada celda son conteo de casos, ignorando escala log."
                    )


            @render_plotly
            def heatmap_municipio_dominio_prevalente():
                df = (
                    selected()
                     .group_by(
                        pl.col("MUNI_DESC"), 
                        pl.col("DOMINIO_LABEL"))
                    .agg(pl.len().alias("DOMINIO_TOTAL"))
                    .pivot(index="MUNI_DESC", on="DOMINIO_LABEL", values="DOMINIO_TOTAL")
                    .fill_null(0)
                    .sort("MUNI_DESC", descending=False)
                )

                return plotly_heatmap_dominios(df, log_scale=True)

    
        with ui.layout_column_wrap(width=(1 / 1)):
        #with ui.layout_columns(col_widths=12, row_heights=(2,1)):  
            ##### PANEL DERECHO SUPERIOR
            with ui.card(full_screen=True):
                ui.card_header("Dominio prevalente por municipio")
            
                #@render.plot
                @render_widget
                def plot_municipios_dominio_prevalente():
                    # Prepara geodataframe
                    selected_gdf = (
                        municipios_data().merge(
                            por_municipio_dominio_prevalente_pl().to_pandas(), 
                            on="MUNI_CODINE", 
                            how="left") 
                            #left para mantener todos los municipios, incluso los que no tienen casos registrados (que aparecerán con DOMINIO_PREVALENTE nulo
            
                    )   

                    # Mapa coropleta por municipio (with plotnine)
                    #return (
                    #    ggplot(selected_gdf)
                    #    + geom_map(
                    #        mapping=aes(fill="DOMINIO_PREVALENTE"),
                    #        color="gray",
                    #        size=0.3
                    #    )
                    #    + scale_fill_manual(
                    #        values=MASTER_COLORMAP_DOMINIO,
                    #        na_value=COLOR_NA
                    #    )
                    #    + labs(fill="Dominio Prevalente")
                    #    + coord_fixed(ratio=1, expand=True)
                    #    + BASE_THEME_VOID
                    #    + THEME_LEGEND_BOTTOM
                    #)

                    # Mapa coropleta por municipio (with leaflet, categorical cloropeth)
                    # leaflet needs WGS84 lon/lat, but our geodata is already in that CRS (EPSG:4326), so we can use it directly
                    # We need to convert the geodataframe to GeoJSON format for use in leaflet                
                    selected_gdf_json = json.loads(selected_gdf.to_json())
                    
                    # categorical fill: replaces scale_fill_manual(values=..., na_value=...)
                    def style_callback(feature):
                        dom = feature["properties"].get("DOMINIO_PREVALENTE")
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
                        hover_style={"weight": 1.2, "color": "black"}, # hovered municipality outlines itself 
                    )

                    # centre on the data extent
                    minx, miny, maxx, maxy = selected_gdf.total_bounds
                    center = ((miny + maxy) / 2, (minx + maxx) / 2)   # (lat, lon)

                    m = Map(
                        center=center,
                        zoom=8,
                        basemap=basemaps.CartoDB.Positron, 
                        scroll_wheel_zoom=True)
                    m.add(layer)

                    m.fit_bounds([[miny, minx], [maxy, maxx]])

                    # floating info box on the map
                    info = HTML("Pasa el ratón sobre un municipio")
                    info.layout.margin = "0 0 0 0"
                    m.add(WidgetControl(widget=info, position="topright"))

                    def describe(feature, **kwargs):
                        props = feature["properties"]
                        muni_desc = props.get("MUNI_DESC")
                        dom_prev = props.get("DOMINIO_PREVALENTE")
                        dom_prev = dom_prev if dom_prev is not None else "Sin datos"
                        info.value = (f"<b>{muni_desc}</b>: {dom_prev}")

                    def on_click_select(feature, **kwargs):
                        props = feature["properties"]
                        geom_id = props.get("MUNI_CODINE")
                        geom_desc = props.get("MUNI_DESC")
                        dom_prev = props.get("DOMINIO_PREVALENTE")    
                        selected_muni_codine.set(geom_id)
                        selected_muni_desc.set(geom_desc)
                        selected_dominio_prev.set(dom_prev)

                    layer.on_hover(describe)
                    layer.on_click(on_click_select)  # used to link with other panels, e.g. show prevalent classes in the selected municipality

                    return m


            ##### PANEL DERECHO INFERIOR
            with ui.card(full_screen=True):
                with ui.card_header():
                    "Clases en dominio prevalente por municipio"
                    with ui.toolbar(align="right"):
                        ui.toolbar_input_button(
                            id="info_donut_municipio",
                            label="Info",
                            icon=ICONS["info"],
                            tooltip="Casos corresponde al número en la celda del municipio y dominio en el heatmap."
                        )

                    
                @render_widget
                def donut_clases_por_municipios():
                    return (
                        plotly_donut_clases(
                            por_municipio_seleccionado_clases_pl(), 
                            message="un municipio", 
                            cmap=MASTER_COLORMAP_CLASES)
                        )
                
                with ui.card_footer():
                    @render.ui
                    def donut_footer_muni():
                        selected_muni = selected_muni_desc.get()
                        selected_dominio = selected_dominio_prev.get()
                        if selected_muni is None:
                            return ui.HTML("Sin selección.")
                        else:
                            return ui.HTML(f"<b>{selected_muni}</b>: {selected_dominio}")

################################################
#
# Mapa de dominios (Municipios)
#
################################################

with ui.nav_panel("Mapa de dominios (Municipios)"):

    with ui.layout_columns(col_widths=(4, 8)):
        with ui.card(full_screen=True):
            ui.card_header("Selección de dominios")


            ui.input_select(  
                id = "param_dominio",  
                label = "Dominio:",  
                choices = [
                    "01. Promocion salud",
                    "02. Nutricion",
                    "03. Eliminacion intercambio",
                    "04. Actividad reposo",
                    "05. Percepcion cognicion",
                    "06. Autopercepcion",
                    "07. Rol relaciones",
                    "08. Sexualidad",
                    "09. Afrontamiento estres",
                    "10. Principios vitales",
                    "11. Seguridad proteccion",
                    "12. Confort"
                ],
                selected = "01. Promocion salud"
            )  

            ui.markdown(
            """
            *Nota metodológica*. 
            - Los municipios sin casos se tratan como 0 casos, por lo que no hay diferencia entre "no se han recopilado datos aquí" y "cero casos".
            - La escala de color se reajusta cada vez que cambia el dominio, por lo que el mismo color indica un recuento de casos diferente para distintos dominios seleccionados.
            """)
    
        with ui.card(full_screen=True):
            ui.card_header("Mapa de dominio seleccionado por municipio")
            
            #@render.data_frame
            #def tabla_dominio_seleccionado_municipio():
            #    return render.DataTable(
            #        por_municipio_dominio_seleccionado_pl().to_pandas(),
            #        filters=True
            #    )
            @render_widget
            def plot_municipios_dominio_seleccionado():

                dominio_sel = input.param_dominio()

                # Prepara geodataframe
                selected_gdf = (
                    municipios_data().merge(
                        por_municipio_dominio_seleccionado_pl().to_pandas(), 
                        on="MUNI_CODINE", 
                        how="left") 
                        #left para mantener todos los municipios, incluso los que no tienen casos registrados (que aparecerán con DOMINIO_TOTAL nulo
                )   
              
                # municipios sin casos del dominio seleccionado -> 0, no "sin datos"
                selected_gdf["DOMINIO_TOTAL"] = selected_gdf["DOMINIO_TOTAL"].fillna(0)


                # Mapa coropleta por municipio (with leaflet, numeric cloropeth)
                # leaflet needs WGS84 lon/lat, but our geodata is already in that CRS (EPSG:4326), so we can use it directly
                # We need to convert the geodataframe to GeoJSON format for use in leaflet                
                selected_gdf_json = json.loads(selected_gdf.to_json())

                # continuous colormap over 0 -> max (per-domain rescaling)
                
                vmax = float(selected_gdf["DOMINIO_TOTAL"].max())
                cmap = linear.YlOrRd_04.scale(0, vmax)
                cmap.caption = f"Casos de {dominio_sel}"
                
                # numeric fill
                def style_callback(feature):
                    val = feature["properties"].get("DOMINIO_TOTAL")
                    color = cmap(val if val is not None else 0)
                    return {
                        "fillColor": color,
                        "color": "gray",     # was color="gray"
                        "weight": 0.3,       # was size=0.3 (line width)
                        "fillOpacity": 0.60,
                    }

                layer = GeoJSON (
                    data=selected_gdf_json,
                    style_callback=style_callback,
                    hover_style={"weight": 1.2, "color": "black"}, # hovered municipality outlines itself 
                )


                #Check https://ipyleaflet.readthedocs.io/en/latest/layers/choropleth.html
                
                 
                # centre on the data extent
                minx, miny, maxx, maxy = selected_gdf.total_bounds
                center = ((miny + maxy) / 2, (minx + maxx) / 2)   # (lat, lon)

                m = Map(
                    center=center,
                    zoom=6,
                    basemap=basemaps.CartoDB.Positron, 
                    scroll_wheel_zoom=True)
                m.add(layer)

                m.fit_bounds([[miny, minx], [maxy, maxx]])

                # floating info box on the map
                info = HTML("Pasa el ratón sobre un municipio")
                info.layout.margin = "0 0 0 0"
                m.add(WidgetControl(widget=info, position="topright"))

                def describe(feature, **kwargs):
                    props = feature["properties"]
                    muni_desc = props.get("MUNI_DESC")
                    casos = props.get("DOMINIO_TOTAL")
                    casos = 0 if casos is None else casos
                    info.value = (f"<b>{muni_desc}</b>: {casos:,} casos de <i>{dominio_sel}</i>")

                layer.on_hover(describe)

                return m




################################################
#
# Shared selection state (AS_ID, AS_DESC, MUNI_CODINE, MUNI_CODINE)
#
################################################

selected_as_id = reactive.value(None)
selected_as_desc = reactive.value(None)
selected_muni_codine = reactive.value(None)
selected_muni_desc = reactive.value(None)
selected_dominio_prev = reactive.value(None)

################################################
#
# Reactive data subsets based on user input
#
################################################

@reactive.calc
def municipios_data():
    selected_ccaa = input.param_ccaa()
    return municipios.loc[municipios["CCAA_CODINE"] == selected_ccaa]


@reactive.calc
def areas_salud_data():
    selected_ccaa = input.param_ccaa()
    return areas_salud.loc[areas_salud["CCAA_CODINE"] == selected_ccaa]

def participantes_data() -> str:
    pass

@reactive.calc
def selected():
    selected_ccaa = input.param_ccaa()
    selected_periodo = input.param_periodo()

    selected_nanda = (
        nanda_periodos
        .filter(
            pl.col("CCAA_CODINE") == selected_ccaa,
            pl.col("PERIODO_TIPO") == selected_periodo,
            pl.col("TIENE_PERIODO"),
        )
    )

    selected_participantes = (
        participantes
        .filter(
            pl.col("CCAA_CODINE") == selected_ccaa
        )
    )

    return (
        selected_nanda.join(
            selected_participantes,
            on="PACIENTE_ID", 
            how="left")
    )


@reactive.calc
def nanda_periodos_data():
    selected_ccaa = input.param_ccaa()
    selected_periodo = input.param_periodo()

    return (
        nanda_periodos
        .filter(
            pl.col("CCAA_CODINE") == selected_ccaa,
            pl.col("PERIODO_TIPO") == selected_periodo,
            pl.col("TIENE_PERIODO"),
        )
        .sample(30)
    )

@reactive.calc
def por_as_dominio_prevalente_pl(): 
    return (
        selected()
        .group_by(
            pl.col("AS_ID"), 
            pl.col("DOMINIO_LABEL"))
        .agg(
            pl.len().alias("DOMINIO_TOTAL"))
        .sort(pl.col("DOMINIO_TOTAL"), descending=True)
        .group_by(pl.col("AS_ID"))
        .agg(pl.first("DOMINIO_LABEL").alias("DOMINIO_PREVALENTE"))
        .sort("AS_ID", descending=False)
    )   


@reactive.calc
def por_municipio_dominio_prevalente_pl(): 
    return (
        selected()
        .group_by(
            pl.col("MUNI_CODINE"), 
            pl.col("DOMINIO_LABEL"))
        .agg(
            pl.len().alias("DOMINIO_TOTAL"))
        .sort(pl.col("DOMINIO_TOTAL"), descending=True)
        .group_by(pl.col("MUNI_CODINE"))
        .agg(pl.first("DOMINIO_LABEL").alias("DOMINIO_PREVALENTE"))
        .sort("MUNI_CODINE", descending=False)
    )   



@reactive.calc
def por_municipio_dominio_seleccionado_pl(): 
    selected_dominio = input.param_dominio()

    return (
        selected()
        .filter(pl.col("DOMINIO_LABEL") == selected_dominio)
        .group_by(
            pl.col("MUNI_CODINE")
        )
        .agg(
            pl.len().alias("DOMINIO_TOTAL"))
        .sort(pl.col("DOMINIO_TOTAL"), descending=True)
    )   


@reactive.calc
def por_as_seleccionada_clases_pl():
    selected_as = selected_as_id.get()

    if selected_as is None:
        return None
    return (
        por_as_clase_prevalentes_pl()
        .filter(pl.col("AS_ID") == selected_as)
        .select(pl.col("CLASE"), pl.col("CLASE_TOTAL"))
        .sort(pl.col("CLASE_TOTAL"), descending=True)
    )



def por_as_clase_prevalentes_pl():
    clases_pl = (
        selected()
        .select(
            pl.col("DOMINIO_LABEL").alias("DOMINIO_PREVALENTE"),
            pl.col("CLASE"),
            pl.col("AS_ID"),
            pl.col("AS_DESC")
        )
    )
    
    return (
        por_as_dominio_prevalente_pl()
        .join(
            clases_pl,             
            on=["AS_ID", "DOMINIO_PREVALENTE"],
            how="inner")
        .group_by(
            pl.col("AS_ID"), 
            pl.col("AS_DESC"), 
            pl.col("DOMINIO_PREVALENTE"),
            pl.col("CLASE"))
        .agg(
            pl.len().alias("CLASE_TOTAL"))
        .sort("AS_ID", "DOMINIO_PREVALENTE", "CLASE_TOTAL", descending=[False, False, True])

    )



@reactive.calc
def por_municipio_seleccionado_clases_pl():
    selected_muni = selected_muni_codine.get()

    if selected_muni is None:
        return None
    return (
        por_municipio_clase_prevalentes_pl()
        .filter(pl.col("MUNI_CODINE") == selected_muni)
        .select(pl.col("CLASE"), pl.col("CLASE_TOTAL"))
        .sort(pl.col("CLASE_TOTAL"), descending=True)
    )


def por_municipio_clase_prevalentes_pl():
    clases_pl = (
        selected()
        .select(
            pl.col("DOMINIO_LABEL").alias("DOMINIO_PREVALENTE"),
            pl.col("CLASE"),
            pl.col("MUNI_CODINE"),
            pl.col("MUNI_DESC")
        )
    )
    
    return (
        por_municipio_dominio_prevalente_pl()
        .join(
            clases_pl,             
            on=["MUNI_CODINE", "DOMINIO_PREVALENTE"],
            how="inner")
        .group_by(
            pl.col("MUNI_CODINE"), 
            pl.col("MUNI_DESC"), 
            pl.col("DOMINIO_PREVALENTE"),
            pl.col("CLASE"))
        .agg(
            pl.len().alias("CLASE_TOTAL"))
        .sort("MUNI_CODINE", "DOMINIO_PREVALENTE", "CLASE_TOTAL", descending=[False, False, True])

    )