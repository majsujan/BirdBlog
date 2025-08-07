from flask import Flask, render_template, request
import pandas as pd
import json

app = Flask(__name__)

# Load species data
species_df = pd.read_csv("unique_species_per_country.csv")

# Load map data
with open("map_data.json", "r") as f:
    map_data = json.load(f)

@app.route("/")
def index():
    total_species = species_df["Species"].nunique()
    return render_template("index.html", map_data=map_data, total_species=total_species)

@app.route("/search")
def search():
    country = request.args.get("country", "").upper()
    filtered = species_df[species_df["Country Code"] == country]
    species_list = filtered["Species"].unique().tolist()
    return {"country": country, "species": species_list}

if __name__ == "__main__":
    app.run(debug=True)
