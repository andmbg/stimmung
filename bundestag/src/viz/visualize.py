import logging
import plotly.graph_objects as go

def get_fig_votes(df):
    """
    Per-fraction x per-legislature figure showing dissent poll-wise.
    """

    fig = go.Figure()

    
    x_range = [df_plot.x.min() - 1, df_plot.x.max() + 1]

    vote_map = {
        "yes": "#00aa00",
        "no": "#aa0000",
        "abstain": "#000000",
    }
    party_map = {
        "AfD": "#4488ff",
    }

    for (dissents, name, vote), grp in df_plot.groupby(["n_dissent", "name", "vote"], observed=True):
        
        fig.add_trace(
            go.Scatter(
                mode="markers",
                x=grp.x,
                y=grp.y,
                name=f"{name}" + (f": {dissents}" if dissents > 0 else ""),
                marker_color=vote_map[vote],
                marker_symbol="square",
                showlegend=False,
                customdata=grp[["name", "label", "date"]],
                hovertemplate="%{customdata[0]}<extra></extra>",
                hoverinfo="name",
            ),
        )

    fig.update_layout(
        width=1200,
        height=1500,
        xaxis=dict(
            zerolinecolor="black",
            zerolinewidth=5,
            range=x_range,
            showticklabels=False,
        ),
        yaxis=dict(
            showticklabels=False,
        ),
        plot_bgcolor="#ffffff",
    )