import polars as pl 
from polars import selectors as cs
import plotly.express as px
  

COLOR_PALETTE = px.colors.qualitative.D3


def get_domain_colormap(df: pl.DataFrame, domain_col: str = "DOMINIO") -> dict:
    """
    Returns a consistent color mapping for all distinct domains.
    Colors are assigned alphabetically to ensure consistency across plots.
    """
    domains = sorted(df[domain_col].drop_nulls().unique().to_list())
    return {
        domain: COLOR_PALETTE[i % len(COLOR_PALETTE)]
        for i, domain in enumerate(domains)
    }



def plotly_heatmap_dominios(
    df: pl.DataFrame,
    geom_var: str = "MUNI_DESC",
    cmap: str = "YlOrRd",
    log_scale: bool = True):

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
        xaxis=dict(tickangle=45, tickfont_size=8, side="bottom"),
        yaxis=dict(tickfont_size=8, autorange="reversed"),  # top-to-bottom row order
        coloraxis_colorbar=dict(title_side="right")
        #margin=dict(l=120, r=40, t=40, b=120),
    )

    return fig