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
    nanda_periodos,
    participantes
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
    ui.markdown(
            """
            Prototipo de visualización de datos de prevalencia de diagnósticos NANDA en personas mayores de 75 años, basado en datos del proyecto [Cuidamos+75](https://cuidamos75.com/).
            """     
        )
    ui.input_radio_buttons(  
        id = "param_ccaa",  
        label = "Selecciona CCAA:",  
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

                @render.plot
                def plot_as_dominio_prevalente():

                    # Prepara geodataframe
                    selected_gdf = (
                        areas_salud_data().merge(
                            por_as_dominio_prevalente(), 
                            on="AS_ID", 
                            how="inner") 
                            #left para mantener todas las AS, incluso las que no tienen casos registrados (que aparecerán con DOMINIO_PREVALENTE nulo)
                    )   
                    # Mapa coropleta por área de salud
                    
                    return (
                        ggplot(selected_gdf)
                        + geom_map(
                            mapping=aes(fill="DOMINIO_PREVALENTE"),
                            color="gray",
                            size=0.3,
                            show_legend=False #TODO: Si se muestra la leyenda, el mapa se vuelve ilegible por la cantidad de categorías de dominio prevalente (hasta 8 dominios diferentes)
                        )
                        + scale_fill_brewer(
                            type="qual", palette=3)
                        + labs(fill="Dominio Prevalente")
                        + coord_fixed(ratio=1, expand=True)
                        + BASE_THEME_VOID
                    )

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
        #return nanda_periodos_data()
        return selected()

# Reactive data subsets based on user input

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
            # TODO: Añadir CCAA_CODINE a nanda_periodos para poder filtrar por CCAA
            #pl.col("CCAA_CODINE") == selected_ccaa,
            pl.col("PERIODO_TIPO") == selected_periodo,
            pl.col("TIENE_PERIODO"),
        )
        .with_columns(
            pl.col("PACIENTE_ID").cast(pl.String)
        )
    )

    selected_participantes = (
        participantes
        .filter(
            pl.col("CCAA_CODINE") == selected_ccaa
        )
        .select(["PACIENTE_ID", "PACIENTE_CP", "AS_ID", "AS_DESC"])
        .with_columns(
            pl.col("PACIENTE_ID").cast(pl.String),
            pl.col("AS_ID").cast(pl.Int64)
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
    #selected_ccaa = input.param_ccaa()
    selected_periodo = input.param_periodo()

    return (
        nanda_periodos
        .filter(
            #pl.col("CCAA_CODINE") == selected_ccaa,
            pl.col("PERIODO_TIPO") == selected_periodo,
            pl.col("TIENE_PERIODO"),
        )
        .sample(30)
    )

@reactive.calc
def por_as_dominio_prevalente(): 
    #selected_ccaa = input.param_ccaa()
    #selected_periodo = input.param_periodo()

    return (
        selected()
        .group_by(
            pl.col("AS_ID"), 
            pl.col("DOMINIO"))
        .agg(
            pl.len().alias("DOMINIO_TOTAL"))
        .sort(pl.col("DOMINIO_TOTAL"), descending=True)
        .group_by(pl.col("AS_ID"))
        .agg(pl.first("DOMINIO").alias("DOMINIO_PREVALENTE"))
        .sort("AS_ID", descending=False)
        .to_pandas()
    )   

def por_municipio_dominio_prevalente(): 
    #selected_ccaa = input.param_ccaa()
    selected_periodo = input.param_periodo()

    return (
        nanda_periodos
        .filter(
            #pl.col("CCAA_CODINE") == selected_ccaa,
            pl.col("PERIODO_TIPO") == selected_periodo,
            pl.col("TIENE_PERIODO")
        )
        .group_by(
            pl.col("MUNI_CODINE"), 
            pl.col("DOMINIO"))
        .agg(
            pl.len().alias("DOMINIO_TOTAL"))
        .sort(pl.col("DOMINIO_TOTAL"), descending=True)
        .group_by(pl.col("MUNI_CODINE"))
        .agg(pl.first("DOMINIO").alias("DOMINIO_PREVALENTE"))
        .sort("MUNI_CODINE", descending=False)
    )   




def por_as_dominio():
    return (
        selected()
        .group_by(
            pl.col("AS_DESC"), 
            pl.col("DOMINIO"))
        .agg(pl.len().alias("DOMINIO_TOTAL"))
        .pivot(index="AS_DESC", on="DOMINIO", values="DOMINIO_TOTAL")
        .fill_null(0)
        .sort("AS_DESC", descending=False)
)