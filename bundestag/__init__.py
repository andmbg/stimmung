import sys
from pathlib import Path
import logging
import json

from flask import Flask
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

    # init_callbacks(app)
    # def init_callbacks(app):
    #     global df_fractions

    # Callback to update storage with the selected UI tool
    @callback(Output('selected-tool-storage', 'data'),
              Input('fig-fraction', 'relayoutData'))
    def update_fraction_tool(relayoutData):
        if relayoutData is None:
            return None

        # Check for UI tool changes
        if "dragmode" in relayoutData:
            selected_tool = relayoutData["dragmode"]
            return {"selected_tool": selected_tool}
        
        return no_update

    # update plots from storage:
    @callback(
        Output("fig-fraction", "figure"),
        Output("fig-dissgrid", "figure"),
        #
        Input("fraction-dropdown", "value"),
        State("fraction-dropdown", "value"),
        Input("idstore", "data"),
        #
        State("selected-tool-storage", "data"),
    )
    def update_fraction_plot(input_fraction, state_fraction, input_storage, tool):

        fraction = input_fraction if input_fraction is not None else state_fraction
        tool = tool["selected_tool"] if tool is not None else "select"

        df_plot = df_fractions.loc[df_fractions.fraction.eq(fraction)]

        fig_fraction = get_fig_votes(df_plot, input_storage)
        fig_fraction.update_layout(dragmode=tool)
        fig_dissgrid = get_fig_dissenters(df_plot, input_storage)

        return fig_fraction, fig_dissgrid
    
    # update the ID store from selection in both figures:
    @callback(Output("idstore", "data"),
              Input("fig-fraction", "selectedData"),
              State("fig-fraction", "selectedData"),
              Input("fig-dissgrid", "selectedData"),
              State("fig-dissgrid", "selectedData"))
    def update_idstore(
        frac_selection_json,
        frac_state_json,
        grid_selection_json,
        grid_state_json
    ):
        # frac status:
        frac = frac_selection_json or frac_state_json or []
        grid = grid_selection_json or grid_state_json or []

        frac_ids = {i["customdata"][4] for i in frac["points"]} if len(frac) > 0 else set()
        grid_ids = {i["customdata"][4] for i in grid["points"]} if len(grid) > 0 else set()

        logger.info(f"frac: {frac_ids}")
        logger.info(f"grid: {grid_ids}")
        
        union = frac_ids.union(grid_ids)
        logger.info(f"union: {union}")

        return list(union)

    # update display from ID store:    
    @callback(
        Output("display", "children"),
        Input("idstore", "data"),
        State("idstore", "data")
    )
    def update_display(idstore_input, idstore_state):
        data = idstore_input if idstore_input else idstore_state

        return json.dumps(data)
    
    return app  # .server



