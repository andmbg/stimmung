import sys
import logging
from pathlib import Path

import numpy as np
import pandas as pd
import dash_bootstrap_components as dbc
from dash import Dash, dcc, html, Input, Output

# import from config relatively, so it remains portable:
dashapp_rootdir = Path(__file__).resolve().parents[1]
sys.path.append(str(dashapp_rootdir))

from .src.data.ensure_data import (
    ensure_data_bundestag,
    get_legislatures,
)
from .src.log_config import setup_logger
from .config import cached_dataset
from .src.i18n import translate as t, translate_series
from .src.language_context import language_context
from .src.viz.visualize import get_fig_dissenters, get_fig_votes


setup_logger()
logger = logging.getLogger(__name__)


def init_dashboard(flask_app, route):

    current_language = config.current_language
    language_context.set_language(current_language)

    # we run >1 instances of the same app, which leads to conflict inside Dash
    # due to bluepriint names; set app name explicitly:
    app_name = f"bundestag_{current_language}"

    app = Dash(
        name=app_name,
        server=flask_app,
        routes_pathname_prefix=route,
        assets_folder=dashapp_rootdir / "bundestag" / "assets",
        # relevant for standalone launch, not used by main flask app:
        external_stylesheets=[dbc.themes.FLATLY],
    )
    #
    # Initialization
    #

    # legislature selection data:
    # dict: {id: label}
    legislature_labels = get_legislatures().data
    legislature_labels = (
        legislature_labels.loc[
            legislature_labels.label.str.contains("Bundestag"), ["id", "label"]
        ]
        .set_index("id")
        .to_dict()["label"]
    )

    # the dataset:
    ensure_data_bundestag()

    data = pd.read_parquet(cached_dataset)
    data.label = translate_series(data.label)

    data = data.loc[data.vote.ne("no_show")]
    data.vote = pd.Categorical(
        data.vote, ordered=True, categories=["yes", "no", "abstain"]
    )

    logger.info(f"votes: {type(data)} {data.shape}")

    # prose paragraphs:
    prosepath = dashapp_rootdir / "bundestag" / "src" / "prose"
    md_intro = dcc.Markdown(t(open(prosepath / "intro.md").read()))
    md_dropdown_pre = dcc.Markdown(t(open(prosepath / "dropdown_pre.md").read()))
    md_dropdown_post = dcc.Markdown(t(open(prosepath / "dropdown_post.md").read()))
    md_pre_dissenter = dcc.Markdown(t(open(prosepath / "pre_dissenter.md").read()))

    app.layout = html.Div(
        [
            html.Div(className="background-fixed"),
            html.Div(
                className="container",
                children=[
                    dbc.Container(
                        style={"paddingTop": "50px"},
                        children=[
                            dbc.Row(
                                [
                                    dbc.Col(
                                        [md_intro],
                                        xs={"size": 12},
                                        lg={"size": 8, "offset": 2},
                                        class_name="para mt-4",
                                    ),
                                ]
                            ),
                            dbc.Row(
                                [
                                    dbc.Col(
                                        [
                                            html.Figure(
                                                [
                                                    html.Img(
                                                        src="assets/Bundestag_-_Palais_du_Reichstag_small.jpg",
                                                        width="100%",
                                                    ),
                                                    html.Figcaption(
                                                        "CC BY-SA 3.0, A. Delesse (Prométhée)"
                                                    ),
                                                ]
                                            ),
                                        ],
                                        xs={"size": 12},
                                        lg={"size": 8, "offset": 2},
                                        class_name="figure mt-4",
                                    )
                                ]
                            ),
                            dbc.Row(
                                [
                                    dbc.Col(
                                        [md_dropdown_pre],
                                        xs={"size": 12},
                                        lg={"size": 8, "offset": 2},
                                        class_name="para mt-4",
                                    )
                                ]
                            ),
                            # Legislature and fraction selection:
                            dbc.Row(
                                [
                                    dbc.Col(
                                        [
                                            dcc.Dropdown(
                                                id="legislature-dropdown",
                                                options=[
                                                    {"label": v, "value": k}
                                                    for k, v in legislature_labels.items()
                                                ],
                                                value=132,  # Bundestag 2021 - 2025
                                                clearable=False,
                                                style={"z-index": "1050"},
                                            )
                                        ],
                                        xs={"size": 6},
                                        lg={"size": 4, "offset": 2},
                                    ),
                                    dbc.Col(
                                        [
                                            dcc.Dropdown(
                                                id="fraction-dropdown",
                                                options=[
                                                    {"label": f, "value": f}
                                                    for f in data.fraction.unique()
                                                ],
                                                value="SPD",
                                                clearable=False,
                                                style={"z-index": "1050"},
                                            )
                                        ],
                                        xs={"size": 6},
                                        lg={"size": 4, "offset": 0},
                                    ),
                                ],
                                class_name="mt-4",
                            ),
                            dbc.Row(
                                [
                                    dbc.Col(
                                        [md_dropdown_post],
                                        xs={"size": 12},
                                        lg={"size": 8, "offset": 2},
                                        class_name="para mt-4",
                                    )
                                ]
                            ),
                            # fraction plot:
                            dbc.Row(
                                [
                                    dbc.Col(
                                        [
                                            dcc.Graph(
                                                id="fig-fraction",
                                                # figure=get_fig_votes(data.loc[data.fraction.eq("SPD")], [445997])
                                            )
                                        ],
                                        xs={"size": 12},
                                        lg={"size": 10, "offset": 1},
                                        class_name="figure mt-4",
                                    ),
                                ]
                            ),
                            # dissenter plot:
                            dbc.Row(
                                [
                                    dbc.Col(
                                        [md_pre_dissenter],
                                        xs={"size": 12},
                                        lg={"size": 8, "offset": 2},
                                        class_name="para mt-4",
                                    )
                                ]
                            ),
                            dbc.Row(
                                [
                                    dbc.Col(
                                        [dcc.Graph(id="fig-dissgrid")],
                                        xs={"size": 12},
                                        lg={"size": 10, "offset": 1},
                                        class_name="figure mt-4",
                                    ),
                                ]
                            ),
                            dbc.Row(
                                [
                                    dbc.Col(
                                        [
                                            html.Div(
                                                [
                                                    html.A(
                                                        children="Copyright der Daten: CC0 1.0",
                                                        href="https://creativecommons.org/publicdomain/zero/1.0/",
                                                    )
                                                ]
                                            )
                                        ],
                                        xs={"size": 12},
                                        lg={"size": 8, "offset": 2},
                                        style={
                                            "margin-top": "150px",
                                            "text-align": "center",
                                        },
                                    ),
                                ]
                            ),
                            # inspect click data:
                            # dbc.Row([
                            #     dbc.Col([html.Pre(id="display")],
                            #         xs={"size": 12},
                            #         lg={"size": 8, "offset": 2}),
                            # ])
                        ],
                    )
                ],
            ),
        ],
    )

    init_callbacks(app, data, current_language)

    return app


def init_callbacks(app, data, language):

    # update plots from selection
    @app.callback(
        Output("fig-fraction", "figure"),
        Output("fig-dissgrid", "figure"),
        Input("legislature-dropdown", "value"),
        Input("fraction-dropdown", "value"),
        Input("fig-fraction", "selectedData"),
        Input("fig-dissgrid", "selectedData"),
    )
    def update_everything(legislature, fraction, selection_frac, selection_grid, language=language):
        plot_data = data.loc[
            data.fid_legislatur.eq(legislature) & data.fraction.eq(fraction)
        ]

        language_context.set_language(language)

        selected_votes = data.vote_id.tolist()

        for selected_data in [selection_frac, selection_grid]:
            if selected_data and selected_data["points"]:
                selected_votes = list(
                    np.intersect1d(
                        selected_votes,
                        [p["customdata"][4] for p in selected_data["points"]],
                    )
                )
        frac_fig = get_fig_votes(plot_data, selected_votes)
        diss_fig = get_fig_dissenters(plot_data, selected_votes)

        return (
            frac_fig,
            diss_fig,
        )

    @app.callback(
        Output("fraction-dropdown", "options"), Input("legislature-dropdown", "value")
    )
    def update_available_parties(legislature):
        parties = data.loc[data.fid_legislatur.eq(legislature), "fraction"].unique()
        return [{"label": p, "value": p} for p in parties]

    @app.callback(
        Output("fraction-dropdown", "value"), Input("fraction-dropdown", "options")
    )
    def update_selected_party(available_options):
        return available_options[0]["value"]
