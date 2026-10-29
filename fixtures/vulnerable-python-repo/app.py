import requests
import yaml

def fetch_data(url: str):
    response = requests.get(url, timeout=5)
    return response.json()

def parse_config(content: str):
    return yaml.load(content, Loader=yaml.FullLoader)

