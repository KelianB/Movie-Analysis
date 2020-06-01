import csv
import config

""" Converts movie metadata into an array for CSV storage. """
def movie_to_array(movie):
    return [
        movie["title"],
        ",".join(movie["authors"]),
        movie["page"],
        movie["script_page"]
    ]

""" Converts an array of raw movie metadata (e.g. from CSV) into a dictionary. """
def array_to_movie(arr):
    movie = dict()
    movie["title"] = arr[0]
    movie["authors"] = arr[1].split(",")
    movie["page"] = arr[2]
    movie["script_page"] = arr[3]
    return movie

""" Get metadata for a given movie from file storage. """
def get_movie_metadata(movie_index):
    # Read metadata CSV file
    with open(config.MOVIES_METADATA_FILE, newline="") as f:
        reader = csv.reader(f, delimiter=";", quotechar="|")

        # Find the correct row and return associated metadata
        for i, row in enumerate(reader):
            if i == 1 + movie_index:
                return array_to_movie(row)

    return None


""" Get metadata for all movies. """
def get_all_movies_metadata():
    # Read metadata CSV file
    with open(config.MOVIES_METADATA_FILE, newline="") as f:
        reader = csv.reader(f, delimiter=";", quotechar="|")

        # Parse CSV data for all movies
        movies = [array_to_movie(row) for i, row in enumerate(reader) if i > 0]
        
        return movies
    
    return None

""" Look for scanning mistakes (misread letters) in the given character name,
    checking against the dictionary of character occurrences. """
def fix_scan_errors(character_name, character_dict):
    scan_errors = {
        "B": "R",
        "G": "C",
        "l": "I",
        "R": "K"
    }
    for name in character_dict:
        if name != character_name and len(name) == len(character_name) and character_dict[name] > character_dict[character_name]:
            diff_idx = [i for i in range(len(name)) if name[i] != character_name[i]]
            if len(diff_idx) <= 2: # allow for max 2 scanning errors                    
                for i in diff_idx:
                    # Detect if there is indeed a scan error and fix it
                    if character_name[i] in scan_errors and name[i] == scan_errors[character_name[i]]:
                        character_name = character_name[:i] + scan_errors[character_name[i]] + character_name[i+1:]
                return character_name
    return character_name