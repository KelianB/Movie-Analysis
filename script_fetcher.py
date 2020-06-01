import config
from bs4 import BeautifulSoup
import requests

# The length threshold under which a movie script is discarded because we probably did not
# successfully retrieve the script from the HTML page
DISCARD_LENGTH_THRESHOLD = 10000

""" Get the raw script for a given movie. """
def get_raw_script(movie):
    url = config.URL_IMSDB + movie["script_page"]

    # Only HTML movie scripts are supported
    if url[-5:].lower() == ".html":
        page = requests.get(url)
        soup = BeautifulSoup(page.content, "html.parser")

        # Get the <pre> tag which contains the script
        pre_tag = soup.select("td.scrtext pre")

        container = pre_tag[0] if len(pre_tag) > 0 else soup.select("td.scrtext")[0]

        raw_content = str(container.decode_contents())
        
        if len(raw_content) < DISCARD_LENGTH_THRESHOLD:
            print("HTML content is too short to be a movie script.")
            return None
        return raw_content
    else:
        return None # Format not handled (e.g. PDF)
