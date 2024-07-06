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
from .src.viz.visualize import get_fig_votes


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

    legislatures = get_legislatures()
    logger.info("legislatures: " + legislatures.__repr__())

    polls = get_polls()
    logger.info("polls: " + polls.__repr__())

    votes = get_votes()
    logger.info(f"votes: {type(votes)} {votes.shape}")

    # we always just show one fraction; at the outset, let
    fr = "AfD"
    df_plot = df.loc[df.fraction.eq(fr)]

    fig_polls = get_fig_votes()

    app.layout = html.Div(
        [
            dbc.Container(
                style={"paddingTop": "50px"},
                children=[
                    dcc.Store(id="keystore", data=[]),
                    # Intro
                    dbc.Row(
                        [
                            dbc.Col([

                            ],
                                xs={"size": 12},
                                lg={"size": 8, "offset": 2},
                            ),
                        ],
                        class_name="para",
                    ),
                ],
            )
        ]
    )

    init_callbacks(app)

    return app  # .server


def init_callbacks(app):
    pass
