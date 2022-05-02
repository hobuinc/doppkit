import json
import asyncio

from .cache import cache as cacheFunction

aoi_endpoint_ext = "/api/v3/aois"
export_endpoint_ext = "/api/v3/exports"


class Api:
    def __init__(self, args):
        self.args = args

    def get_aois(self, pk=None):
        #        intersections=false&intersection_geoms=false&export_full=false
        # Grab full dictionary for the export and parse out the download urls

        filter = "intersections=false&intersection_geoms=false&export_full=false"
        if pk:
            aoi_endpoint = f"{self.args.url}{aoi_endpoint_ext}/{pk}?intersections=false&intersection_geoms=false&export_full=true&sort=pk"
        else:
            aoi_endpoint = f"{self.args.url}{aoi_endpoint_ext}?{filter}"

        headers = {"Authorization": f"Bearer {self.args.token}"}
        urls = [aoi_endpoint]
        files = asyncio.run(cacheFunction(self.args, urls, headers))

        response = json.load(files[0].bytes)

        if response.get('error'):
            raise Exception(response['error'])
        aois = response["aois"]
        return aois

    
    async def get_exports_async(self, export_pk):

        # grid.nga.mil/grid/api/v3/exports/56193?sort=pk&file_geoms=false
        export_endpoint = f"{self.args.url}{export_endpoint_ext}/{export_pk}?sort=pk&file_geoms=false"
        headers = {"Authorization": f"Bearer {self.args.token}"}
        urls = [export_endpoint]
        files = cacheFunction(self.args, urls, headers) 

        response = json.loads(files[0].data)

        if response.get('error'):
            return None

        exports = []
        async for f in files:
            j = json.loads(f.data)
            exports.append(j)

        output = []
        for e in exports:
            ex = e['exports']
            for item in ex:
                for f in item['exportfiles']:
                    output.append(f)
        return output

    
    def get_exports(self, export_pk):

        # grid.nga.mil/grid/api/v3/exports/56193?sort=pk&file_geoms=false
        export_endpoint = f"{self.args.url}{export_endpoint_ext}/{export_pk}?sort=pk&file_geoms=false"
        headers = {"Authorization": f"Bearer {self.args.token}"}
        urls = [export_endpoint]
        files = asyncio.run(cacheFunction(self.args, urls, headers))
        response = json.loads(files[0].data)

        if response.get('error'):
            return None

        exports = []
        for f in files:
            j = json.loads(f.data)
            exports.append(j)

        output = []
        for e in exports:
            ex = e['exports']
            for item in ex:
                for f in item['exportfiles']:
                    output.append(f)
        return output