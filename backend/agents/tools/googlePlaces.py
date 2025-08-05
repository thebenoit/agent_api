from tools.base_tool import BaseTool
from dotenv import load_dotenv
import requests
import os

load_dotenv()



class GooglePlaces(BaseTool):
    def __init__(self):
        self.api_key = os.getenv("GOOGLE_PLACES_API_KEY")
        self.base_url = "https://places.googleapis.com/v1/places:searchText"
    
    @property
    def name(self):
        return "google_places"

    @property 
    def description(self):
        return "Search for places using Google Places API based on location and keywords"

    def execute(self,city:str,location_near:list):
        
        text_query = []
        
        print(self.api_key)
        headers ={
            "Content-Type": "application/json",
            "X-Goog-Api-Key": self.api_key,
            "X-Goog-FieldMask": "places.displayName,places.location"   
        }       
            
        if location_near:
            location_near = " ".join(location_near)
            print("location_near: ",location_near)
            text_query.append(f"{location_near}")
            
        if city:
            print("city: ",city)
            text_query.append(f"in {city}")
            
        
        text_query = " ".join(text_query)
        
        print(text_query)
        
        data = {
            "textQuery": text_query
        }
        
        try:
            response = requests.post(
                self.base_url,
                headers=headers,
                json=data  # requests convertit automatiquement en JSON
            )
            response.raise_for_status()
            print(response.json())
            return response.json()
            
        except requests.exceptions.RequestException as e:
            print(f"Erreur lors de la requête: {e}")
            return None
            
        
        
        