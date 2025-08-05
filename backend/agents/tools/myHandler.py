import osmium
import apsw
import sqlite3
from typing import Set, Dict, Tuple


class MyHandler(osmium.SimpleHandler):
    def __init__(
        self,
        city: str,
        wanted_tags: dict[str, list[str]],
        db_path: str = "data/montreal_spatialite.db",
    ):
        print("MyHandler initialized")
        ##initialiser la sous classe (osmium.SimpleHandler)
        # super().__init__()
        self.city = city #"Montreal"
        self.wanted_tags = wanted_tags
        self.found: Dict[str, Tuple[float, float]] = {}
        self.db_path = db_path

    def search_in_sqlite(self):
        """Search in the sqlite database for the wanted tags"""
        self.found = {}
        # conn = sqlite3.connect(self.db_path)
        # # load the spatialite extension
        # conn.enable_load_extension(True)
        # # where the extension is located
        # conn.load_extension("/opt/homebrew/opt/libspatialite/lib/mod_spatialite.dylib")

        # conn.row_factory = sqlite3.Row
        # cursor = conn.cursor()
        
        # if no wanted tags, return the default coordinates for the city
        if self.wanted_tags is None:
            # Return Montreal's default coordinates if no tags specified
            self.found["Montreal"] = ("45.5017", "-73.5673")
            return

        conn = apsw.Connection(self.db_path)
        conn.enableloadextension(True)
        conn.loadextension("/opt/homebrew/opt/libspatialite/lib/mod_spatialite.dylib")
        cursor = conn.cursor()
     
        for tag_key, tag_values in self.wanted_tags.items():
            for tag_value in tag_values:
                # construct the query
                query = """
                SELECT p.ogc_fid, p.name, p.osm_id, 
                       ST_X(p.GEOMETRY) as longitude, 
                       ST_Y(p.GEOMETRY) as latitude
                FROM points p
                JOIN points_fid_to_tag t ON p.ogc_fid = t.ogc_fid
                WHERE t.key = ? AND t.value = ?
                """
                # execute the query
                print(f"Searching for {tag_key} = {tag_value}")
                cursor.execute(query, (tag_key, tag_value))
                # fetch the results
                results = cursor.fetchall()
                # print the results
                print(f"Found {len(results)} results")

                for ogc_fid, name, osm_id, lon, lat in results:
                    key = name or f"point_{osm_id}"
                    self.found[key] = (lat, lon)

        conn.close()
        print(f"Found {len(self.found)} results")

    # called by apply_file
    def node(self, n):
        # n est un objet de type osmium.Node
        name = n.tags.get("name")
        # si le nom est dans la liste des wanted,
        if name in self.wanted:
            # on ajoute le nom et les coordonnées dans le dictionnaire found
            self.found[name] = (n.lat, n.lon)

    # called by apply_file
    def way(self, w):
        name = w.tags.get("name")
        if name in self.wanted:
            self.found[name] = (w.nodes[0].lat, w.nodes[0].lon)
