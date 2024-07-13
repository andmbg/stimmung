import sys
from pathlib import Path
import logging
import json

from flask import Flask
import numpy as np
import pandas as pd
from dash import Dash, dcc, html, Input, Output, State, callback, dash_table, no_update
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
    df_fractions = df_fractions.loc[df_fractions.vote.ne("no_show")]
    df_fractions.vote = pd.Categorical(
        df_fractions.vote, ordered=True, categories=["yes", "no", "abstain"]
    )

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
                        dbc.Col([
                            dcc.Graph(
                                id="fig-fraction",
                                figure=get_fig_votes(df_fractions.loc[df_fractions.fraction.eq("AfD")], [445997])
                            )],
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
                dcc.Store(id="idstore", storage_type="memory"),
                dcc.Store(id='selected-tool-storage', storage_type='memory'),
                dbc.Row([
                    dbc.Col([html.Pre(id="display")],
                        xs={"size": 12},
                        lg={"size": 8, "offset": 2}),
                ])
            ]
        )
    ])

    # update plots from selection
    @callback(Output("fig-fraction", "figure"),
              Output("fig-dissgrid", "figure"),
              Output("display", "children"),
              Input("fraction-dropdown", "value"),
              Input("fig-fraction", "selectedData"),
              State("fig-fraction", "figure"),
              State("fig-fraction", "selectedData"),
              Input("fig-dissgrid", "selectedData"))
    def update_everything(fraction, selection_frac, current_frac_fig, current_frac_data, selection_grid):

        selected_votes = df_fractions.vote_id.tolist()

        for selected_data in [selection_frac, selection_grid]:
            if selected_data and selected_data["points"]:
                selected_votes = list(np.intersect1d(
                    selected_votes, [p["customdata"][4] for p in selected_data["points"]]
                ))
        frac_fig = get_fig_votes(df_fractions.loc[df_fractions.fraction.eq(fraction)], selected_votes)
        diss_fig = get_fig_dissenters(df_fractions[df_fractions.fraction.eq(fraction)], selected_votes)

        return (
            frac_fig,
            diss_fig,
            str(selected_votes)
        )

    return app  # .server



