import json
import requests
from urllib.request import urlopen, Request

aoi_endpoint_ext = "/api/v3/aois"
export_endpoint_ext = "/api/v3/exports"


class Api:
    def __init__(self, token, grid_path, logging):
        self.token = token
        self.grid_path = grid_path
        self.logging = logging

    def get_aois(self, filter_substring=None):

        #        intersections=false&intersection_geoms=false&export_full=false
        # Grab full dictionary for the export and parse out the download urls
        aoi_endpoint = f"{self.grid_path}{aoi_endpoint_ext}?intersections=false&intersection_geoms=false&export_full=false"
        self.logging.debug(f"endpoint: {aoi_endpoint}")
        info_request = Request(aoi_endpoint)
        info_request.add_header("Authorization", f"Bearer {self.token}")

        result = urlopen(info_request)
        response = json.loads(result.read())
        aois = response["aois"]

        if filter_substring:
            return [aoi for aoi in aois if filter_substring in aoi["notes"]]
        else:
            return aois
