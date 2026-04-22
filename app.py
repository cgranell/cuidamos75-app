import os
os.environ["POLARS_UNKNOWN_EXTENSION_TYPE_BEHAVIOR"] = "load_as_storage"

#import geopandas as gpd
#import pyarrow
#import polars as pl 

# Load data and compute static values/constants that will be used in the app
from data import (
    ICONS, 
    BASE_THEME_VOID,
    municipios,
    areas_salud
    )

from plotnine import (
    ggplot, geom_map, coord_fixed)

from shiny.express import input, ui, render, reactive


#param_periodo = "PRE-PANDEMIA"  # "INTRA-PANDEMIA, "POST-PANDENIA"

# Add page title and sidebar inputs
ui.page_opts(title = "Cuidamos +75", fillable = True)


with ui.sidebar():
    ui.input_radio_buttons(  
        id = "param_ccaa",  
        label = "Comunidad Autónoma",  
        choices ={"14": "Murcia", "15": "Navarra"},
        #choices ={"14": "Murcia"},
        inline = False
    )  

    ui.input_select(  
        id = "param_periodo",  
        label = "Periodo",  
        choices ={
            "PRE-PANDEMIA": "Pre-pandemia (2018-2019)", 
            "INTRA-PANDEMIA": "Intra-pandemia (2020-2021)",
            "POST-PANDEMIA": "Post-pandemia (2022-2023)"}
    )  


# Add navigation panels with content
with ui.nav_panel("Contexto"):
    with ui.layout_columns(col_widths=(4, 4, 4)):
    
        with ui.value_box(showcase=ICONS["participantes"]):
            "Participantes"
            "100,000"

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
    
    with ui.layout_columns(col_widths=(8, 4)):
        with ui.card(full_screen=True):
            ui.card_header("Municipios")
            @render.plot
            def plot_municipios():
                filtered = municipios_data()

                return (
                    ggplot(filtered)
                    + geom_map(
                        color="grey",
                        fill="white",
                        size=0.3
                    )
                    + coord_fixed(ratio=1, expand=True)
                    + BASE_THEME_VOID
                )
                
        with ui.card(full_screen=True):
            ui.card_header("Áreas de salud")
            @render.plot
            def plot_as():
                filtered = areas_salud_data()

                return (
                    ggplot(filtered)
                    + geom_map(
                        color="grey",
                        fill="white",
                        size=0.3
                    )
                    + coord_fixed(ratio=1, expand=True)
                    + BASE_THEME_VOID
                )

with ui.nav_panel("Dominio prevalente por áreas de salud"):
    with ui.card():
        ui.markdown("Another card with some _markdown_.")

with ui.nav_panel("Dominio prevalente por municipio"):
    "Page 3 content"


with ui.nav_panel("Notas"):
    "Page 4 content"


# Reactive data subsets based on user input

@reactive.calc
def municipios_data():
    selected_ccaa = input.param_ccaa()
    return municipios.loc[municipios["CCAA_CODINE"] == selected_ccaa]


@reactive.calc
def areas_salud_data():
    selected_ccaa = input.param_ccaa()
    return areas_salud.loc[areas_salud["CCAA_CODINE"] == selected_ccaa]

