import logging

import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd


def get_fig_votes(votes_plot):
    """
    Per-fraction x per-legislature figure showing dissent poll-wise.
    """

    vote_map = {
        "yes": "#00aa00",
        "no": "#aa0000",
        "abstain": "#000000",
    }

    # ranges and panel sizes:
    panel1_xmin = votes_plot.unanimity.max()
    panel3_xmax = (
        votes_plot.groupby("y")["on_party_line"].apply(lambda x: sum(x == False)).max()
    )
    xspan = panel1_xmin + panel3_xmax
    # poll result should be 5 % width of the plot:
    panel2_width = 1 / 50 * xspan
    height = votes_plot.y.max()

    votes_opl = votes_plot.loc[votes_plot.on_party_line]
    votes_opl = votes_opl.groupby("y").agg("first").reset_index()
    votes_dissent = votes_plot.loc[~votes_plot.on_party_line]
    parliament_vote = (
        votes_plot.groupby("y").parliament_vote.agg("first").to_frame().reset_index()
    )
    parliament_vote["x"] = 0

    fig = make_subplots(
        cols=3,
        rows=1,
        column_widths=[panel1_xmin, panel2_width, panel3_xmax],
        horizontal_spacing=.0,
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
            col=1, row=1
        )

    # individual markers for each dissenter:
    for (name, vote), grp in votes_dissent.groupby(["name", "vote"], observed=True):

        fig.add_trace(
            go.Bar(
                orientation="h",
                y=grp.y,
                x=[1],
                marker=dict(
                    line_width=.5,
                    line_color="white",
                    color=vote_map[vote],
                ),
                showlegend=False,
                customdata=grp[["label", "date", "vote", "name"]],
                hovertemplate="<b>%{customdata[3]}</b> (%{customdata[1]})<br>%{customdata[0]}<extra>%{customdata[2]}</extra>",
            ),
            col=3, row=1
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
            col=2, row=1,
        )

    fig.add_annotation(
        text="<= Fraktionslinie",
        x=-5, y=1,
        xanchor="right", xref="x",
        yanchor="bottom", yref="y domain",
        showarrow=False,
        font=dict(size=18),
        col=1, row=1,
    )

    fig.add_annotation(
        text="Dissens =>",
        x=5, y=1,
        xanchor="left", xref="x",
        yanchor="bottom", yref="y3 domain",
        showarrow=False,
        font=dict(size=18),
        col=3, row=1,
    )

    # white bg for parliamentary vote:
    fig.add_shape(
        type="rect",
        x0=0, x1=1, xref="x2 domain",
        y0=0, y1=1, yref="y2 domain",
        col=2, row=1,
        line_width=0,
        fillcolor="white",
        layer="below",
    )

    fig.update_layout(
        barmode="relative",
        width=1200,
        height=1500,
        plot_bgcolor="#dddddd",
        margin=dict(t=30, r=0, b=0, l=0),
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
        range=[.5, height + .5]
    )

    return fig


def get_fig_dissenters(votes_plot):
    """
    Show every MdB who dissented at least once and evey poll with at least one dissenter as a grid.
    """

    df_diss = (
        # look only at dissenting votes:
        votes_plot.loc[~votes_plot.on_party_line]
        # order y-axis by degree of dissent per MdB, select relevant attributes:
        .sort_values("n_dissent", ascending=True)[["name", "label", "party_line", "vote"]]
        .reset_index(drop=True)
    )

    # 
    label_freq = (
        df_diss
        .groupby("label")
        .size()
        .to_frame("freq")
        .reset_index()
        .sort_values(["freq", "label"], ascending=[False, True])
        .reset_index(drop=True)
        .reset_index()[["label", "freq", "index"]]
        .rename({"index": "x"}, axis=1)
    )
    df_diss = pd.merge(df_diss, label_freq, how="left", on="label")
    df_diss.sort_values("x").head(20)

    fig = go.Figure()

    fig.add_trace(
        go.Scatter(
            x=df_diss.x,
            y=df_diss.name,
            mode="markers",
            marker=dict(
                size=8,
                symbol="square",
                color="rgba(0,0,128, 1)"
            ),
            customdata=df_diss[["name", "label", "party_line", "vote"]],
            hovertemplate="<b>%{customdata[0]}</b> zur Abstimmung<br>„<i>%{customdata[1]}</i>“<br>Stimme: %{customdata[3]}<br>Fraktionsmehrheit: %{customdata[2]}.<extra></extra>"
        )
    )

    fig.update_layout(
        width=800,
        height=1500,
        xaxis=dict(
            showticklabels=False
        ),
        margin=dict(t=0, r=0, b=0, l=0)
    )
    
    return fig
