from tools.base_tool import BaseTool
from myHandler import MyHandler

from typing import List


class GetCoordinates(BaseTool):
    def __init__(self):
        self.db_path = "data/montreal_spatialite.db"

    @property
    def name(self):
        return "get_coordinates"

    @property
    def description(self):
        return "Find coordinates of locations based on OpenStreetMap tags (schools, parks, restaurants, etc.)"

    def execute(self, city: str, location_near: dict, radius: str):
        
        city = "Montreal"

        handler = MyHandler(city,location_near, self.db_path)

        handler.search_in_sqlite()
        
        print("handler.found: ", list(handler.found.items())[:1])

        return [
            {"name": name, "lat": lat, "lon": lon}
            for name, (lat, lon) in handler.found.items()
        ]
