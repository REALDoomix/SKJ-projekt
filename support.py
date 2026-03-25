import json


def load_metadata():
    with open("metadata.json", "r") as f:
        return json.load(f)
    
def save_metadata(data):
    with open("metadata.json", "w") as f:
        json.dump(data, f, indent=4)