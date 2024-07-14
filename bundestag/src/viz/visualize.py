import logging

import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd

from bundestag.src.log_config import setup_logger

setup_logger()
logger = logging.getLogger(__name__)


def get_fig_votes(votes_plot, selected_vote_ids: list):
    """
    Per-fraction * per-legislature figure showing dissent poll-wise.
    """

    vote_map = {
        "yes": "rgba(0,200,0, .5)",
        "no": "rgba(200,0,0, .5)",
        "abstain": "rgba(100,100,100, .5)",
    }

    logger.info(f"Received vote_ids: {selected_vote_ids}")

    df = votes_plot.copy()

    #
    # ranges and panel sizes:
    #
    layout_measures = {}
    layout_measures["panel1_xmin"] = df.unanimity.max()
    layout_measures["panel3_xmax"] = (
        df.groupby("y")["on_party_line"].apply(lambda x: sum(x == False)).max()
    )
    layout_measures["xspan"] = layout_measures["panel1_xmin"] + layout_measures["panel3_xmax"]
    # poll result should be 2 % width of the plot:
    layout_measures["panel2_width"] = 1 / 50 * layout_measures["xspan"]
    layout_measures["height"] = df.y.max()
    
    # for each poll, get one datapoint for the partyline vote
    # (x extension is in "unanimity" col):
    votes_opl = df.loc[df.on_party_line]
    votes_opl = votes_opl.groupby("y").agg("first").reset_index()
    
    # we care about each individual dissenter vote:
    votes_dissent = df.loc[~df.on_party_line]
    
    # for each poll, get overall result once:
    parliament_vote = (
        df.groupby("y").parliament_vote.agg("first").to_frame().reset_index()
    )
    parliament_vote["x"] = 0

    fig = make_subplots(
        cols=3,
        rows=1,
        column_widths=[
            layout_measures["panel1_xmin"],
            layout_measures["panel2_width"],
            layout_measures["panel3_xmax"],
        ],
        horizontal_spacing=0.0,
        shared_yaxes=True,
    )

    # single bars for the fraction majority vote:
    for vote, grp in votes_opl.groupby("vote", observed=True):

        fig.add_trace(
            go.Bar(
                orientation="h",
                y=grp.y,
                x=-grp.unanimity,
                marker=dict(
                    line_width=1,
                    # line_color="cyan",
                    color=vote_map[vote],
                ),
                showlegend=False,
                customdata=grp[["label", "date"]],
                hovertemplate="%{customdata[0]}<extra></extra>",
            ),
            col=1,
            row=1,
        )

    # individual markers for each dissenter,
    # grouped by person (name) and color (yes/no/abs vote):
    for vote, grp in votes_dissent.groupby("vote", observed=True):

        selected_votes_rownum = (grp["vote_id"].isin(selected_vote_ids)).to_numpy().nonzero()[0].tolist()
        logger.info(f"vote '{vote}' selected_votes_rownum: {selected_votes_rownum}")

        fig.add_trace(
            go.Bar(
                orientation="h",
                y=grp.y,
                x=np.repeat([1], len(grp)),
                marker=dict(
                    line_width=.5,
                    line_color="white",
                    color=vote_map[vote],
                ),
                showlegend=False,
                # customdata=grp.vote_id,
                customdata=grp.reset_index()[["label", "date", "vote", "name", "vote_id"]],
                hovertemplate="<b>%{customdata[3]}</b> (%{customdata[1]})<br>%{customdata[0]}<extra>%{customdata[2]}</extra>",
                selectedpoints=selected_votes_rownum,
            ),
            col=3,
            row=1,
        )

    # overall result of each vote:
    for vote, grp in parliament_vote.groupby("parliament_vote"):

        fig.add_trace(
            go.Scatter(
                mode="markers",
                y=grp.y,
                x=grp.x,
                marker_color=vote_map[vote],
                marker_size=10,
                marker_line_color="black",
                marker_line_width=1,
                showlegend=False,
            ),
            col=2,
            row=1,
        )

    fig.add_annotation(
        text="Fraktionslinie",
        x=-5,
        y=1,
        xanchor="right",
        xref="x",
        yanchor="bottom",
        yref="y domain",
        showarrow=False,
        font=dict(size=18),
        col=1,
        row=1,
    )

    fig.add_annotation(
        text="Dissens",
        x=5,
        y=1,
        xanchor="left",
        xref="x",
        yanchor="bottom",
        yref="y3 domain",
        showarrow=False,
        font=dict(size=18),
        col=3,
        row=1,
    )

    # white bg for parliamentary vote:
    # fig.add_shape(
    #     type="rect",
    #     x0=0, x1=1, xref="x2 domain",
    #     y0=0, y1=1, yref="y2 domain",
    #     col=2, row=1,
    #     line_width=0,
    #     fillcolor="white",
    #     layer="below",
    # )

    fig.update_layout(
        title=dict(
            text=(
                "<b>Die Fraktionen:</b> Wie hoch war der Grad der Abweichung in den Abstimmungen?<br>"
                f"Hier für die Fraktion: {df.fraction.iloc[0]}"
            )
        ),
        barmode="relative",
        # width=900,
        height=100 + 11 * layout_measures["height"],
        plot_bgcolor="rgba(0,0,0, 0)",
        paper_bgcolor="rgba(255,255,255, .5)",
        margin=dict(t=100, r=0, b=0, l=0),
        xaxis3_range=[-0.5, layout_measures["panel3_xmax"]],
        clickmode="event+select",
        dragmode="select",
        newselection_mode="gradual"
    )

    fig.update_xaxes(
        showticklabels=False,
        showgrid=False,
        zeroline=False,
    )

    fig.update_yaxes(
        showticklabels=False,
        showgrid=False,
        zeroline=False,
        range=[0.5, layout_measures["height"] + 0.5]
    )

    logger.info(f"just drew frac plot with selection {selected_vote_ids}")

    return fig


def get_fig_dissenters(votes_plot, selected_vote_ids):
    """
    Show every MdB who dissented at least once and evey poll with at least one dissenter as a grid.
    """

    df_diss = (
        # look only at dissenting votes:
        votes_plot.loc[~votes_plot.on_party_line]
        # order y-axis by degree of dissent per MdB, select relevant attributes:
        .sort_values(["n_dissent", "name"], ascending=[True, True])[
            ["name", "label", "party_line", "vote", "vote_id"]
        ].reset_index(drop=True)
    )

    # fix y-axis sorting by giving explicit row numbers in the plot:
    df_diss.name = pd.Categorical(df_diss.name, ordered=True, categories=df_diss.name.unique())

    height = len(df_diss.name.unique())

    #
    label_freq = (
        df_diss.groupby("label")
        .size()
        .to_frame("freq")
        .reset_index()
        .sort_values(["freq", "label"], ascending=[False, True])
        .reset_index(drop=True)
        .reset_index()[["label", "freq", "index"]]
        .rename({"index": "x"}, axis=1)
    )
    df_diss = pd.merge(df_diss, label_freq, how="left", on="label")
    df_diss.sort_values("x")

    selected_votes_rownum = (df_diss["vote_id"].isin(selected_vote_ids)).to_numpy().nonzero()[0].tolist()

    fig = go.Figure()

    fig.add_trace(
        go.Scatter(
            x=df_diss.x,
            y=df_diss.name,
            mode="markers",
            marker=dict(
                size=8,
                symbol="square",
                color="rgba(0,0,128, 1)",
                line_width=.5,
                line_color="white",
            ),
            selectedpoints=selected_votes_rownum,
            # customdata=df_diss.vote_id,
            customdata=df_diss[["name", "label", "party_line", "vote", "vote_id"]],
            hovertemplate="<b>%{customdata[0]}</b> zur Abstimmung<br>„<i>%{customdata[1]}</i>“<br>Stimme: %{customdata[3]}<br>Fraktionsmehrheit: %{customdata[2]}.<extra></extra>",
            showlegend=False,
        )
    )

    fig.update_layout(
        title=dict(
            text=(
                "<b>Die Abgeordneten:</b> Wer hat bei welcher Frage abweichend gestimmt?<br>"
                f"Hier für die Fraktion: {votes_plot.fraction.iloc[0]}:"
            ),
            x=0,
            xref="paper",
        ),
        # width=900,
        height=100 + height * 15,
        plot_bgcolor="rgba(0,0,0, 0)",
        paper_bgcolor="rgba(255,255,255, .5)",
        xaxis=dict(
            showticklabels=False,
            dtick=1,
        ),
        yaxis=dict(
            range=[-0.5, height - 0.5],
        ),
        margin=dict(t=100, r=0, b=0, l=0),
        clickmode="event+select",
        dragmode="select",
        newselection_mode="gradual"
    )

    return fig
