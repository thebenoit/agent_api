from abc import ABC, abstractmethod
import json
import time

class BaseScraper(ABC):
    
    @abstractmethod
    def scrape(self, url: str) -> str:
        """scrape the url and return the data"""
        raise NotImplementedError
    
    def get_har_entry(self):
        """
        get the har entry from the har file
        headers, payload, resp_body 
        """
        # Extrait les headers de toutes les requêtes dans le HAR
        try:
            # Ouvre et lit le fichier HAR
            with open("data/facebook.har", "r") as f:
                try:
                    har_data = json.load(f)
                except json.JSONDecodeError as e:
                    print(f"Erreur de décodage JSON: {e}")
                    return None, None, None
                except Exception as e:
                    print(f"Erreur lors du chargement du fichier HAR: {e}")
                    return None, None, None

            for entry in har_data["log"]["entries"]:

                if "graphql" in entry["request"]["url"]:
                    print("graphql request found")

                    headers = [
                        (h["name"], h["value"]) for h in entry["request"]["headers"]
                    ]
                    payload = entry["request"].get("postData", {}).get("text", "")
                    resp_text = entry["response"].get("content", {}).get("text", "")

                    return headers, payload, json.loads(resp_text)
                else:
                    print("no graphql request found")

            return None, None, None

        except Exception as e:
            print(f"Erreur lors de l'extraction des headers : {e}")
            return None, None, None

        ##methode to get the har file from the driver
    
    def get_har(self,driver,url):
        print("Lancement du driver")
        driver.get(url)
        time.sleep(15)
        raw_har = self.driver.har
        # si c'est une chaîne JSON, on la parse
        if isinstance(raw_har, str):
            self.har = json.loads(raw_har)
        else:
            self.har = raw_har

        # Extract headers, payload, url and response body for graphql requests
        filtered_har = {
            "log": {
                "entries": [
                    {
                        "request": {
                            "url": entry["request"]["url"],
                            "headers": entry["request"]["headers"],
                            "method": entry["request"]["method"],
                            "postData": entry["request"].get("postData", {}),
                        },
                        "response": {
                            "content": entry["response"].get("content", {}),
                            "headers": entry["response"].get("headers", []),
                            "status": entry["response"].get("status"),
                            "statusText": entry["response"].get("statusText"),
                            "bodySize": entry["response"].get("bodySize"),
                            "body": entry["response"].get("body", ""),
                        },
                    }
                    for entry in self.har["log"]["entries"]
                    if entry["request"].get("url")
                    == "https://www.facebook.com/api/graphql/"
                ]
            }
        }

        # Write filtered HAR data to file
        with open("data/facebook.har", "w") as f:
            json.dump(filtered_har, f, indent=4)

        return filtered_har     