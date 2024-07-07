import sys
from pathlib import Path
import logging
import json

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

    # the dataset:
    df_fractions = get_votes()
    logger.info(f"votes: {type(df_fractions)} {df_fractions.shape}")

    # prose paragraphs:
    prosepath = dashapp_rootdir / "bundestag" / "src" / "prose"
    md_intro =         dcc.Markdown(open(prosepath / "intro.md"        ).read())
    md_dropdown_pre =  dcc.Markdown(open(prosepath / "dropdown_pre.md" ).read())
    md_dropdown_post = dcc.Markdown(open(prosepath / "dropdown_post.md").read())
    md_pre_dissenter = dcc.Markdown(open(prosepath / "pre_dissenter.md").read())


    app.layout = html.Div([
        dbc.Container(
            style={"paddingTop": "50px"},
            children=[
                dcc.Store(id="keystore", data=[]),

                dbc.Row([
                    dbc.Col([
                        md_intro
                    ],
                        xs={"size": 12},
                        lg={"size": 8, "offset": 2},
                    ),
                ]),

                # Fraction selection:
                # show one fraction, selected via a Dropdown menu:
                dbc.Row([
                    dbc.Col([md_dropdown_pre],
                        xs={"size": 12},
                        lg={"size": 8, "offset": 2}),
                ]),
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
                        lg={"size": 2, "offset": 2}
                    )
                ]),
                dbc.Row([
                    dbc.Col([md_dropdown_post],
                        xs={"size": 12},
                        lg={"size": 8, "offset": 2}),
                ]),

                # fraction plot:
                dbc.Row([
                        dbc.Col([dcc.Graph(id="fig-fraction")],
                            xs={"size": 12},
                            lg={"size": 8, "offset": 2},
                            style={"border-top": "3px solid #cccccc",
                                   "border-bottom": "3px solid #cccccc",
                                   "margin-top": "50px"},
                        ),
                ]),
                
                # dissenter plot:
                dbc.Row([
                    dbc.Col([md_pre_dissenter],
                        xs={"size": 12},
                        lg={"size": 8, "offset": 2},
                        style={"margin-top": "50px"}),
                ]),
                dbc.Row([
                    dbc.Col([dcc.Graph(id="fig-dissgrid")],
                        xs={"size": 12},
                        lg={"size": 8, "offset": 2},
                        style={"border-top": "3px solid #cccccc",
                            "border-bottom": "3px solid #cccccc",
                            "margin-top": "50px"}),
                ]),

                # click data:
                dbc.Row([
                    dbc.Col([html.Pre(id="selection")],
                        xs={"size": 12},
                        lg={"size": 8, "offset": 2}),
                ])
            ]
        )
    ])

    # init_callbacks(app)
    # def init_callbacks(app):
    #     global df_fractions
        
    @callback(
        Output("fig-fraction", "figure"),
        Output("fig-dissgrid", "figure"),
        Input("fraction-dropdown", "value"),
        Input("fig-dissgrid", "clickData"),
        State("fraction-dropdown", "value"),
        State("fig-dissgrid", "clickData"),
    )
    def update_fraction_plot(
        input_fraction,
        input_focus,
        state_fraction,
        state_focus
    ):
        fraction = input_fraction if input_fraction is not None else state_fraction
        focus_json = input_focus if input_focus is not None else state_focus
        focus = focus_json["points"][0]["customdata"][0] if focus_json is not None else None

        df_plot = df_fractions.loc[df_fractions.fraction.eq(fraction)]
        fig_fraction = get_fig_votes(df_plot, focus)
        fig_dissgrid = get_fig_dissenters(df_plot, focus)

        return fig_fraction, fig_dissgrid
    
    @callback(
        Output("selection", "children"),
        Input("fig-fraction", "selectedData"),
    )
    def update_selection(
        selection_json
    ):
        if selection_json is None:
            return None
        else:
            vote_ids = [point["customdata"][4] for point in selection_json["points"]]

        return f"{[i for i in vote_ids]}"
    
    return app  # .server



