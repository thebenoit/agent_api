from pydantic import BaseModel, Field, field_validator
from typing import List



class CoordinatesInput(BaseModel):
    city: str = Field(..., description="The city to search for")
    location_near: dict = Field(
        ...,
        description="""Dictionary of OpenStreetMap tags to search for. Use OSM tag format like:
    AMENITIES:
        "amenity": ["school", "university", "college","kindergarten"] # education
        "amenity": ["restaurant", "cafe", "bar"] # food & drink
        "amenity": ["hospital", "pharmacy", "clinic"] # healthcare
        "amenity": ["bank", "post_office", "library"] # services
        "amenity": ["fuel", "parking"] # transport
    
    LEISURE:
        "leisure": ["park", "playground", "sports_centre"]
        "leisure": ["swimming_pool", "golf_course"]
    
    SHOPS:
        "shop": ["supermarket", "bakery", "clothes"]
        "shop": ["electronics", "pharmacy"]
    
    TRANSPORT:
        "highway": ["bus_stop"]
        "railway": ["station", "subway_entrance"]
        "aeroway": ["aerodrome"]
        "public_transport": ["stop_position"]
    
    NATURAL:
        "natural": ["water", "forest", "beach"]
    
    Example: {"amenity": ["school"], "leisure": ["park"], "shop": ["supermarket"]}""",
    )
    radius: str = Field(..., description="The radius to search for")

    @field_validator("location_near")
    def validate_location_near(cls, v):
        if not v:
            raise ValueError("location_near must be a list of strings")
        return v
