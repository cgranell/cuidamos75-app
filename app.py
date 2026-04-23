import os
os.environ["POLARS_UNKNOWN_EXTENSION_TYPE_BEHAVIOR"] = "load_as_storage"

#import geopandas as gpd
#import pyarrow
import polars as pl 

# Load data and compute static values/constants that will be used in the app
from data import (
    ICONS, 
    BASE_THEME_VOID,
    municipios,
    areas_salud,
    nanda_periodos
    )

from plotnine import (
    ggplot, geom_map, coord_fixed, aes, labs,
    scale_fill_brewer)

from shiny import reactive
from shiny.express import input, ui, render


#param_periodo = "PRE-PANDEMIA"  # "INTRA-PANDEMIA, "POST-PANDENIA"

# Add page title and sidebar inputs
ui.page_opts(title = "Cuidamos +75", fillable = True)


with ui.sidebar():
    ui.input_radio_buttons(  
        id = "param_ccaa",  
        label = "Seleccionad CCAA:",  
        choices ={"14": "Murcia", "15": "Navarra"},
        #choices ={"14": "Murcia"},
        inline = False
    )  

    ui.input_select(  
        id = "param_periodo",  
        label = "Selecciona periodo:",  
        choices ={
            "PRE-PANDEMIA": "Pre-pandemia (2018-2019)", 
            "INTRA-PANDEMIA": "Intra-pandemia (2020-2021)",
            "POST-PANDEMIA": "Post-pandemia (2022-2023)"}
    )  


# Add navigation panels with content
with ui.nav_panel("Contexto"):
    with ui.layout_columns(col_widths=(6, 3, 3)):
    
        with ui.value_box(showcase=ICONS["participantes"]):
            "Participantes (total / periodo)"
            "25.000 / 100,000"

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
                        data=municipios_data(),
                        color="#cccccc",
                        fill="white",
                        size=0.5
                    )
                    + geom_map(
                        data=areas_salud_data(),
                        mapping=aes(fill="AS_DESC"),
                        color="black",
                        alpha=0.3,
                        size=0.2,
                        show_legend=True
                    )
                    + scale_fill_brewer(
                        type="qual", palette=3)
                    + labs(fill="Áreas de salud")
                    + coord_fixed(ratio=1, expand=True)
                    + BASE_THEME_VOID
                )

with ui.nav_panel("Prevalencia dominios (Áreas de salud)"):

    with ui.layout_columns(col_widths=(7, 5)):
        with ui.card(full_screen=True):
            ui.card_header("Heatmap dominios por AS")

        with ui.layout_column_wrap(col_widths=(1 / 2)):
            with ui.card(full_screen=True):
                ui.card_header("Mapa dominio prevalente")

            with ui.card(full_screen=True):
                ui.card_header("Tabla de clases por dominio prevalente")


with ui.nav_panel("Prevalencia dominios (Municipios)"):
    "Page 3 content"
    

    with ui.layout_columns(col_widths=(7, 5)):
        with ui.card(full_screen=True):
            ui.card_header("Heatmap dominios por municipio")

        with ui.layout_column_wrap(col_widths=(1 / 2)):
            with ui.card(full_screen=True):
                ui.card_header("Mapa dominio prevalente")

            with ui.card(full_screen=True):
                ui.card_header("Tabla de clases por dominio prevalente")


with ui.nav_panel("Datos"):
    @render.data_frame
    def tabla_nanda():
        return nanda_periodos_data()

with ui.nav_panel("Notas"):
    with ui.card(full_screen=True):
        ui.card_header("Notas sobre la aplicación")
        ui.markdown(
            """
            - Esta aplicación es un prototipo de visualización de datos de prevalencia de diagnósticos NANDA en personas mayores de 75 años, basado en datos reales pero con fines exclusivamente ilustrativos.
            - Los datos han sido anonimizados y agregados para proteger la privacidad de los pacientes y cumplir con las normativas de protección de datos.
            - La aplicación se ha desarrollado con fines educativos y de demostración, y no debe ser utilizada para tomar decisiones clínicas o administrativas.
            """
        )


# Reactive data subsets based on user input

@reactive.calc
def municipios_data():
    selected_ccaa = input.param_ccaa()
    return municipios.loc[municipios["CCAA_CODINE"] == selected_ccaa]


@reactive.calc
def areas_salud_data():
    selected_ccaa = input.param_ccaa()
    return areas_salud.loc[areas_salud["CCAA_CODINE"] == selected_ccaa]


@reactive.calc
def nanda_periodos_data():
    selected_periodo = input.param_periodo()
    return (
        nanda_periodos
        .filter(
            pl.col("PERIODO_TIPO") == selected_periodo,
            pl.col("TIENE_PERIODO"),
        )
        .sample(30)
    )