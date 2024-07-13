import requests
import pandas as pd
import json
from dataclasses import dataclass, field
from pathlib import Path
import logging

from ...config import awde_url

logger = logging.getLogger(__name__)

def query_all(
    url: str, endpoint: str, params: dict, page: int = 0, pager_limit: int = 1000, total: int = None
) -> list:
    """
    Query the endpoint, get > 1000 results if there are.
    """
    params["page"] = page
    params["pager_limit"] = total if total is None or total < pager_limit else pager_limit

    response = requests.get(url + endpoint, params=params)
    response.raise_for_status()  # Raise an error for bad responses
    response_dict = json.loads(response.text)

    result_list = response_dict["data"]
    r = response_dict["meta"]["result"]

    nrow_awde = r["total"]
    limit = total if total is not None else nrow_awde
    done = int(r["page"]) * int(r["results_per_page"]) + int(r["count"])

    while done < limit:

        params["page"] += 1

        response = requests.get(url + endpoint, params=params)
        response.raise_for_status()
        response_dict = json.loads(response.text)

        this_result_list = response_dict["data"]
        result_list += this_result_list

        r = response_dict["meta"]["result"]
        done = int(r["page"]) * int(r["results_per_page"]) + int(r["count"])
    
    return result_list


@dataclass
class Dataset:
    """
    Represents a dataset as offered at abgeordnetenwatch.
    Field rawdata, if changed, updates data, which in turn updates nrow. Also, when the transformation
    function is set, it updates data. So Dataset always represents a consistent combination of raw and
    processed data and metadata.
    """

    name: str
    awde_endpoint: str
    awde_url: str = awde_url
    awde_params: dict = field(default_factory=dict)
    # awde_nrow: int = field(init=False, default=None)
    filepath: Path = None
    _rawdata: pd.DataFrame = field(init=False, default=None)
    _data: pd.DataFrame = field(init=False, default=None)
    _nrow: int = field(init=False, default=None)

    @property
    def rawdata(self):
        return self._rawdata

    @property
    def data(self):
        return self._data

    @property
    def nrow(self):
        return self._nrow

    @property
    def transform_data(self):
        return self._transform_data

    @data.setter
    def data(self, value):
        self._data = value
        self._nrow = len(value) if value is not None else None

    @rawdata.setter
    def rawdata(self, value):
        self._rawdata = value
        self.data = self.transform_data(value) if value is not None else None

    @transform_data.setter
    def transform_data(self, value):
        self._transform_data = value
        self.data = (
            self.transform_data(self.rawdata) if self.rawdata is not None else None
        )

    def __post_init__(self):
        self._load_rawdata()
        # Get nrow from awde
        # self.awde_nrow = self.get_awde_nrow()

    def _load_rawdata(self):
        # set filepath for cache from name:
        filepath = Path().cwd() / "data" / f"{self.name}.parquet"
        # Attempt to load data from the local file,
        # set data if possible, set nrow if possible:
        if filepath.exists():
            self.filepath = filepath
            self.rawdata = pd.read_parquet(self.filepath)
            logger.info(f"Loaded data from cache: {self.filepath}")
        else:
            self.filepath = None
            self.rawdata = None

    def save(self):
        # Save the dataframe to the local file
        if self.rawdata is not None:
            self.rawdata.to_parquet(self.filepath, index=False)

    def get_awde_nrow(self):  # disused
        # find out how many datapoints exist at abgeordnetenwatch for this endpoint
        query_params = {k: v for k, v in self.awde_params.items()}
        response = requests.get(
            self.awde_url + self.awde_endpoint,
            params=query_params.update({"range_end": 1}),
        )
        response.raise_for_status()
        metadata = json.loads(response.text)["meta"]
        nrow = metadata["result"]["total"]
        return nrow

    def fetch(self, total: int = None):
        """
        Fetch data from AWDE.
        """
        response = query_all(self.awde_url, self.awde_endpoint, params=self.awde_params, total=total)
        self.filepath = Path().cwd() / "data" / f"{self.name}.parquet"

        # sometimes values are [], which makes Arrow choke. Replace with None:
        def _noneify_empty_lists(value):
            if isinstance(value, list) and len(value) == 0:
                return None
            return value
        
        response = pd.DataFrame(response).map(_noneify_empty_lists)
        self.rawdata = pd.DataFrame(response)

    def _transform_data(self, data: pd.DataFrame) -> pd.DataFrame:
        # Default implementation (no transformation)
        return data

    def __repr__(self):
        out = f"<{'Empty ' if self.data is None else ''}Dataset '{self.name}'"
        if self.nrow is not None:
            out += f"; {self.nrow} rows"
        if self.filepath is not None:
            out += f"; cached"
        else:
            out += "; uncached"
        if self.data is not None:
            out += f"; {len(self.data.columns)} columns."
        out += ">"

        return out

    def __str__(self):
        out = f"{'Empty ' if self.data is None else ''}Dataset '{self.name}':\n"
        out += f"'{self.awde_url}' + '{self.awde_endpoint}'\n"
        out += "params: {"
        for k, v in self.awde_params.items():
            out += f"\n\t{k}: {v}"
        if len(self.awde_params) > 0:
            out += "\n\t"
        out += "}\n"
        if self.nrow is not None:
            out += f"nrow cached: {self.nrow}; "
        # out += f"nrow at awde if unfiltered: {self.awde_nrow}\n"
        if self.filepath is not None:
            out += f"cache file location: {self.filepath.relative_to(Path().cwd())}\n"
        else:
            out += "no file cached\n"

        return out
