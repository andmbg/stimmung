import sys
from pathlib import Path
import logging

from flask import Flask
import pandas as pd
from dash import Dash, dcc, html, Input, Output, State, callback, dash_table
import dash_bootstrap_components as dbc

# import from config relatively, so it remains portable:
dashapp_rootdir = Path(__file__).resolve().parents[1]
sys.path.append(str(dashapp_rootdir))

from .src.data.models import Dataset
from .src.data.ensure_data import get_legislatures, get_polls, get_votes
from .src.log_config import setup_logger
from .src.viz.visualize import get_fig_dissenters, get_fig_votes


setup_logger()
logger = logging.getLogger(__name__)


def init_dashboard(flask_app, route):

    app = Dash(
        __name__,
        server=flask_app,
        routes_pathname_prefix=route,
        # relevant for standalone launch, not used by main flask app:
        external_stylesheets=[dbc.themes.FLATLY],
    )

    df_fractions = get_votes()
    logger.info(f"votes: {type(df_fractions)} {df_fractions.shape}")

    #
    # Fraction selection:
    # we always just show one fraction, selected via a Dropdown menu:
    #

    app.layout = html.Div([
        dbc.Container(
            style={"paddingTop": "50px"},
            children=[
                dcc.Store(id="keystore", data=[]),
                dbc.Row([
                    dbc.Col([
                        dcc.Dropdown(
                            id="fraction-dropdown",
                            options=[
                                {"label": f, "value": f}
                                for f in df_fractions.fraction.unique()
                            ],
                            value=df_fractions.fraction.unique()[0],
                            clearable=False,
                        )],
                        xs={"size": 12},
                        lg={"size": 8, "offset": 2}
                    )
                ]),
                dbc.Row([
                        dbc.Col([dcc.Graph(id="fig-fraction")],
                            xs={"size": 12},
                            lg={"size": 8, "offset": 2},
                        ),
                ]),
                dbc.Row([
                        dbc.Col([dcc.Graph(id="fig-dissgrid")],
                            xs={"size": 12},
                            lg={"size": 8, "offset": 2},
                        ),
                ]),
            ]
        )
    ])

    # init_callbacks(app)
    # def init_callbacks(app):
    #     global df_fractions
        
    @callback(
        Output("fig-fraction", "figure"),
        Output("fig-dissgrid", "figure"),
        Input("fraction-dropdown", "value")
    )
    def update_fraction_plot(fraction):
        df_plot = df_fractions.loc[df_fractions.fraction.eq(fraction)]
        fig_fraction = get_fig_votes(df_plot)
        fig_dissgrid = get_fig_dissenters(df_plot)

        return fig_fraction, fig_dissgrid

    return app  # .server



