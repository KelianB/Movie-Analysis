import requests
from bs4 import BeautifulSoup
import csv

import config
import utils

""" Get data from the movie page for the given movie. """
def add_specific_movie_data(movie):
    movie_page = requests.get(config.URL_IMSDB + movie["page"])
    movie_soup = BeautifulSoup(movie_page.content, "html.parser")
    
    # Get the <a href="...">Read "Star Wars: A New Hope" Script</a>
    script_a = movie_soup.select("table.script-details a:last-child")

    # Extract href
    script_href = script_a[0]["href"] if len(script_a) > 0 else None

    movie["script_page"] = script_href

""" Output data to file for all given movies. """
def output_movies_data(movies):
    with open(config.MOVIES_METADATA_FILE, "w", newline="") as f:
        writer = csv.writer(f, delimiter=";", quotechar="|", quoting=csv.QUOTE_MINIMAL)
        writer.writerow(["Title", "Authors", "IMSDb Page", "IMSDb Script Page"])

        without_script_page = 0
        non_html_script_page = 0

        for m in movies:
            # Ignore movie if its script page wasn't found
            if m["script_page"] == None:
                without_script_page += 1
            # Ignore movie if its script page isn't html (e.g. PDF)
            elif m["script_page"][-5:].lower() != ".html":
                non_html_script_page += 1
            else:
                writer.writerow(utils.movie_to_array(m))
        
        print("Script page not found for", without_script_page, "movies.")
        print("Non-HTML script page for", non_html_script_page, "movies.")

""" Get an array of movies that are listed on the IMSDB all-scripts page """
def get_imsdb_movies():
    # Access page that lists all movie entries on IMSDB
    print("Accessing scripts list page...")
    page = requests.get(config.URL_IMSDB + "/all scripts")

    if page.status_code != 200:
        print("Error while accessing the page.")
        return []
    else:
        # Use BeautifulSoup to parse raw HTML
        print("Parsing HTML...")
        soup = BeautifulSoup(page.content, "html.parser")
        
        # Find elements that contain information about a movie
        paragraphs = [i.find_parent("p") for i in soup.select("i")]

        # Extract basic data for each movie
        movies = []
        for p in paragraphs:
            movie = dict()
            a = p.find("a")
            movie["title"] = a.text
            movie["page"] = a["href"]
            movie["authors"] = p.find("i").text.replace("Written by ", "").split(",")
            movies.append(movie)

        return movies
    

if __name__ == "__main__":
    # Get all movie entries
    movies = get_imsdb_movies()
    print("Found", len(movies), "movies.")

    # Get data from the individual movie pages
    print("Fetching specific data for each movie...")        
    for i in range(len(movies)):
        if i % 50 == 0:
            print(i, "/", len(movies), sep="")
        add_specific_movie_data(movies[i])
    print(len(movies), "/", len(movies), sep="")

    # Output data to file
    print("Writing movie data to file...")
    output_movies_data(movies)

    print("Finished!")