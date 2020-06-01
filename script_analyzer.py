import utils
import script_parser
import config

import matplotlib.pyplot as plt
import numpy as np
import json
from nltk.sentiment.vader import SentimentIntensityAnalyzer

classifier = SentimentIntensityAnalyzer()

""" Get compound sentiment score for a given utterance. """
def get_sentiment_score(text):
    scores = classifier.polarity_scores(text)
    return scores["compound"]

class AnalyzedMovieScript:
    def __init__(self, parsed_script):
        self.parsed_script = parsed_script
        self.character_names = parsed_script.character_names
        self.entries = parsed_script.entries

        # Compute sentiment score for all entries
        for e in self.entries:
            if e["type"] in [script_parser.TYPE_SPEECH, script_parser.TYPE_DIRECTION]:
                e["cs"] = get_sentiment_score(e["content"])

        # Compute information about characters (line count, average compound score)
        self.characters = dict()
        for n in parsed_script.character_names:
            self.characters[n] = {"name": n, "line_count": 0, "avg_cs": 0}
        for i in range(1, len(parsed_script.entries)):
            e = parsed_script.entries[i]
            prev_e = parsed_script.entries[i-1]
            if e["type"] == script_parser.TYPE_SPEECH and prev_e["type"] == script_parser.TYPE_CHARACTER:
                name = prev_e["content"]
                c = self.characters[name] 
                c["avg_cs"] = (c["line_count"] * c["avg_cs"] + e["cs"]) / (c["line_count"] + 1)
                c["line_count"] += 1
    
         # Co-occurrence matrix
        self.co_occurrences = self.create_cooccurrences_matrix()
    

    def create_cooccurrences_matrix(self):
        # Init matrix
        m = dict()
        for namei in self.character_names:
            m[namei] = dict()
            for namej in self.character_names:
                m[namei][namej] = {"count": 0, "avg_cs": 0}

        # Fill matrix
        characters_in_scene = dict()
        for i,e in enumerate(self.entries):
            # Check for a new scene
            if e["type"] == script_parser.TYPE_LOCATION:
                if len(characters_in_scene) > 0:
                    for namei in characters_in_scene:
                        avg_cs_i = (characters_in_scene[namei]["sum_cs"] / characters_in_scene[namei]["num_lines"])
                        for namej in characters_in_scene:
                            avg_cs_j = (characters_in_scene[namej]["sum_cs"] / characters_in_scene[namej]["num_lines"])
                            mutual_cs = (avg_cs_i + avg_cs_j) / 2
                            c = m[namei][namej]["count"]
                            m[namei][namej]["avg_cs"] = (m[namei][namej]["avg_cs"] * c + mutual_cs) / (c + 1)
                            m[namei][namej]["count"] += 1 # TODO replace 1 with number of appearances? 
                            
                characters_in_scene = dict()
            if e["type"] == script_parser.TYPE_CHARACTER:
                name = e["content"]
                if not name in characters_in_scene:
                    characters_in_scene[name] = {"sum_cs": 0, "num_lines": 0}
                characters_in_scene[name]["num_lines"] += 1

                if i+1 < len(self.entries) and self.entries[i+1]["type"] == script_parser.TYPE_SPEECH:
                    characters_in_scene[name]["sum_cs"] += self.entries[i+1]["cs"]
        
        return m

    
    def to_dict(self):
        obj  = dict()
        obj["info"] = self.parsed_script.info
        obj["entries"] = self.entries
        obj["characters"] = self.characters
        obj["cooccurrences"] = self.co_occurrences
        return obj


""" Saves an analyzed movie to file. """
def save_analyzed_movie(analyzed):
    movie_info = analyzed.parsed_script.info
    obj = analyzed.to_dict()
    safe_name = movie_info["title"].lower().replace(" ", "-").replace(":", "")

    # Write JSON to file
    with open(config.DIR_ANALYZED + safe_name + ".json", "w") as out_file:
        json.dump(obj, out_file)
    
    print("Saved", safe_name + ".json")


if __name__ == "__main__":
    export_movies = [
        "Apocalypse Now",
        "Avatar",
        "Blade Runner",
        "Ghostbusters",
        "Gladiator",
        "Godfather",
        "Guardians of the Galaxy Vol 2",
        "Indiana Jones and the Raiders of the Lost Ark",
        "Indiana Jones and the Last Crusade",
        "Indiana Jones and the Temple of Doom",
        "Jurassic Park",
        "Lord of the Rings: Fellowship of the Ring",
        "Lord of the Rings: Return of the King",
        #"Lord of the Rings: The Two Towers"
        "Men in Black",
        "Mission Impossible",
        "Pirates of the Caribbean",
        "Pulp Fiction",
        "Shrek",
        "Star Wars: A New Hope",
        "Star Wars: The Empire Strikes Back",
        "Star Wars: Return of the Jedi",
        "Star Wars: The Phantom Menace",
        "Star Wars: Attack of the Clones",
        "Star Wars: Revenge of the Sith",
        "Star Wars: The Force Awakens",
        "Terminator",
        "Terminator 2: Judgement Day",
        "Terminator Salvation",
        "Thor",
        "Thor Ragnarok",
        "Titanic",
        "TRON",
        "Wall-E",
        "Wizard of Oz", 
        "Wolf of Wall Street",
        "X-Men Origins: Wolverine",
    ]

    movies = [utils.get_movie_metadata_by_name(name) for name in export_movies]
    #movies = [utils.get_movie_metadata_by_name(export_movies[-1])]

    for i, movie in enumerate(movies):
        print("Parsing", "'" + movie["title"] + "'", "(" + str(i+1) + "/" + str(len(movies)) + ")")
        parsed_script = script_parser.parse_movie(movie)
        if parsed_script != None:
            parsed_script.print()
            analyzed = AnalyzedMovieScript(parsed_script)
            save_analyzed_movie(analyzed)


    