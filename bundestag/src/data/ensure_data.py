import logging

import pandas as pd

from bundestag.src.data.models import Dataset


logger = logging.getLogger(__name__)


def get_legislatures(label: str = None):

    logger.info("Loading legislatures data")

    legislatures = Dataset(
        name="legislatures",
        awde_endpoint="parliament-periods",
        awde_params={
            "label": label,
            "type": "legislature",
        },
    )
    if legislatures.data is None:
        legislatures.fetch()
        legislatures.save()

    return legislatures


def get_polls(legislature: int = 132):

    logger.info("Loading data about polls")

    polls = Dataset(
        name=f"polls_legislature_{legislature}",
        awde_endpoint="polls",
        awde_params={"field_legislature[entity.id]": legislature},
    )
    if polls.data is None:
        polls.fetch()
        polls.save()

    def _transform_polls(data: pd.DataFrame) -> pd.DataFrame:
        df = data.copy()
        df.rename(
            {"field_accepted": "accepted", "field_poll_date": "date"},
            axis=1,
            inplace=True,
        )
        df["parliament_vote"] = df.accepted.apply(lambda x: "yes" if x else "no")
        df["fid_legislatur"] = df.field_legislature.apply(lambda x: x["id"])
        df["fid_topic"] = df.field_topics.apply(
            lambda x: ",".join([str(i["id"]) for i in x]) if x is not None else None
        )
        df = df[
            ["id", "fid_legislatur", "fid_topic", "label", "date", "parliament_vote"]
        ]

        return df

    polls.transform_data = _transform_polls

    return polls


def get_votes():
    """
    Get vote-level data on all relevant votes at Bundestag.
    """

    logger.info("Loading vote-level data")

    # identify for which polls we want vote-level data:
    polls = get_polls()
    poll_ids = polls.data.id

    # load or download vote data:
    all_votes = {}

    for id in poll_ids:
        all_votes[id] = Dataset(
            name=f"poll_{id}", awde_endpoint="votes", awde_params={"poll": id}
        )
        if all_votes[id].data is None:
            logger.info(f"poll id {id} not present locally; downloading from AWDE")

            all_votes[id].fetch()
            all_votes[id].save()

    # We want our vote data to look different from what we get from AWDE.
    # This function creates a pretty version of the raw data on the fly,
    # and we make it the display function of all Datasets in all_votes;
    # (raw data stay untouched):
    def _transform_vote(data):
        df = data.copy()

        df["name"] = df.mandate.apply(
            lambda d: d["label"].split(" (Bundestag")[0] if d is not None else None
        )
        df["fid_vote"] = df.id
        df["fid_poll"] = df.poll.apply(lambda d: d["id"])
        df["fraction"] = df.fraction.apply(
            lambda d: d["label"].split(" (Bundestag")[0] if d is not None else None
        )

        df = df[
            [
                "fid_poll",
                "fid_vote",
                "name",
                "fraction",
                "vote",
                "reason_no_show",
                "reason_no_show_other",
            ]
        ]

        return df

    for v in all_votes.values():
        v.transform_data = _transform_vote

    allvotes = pd.concat([x.data for x in all_votes.values()])

    logger.info("Processing vote data")

    df = (
        allvotes.set_index("fid_poll")
        .join(polls.data.set_index("id"))
        .reset_index()
        .rename({"fid_poll": "poll_id", "fid_vote": "vote_id"}, axis=1)
    )

    df.fraction = df.fraction.replace(
        {
            "SPD": "SPD",
            "CDU/CSU": "CDU",
            "BÜNDNIS 90/DIE GRÜNEN": "GRÜ",
            "FDP": "FDP",
            "AfD": "AfD",
            "DIE LINKE.": "LIN",
            "Die Linke. (Gruppe)": "LIN",
            "BSW (Gruppe)": "BSW",
        }
    )

    df["n_votes"] = df.groupby("poll_id").poll_id.transform("size")
    df["sum_yes"] = df.groupby("poll_id").vote.transform(lambda x: (x == "yes").sum())
    df["sum_no"] = df.groupby("poll_id").vote.transform(lambda x: (x == "no").sum())
    df["sum_abs"] = df.groupby("poll_id").vote.transform(lambda x: (x == "abs").sum())
    df.set_index("poll_id", inplace=True)

    # remove fractionless votes:
    old_nrow = len(df)

    df = df.loc[(df.fraction.ne("fraktionslos")) & (df.fraction.notna())]
    a, b = (old_nrow - len(df), (old_nrow - len(df)) / old_nrow * 100)
    logger.info(f"Fractionless deletion removes {a} rows, {round(b, 1)}% of votes.")

    # cast vote as ordered Category type:
    df.vote = pd.Categorical(
        df.vote, ordered=True, categories=["yes", "no", "abstain", "no_show"]
    )
    df.reset_index(inplace=True)

    # poll_id being int should not mess with the y-position of traces, so cast as str:
    df.poll_id = df.poll_id.astype("str")

    # drop no_shows and the columns that explain no_shows:
    df = df.loc[df.vote.ne("no_show")].drop(
        ["reason_no_show", "reason_no_show_other"], axis=1
    )

    # add party line per poll and fraction:
    party_line = (
        df.groupby(["fraction", "poll_id"])
        .vote.apply(lambda x: x.mode())
        .reset_index(level=-1, drop=True)
    )
    party_line.name = "party_line"
    df = (
        df.reset_index()
        .set_index(["fraction", "poll_id"])
        .join(party_line)
        .reset_index()
    )

    # MdB x-position:
    # sort within each fraction and poll;
    # first, by "within vs. without party line"
    # second, by vote; => no effect on party line voters, but dissenters are grouped by their vote
    # finally, enumerate for x position by groups: fraction, poll, partyline (both dissent options should be counted together)
    df = df.sort_values(["fraction", "poll_id", "party_line", "vote"])
    df["on_party_line"] = df.vote == df.party_line
    # df["x"] = (
    #     df.groupby(["fraction", "poll_id", "on_party_line"], observed=True)
    #     .cumcount()
    #     .add(1)
    # )
    # df.x = df.apply(lambda x: -x.x if x.vote == x.party_line else x.x, axis=1)

    # mark dissenting voters:
    dissenters = (
        df.groupby(["fraction", "name"])
        .apply(lambda x: sum(x.on_party_line == False), include_groups=False)
        .to_frame("n_dissent")
    )
    df = df.set_index(["fraction", "name"]).join(dissenters).reset_index()

    # poll y-position:
    # compute degree of unanimity as (1 + N_dissenters) / (N_lineVoters)
    unanimity = (
        df.groupby(["fraction", "poll_id"])
        .apply(lambda df: df.on_party_line.sum(), include_groups=False)
        .to_frame("unanimity")
        .sort_values(["fraction", "unanimity"])
    )
    unanimity["y"] = unanimity.groupby(["fraction"]).cumcount().add(1)
    df = df.set_index(["fraction", "poll_id"]).join(unanimity).reset_index()

    return df
