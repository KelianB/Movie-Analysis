import csv
import re
import json

import config
import utils
import script_fetcher

# Entry types
TYPE_META = "META"
TYPE_CHARACTER = "CHARACTER"
TYPE_SPEECH = "SPEECH"
TYPE_DIRECTION = "DIRECTION"
TYPE_LOCATION = "LOCATION"

# Pre-compiled regular expressions
exp_location = re.compile("INT\.|EXT\.|INT |EXT |INT:|EXT:|INTERIOR|EXTERIOR|EXT/INT|INT/EXT|I/E|INSIDE|OUTSIDE| ROOM")
exp_location_2 = re.compile("^\s*[0-9]+[A-Z]{0,1}\s*[A-Z]+")
exp_direction = re.compile("FADE |FADES |THE END|- END |- THE END |CREDITS|END CREDITS|CUT TO|CUT BACK TO|(\()*CONTINUED|\(MORE\)|TITLE |\(INTERCUT\)|ANGLE|CLOSE ON |CLOSE UP| SHOT|THEIR POV|\'S POV|WIDER ON|WIDE ON|CLOSER ON|CLOSE ON|RESUME ON|^\s*ON | VIEW|LATER| SHOTS|DISSOLVE|SUPER:|IN THE |UNDER THE |OVER THE |BACK ON |UP ON |FROM |CLOSEUP|CAMERA|IMAGE:")
exp_direction_continued = re.compile("^(\s)*[0-9    ]*(\s)*(\()*CONTINUED")

exp_number_period = re.compile("^(\s|\n)*[0-9]+\.(\s|\n)*$")
exp_character_colon_speech = re.compile("^[\t ]*[0-9A-Z\- l]+(?=\: [a-zA-Z!() ]+)")

# Example match: "FADE TO:"
exp_direction_colon_ending = re.compile("\:\s*$")

# Example match: "SUDDENLY."
exp_direction_period_ending = re.compile("\.\s*$")

# Example match: "  45 \n "
exp_numeric_only = re.compile("^\s*[0-9]+\s*$")

# Example match: "(PEEKS INSIDE)"
exp_parenthesis_caps = re.compile("^(\s|\n)*\([A-Z 0-9`]+\)(\s|\n)*$") 

exp_has_alphanumeric = re.compile(r"[0-9A-Za-z]")

character_cleanup_pattern_1 = r"\s*(\(V\.O\.\)|\(VO\)|\(V/O\)|\(O.S.\)|\(OS\)|\(O/S\)|\(O\.C\.\)|\(OC\)|\(CONT'D\)|\(CONT\)|\(CONT\.\)|\(CONT'D.\)|\(CONT 'D.\)|(OFF))"
character_cleanup_pattern_2 = r" --"


""" Clean-up a raw entry before classification. """
def basic_cleanup(l):
    # Delete some tokens
    delete_tokens = ["<b>", "</b>", "<pre>", "</pre>", "<html>", "</html>"]
    for x in delete_tokens:
        l = l.replace(x, "")
    # Strip
    l = l.strip()
    # Remove multi-spaces
    l = re.sub(r"[\t ]+", " ", l)
    return l


class MovieScript:
    def __init__(self, movie_info):
        self.entries = []
        self.info = movie_info
        self.character_names = []
        self.meta_finished =  False


    def classify_entry_type(self, raw, is_bold):
        is_first = len(self.entries) == 0

        entry_type = TYPE_DIRECTION

        # Handle lines like "64." or "12"
        if exp_number_period.search(raw) != None or exp_numeric_only.search(raw) != None:
            entry_type = TYPE_DIRECTION
        else:
            # Lines that are for sure a LOCATION
            if is_bold and (exp_location.search(raw) != None or exp_location_2.search(raw) != None):
                entry_type = TYPE_LOCATION
                self.meta_finished = True
            # Lines that are for sure a DIRECTION
            elif exp_direction.search(raw) != None:
                entry_type = TYPE_DIRECTION
                self.meta_finished = True
            # Handle movies where dialogue is written as CHARACTER: Speech
            elif exp_character_colon_speech.search(raw) != None:
                match = exp_character_colon_speech.search(raw)
                character_name = match.group().strip()
                character_name = character_name.replace("l", "I") # fix a scan error that often occurs
                self.entries.append({"type": TYPE_CHARACTER, "content": character_name})
                entry_type = TYPE_SPEECH
                raw = raw[match.end()+1:]
            elif is_bold:
                if exp_direction_continued.search(raw) != None or exp_direction_colon_ending.search(raw) != None or exp_direction_period_ending.search(raw) != None:
                    entry_type = TYPE_DIRECTION
                # After a CHARACTER entry, there should be a SPEECH entry
                elif (not is_first) and self.entries[-1]["type"] == TYPE_CHARACTER:
                    entry_type == TYPE_SPEECH
                # Very likely to be a speech
                elif "!" in raw or raw.strip().count(" ") >= 4:
                    entry_type = TYPE_SPEECH
                elif exp_parenthesis_caps.search(raw) != None:
                    if (not is_first) and self.entries[-1]["type"] in [TYPE_CHARACTER, TYPE_SPEECH]:
                        entry_type = TYPE_SPEECH # action like "(SCANS FILE)"
                    else:
                        entry_type = TYPE_DIRECTION # direction like "(INTO COMM)" or "(TO <name>)"
                else:
                    entry_type = TYPE_CHARACTER
            else:
                # Check again for LOCATION, this time on non-bold
                if exp_location.search(raw) != None:
                    entry_type = TYPE_LOCATION
                    self.meta_finished = True
                # Flag instructions such as "PAN TO:" as DIRECTION
                elif exp_direction_colon_ending.search(raw) != None:
                    entry_type = TYPE_DIRECTION
                elif (not is_first) and self.entries[-1]["type"] in [TYPE_CHARACTER, TYPE_SPEECH]:
                    entry_type = TYPE_SPEECH

        if not self.meta_finished:
            entry_type = TYPE_META                

        return entry_type, raw


    def add_entry(self, raw, is_bold):
        entry = dict()
        entry_type, raw = self.classify_entry_type(raw, is_bold)

        # Correct the previous entry
        if len(self.entries) > 0:
            if self.entries[-1]["type"] == TYPE_CHARACTER and entry_type != TYPE_SPEECH:
                self.entries[-1]["type"] = TYPE_DIRECTION

        entry["type"] = entry_type
        entry["content"] = basic_cleanup(raw)

        if entry_type == TYPE_CHARACTER:
            entry["content"] = self.cleanup_character_name(entry["content"])            

        if len(entry["content"]) > 0 and exp_has_alphanumeric.search(entry["content"]) != None:
            self.entries.append(entry)


    def cleanup_character_name(self, name):
        name = re.sub(character_cleanup_pattern_1, "", name)
        name = re.sub(character_cleanup_pattern_2, "", name)
        name = name.strip()

        return name


    def fix_character_scan_errors(self, character_dict):
        for e in self.entries:
            if e["type"] == TYPE_CHARACTER:
                e["content"] = utils.fix_scan_errors(e["content"], character_dict)


    def create_character_occurrence_dict(self):
        character_dict = dict()
        for e in self.entries:
            if e["type"] == TYPE_CHARACTER:
                name = e["content"]
                if not(name in character_dict):
                    character_dict[name] = 0
                character_dict[name] += 1  
        return character_dict


    def finalize(self):
        # Create a dictionary of name:occurrences for characters
        character_dict = self.create_character_occurrence_dict()

        # Clean-up characters

        # Fix false negatives: non-bold character names
        for i,e in enumerate(self.entries):
            if e["type"] in [TYPE_SPEECH, TYPE_DIRECTION]:
                text = e["content"]
                
                # TODO re-insert in speech
                text = re.sub("\s*\(([a-zA-Z]|\s)+\)", "", text, count=1)
                
                lines = text.split("\n")

                for name in character_dict:
                    if name == lines[0]:
                        e["type"] = TYPE_CHARACTER
                        e["content"] = name
                        
                        if len(lines) > 1:
                            speech_entry = dict()
                            speech_entry["type"] = TYPE_SPEECH
                            speech_entry["content"] = " ".join(lines[1:])
                            self.entries.insert(i+1, speech_entry)
                        break

        self.fix_character_scan_errors(character_dict)

        # Update character occurrence dict
        character_dict = self.create_character_occurrence_dict()
        print("Cleaned-up character occurrences:", character_dict, sep="\n")
        
        # If a SPEECH entry does not follow a CHARACTER, it is actually a DIRECTION.
        for i in range(1, len(self.entries)):
            if self.entries[i]["type"] == TYPE_SPEECH and self.entries[i-1]["type"] != TYPE_CHARACTER:
                self.entries[i]["type"] = TYPE_DIRECTION
        
        # Get rid of \n within entries
        for e in self.entries:
            e["content"] = e["content"].replace("\n", "")

        # Store character names
        for e in self.entries:
            if e["type"] == TYPE_CHARACTER:
                name = e["content"]
                if not(name in self.character_names):
                    self.character_names.append(name)

    def print(self):
        #print(*self.entries, sep="\n")
        print("(" + str(len(self.entries)) + " entries).")
        num_entries = dict()
        for e in self.entries:
            if not(e["type"] in num_entries):
                num_entries[e["type"]] = 0
            num_entries[e["type"]] += 1
        print("Entry breakdown:", num_entries)
    

def parse_script(movie, raw_script):
    movie_script = MovieScript(movie)
    text = raw_script
    text = re.sub("\r", "", text)
    text = re.sub("<br>", "\n", text)
    text = re.sub("<br/>", "\n", text)
    
    # Remove spaces before a </b>
    text = re.sub("(?<=[^ ])( +)(?=</b>)", "", text)

    # Extract \n from <b> tags when there is no other content inside
    text = re.sub("<b>( *)\n(?=(\s|\n)*</b>)", "\n<b>", text)
    text = re.sub("<b>( *)\n(?=(\s|\n)*</b>)", "\n<b>", text)
    text = re.sub("<b>( *)\n(?=(\s|\n)*</b>)", "\n<b>", text)
    text = re.sub("<b>( *)\n(?=(\s|\n)*</b>)", "\n<b>", text)

    # Remove empty <b> tags
    text = re.sub("<b>(\s)*</b>", "", text)
    
    # Remove spaces between consecutive line breaks
    text = re.sub(r"\n( *)\n", r"\n\n", text)

    exp_bold = re.compile(r"(?<=(<b>))(.|\n|\s)*?(?=(</b>))")
    exp_until_bold = re.compile(r"(.|\n|\s)*?(?=<b>|$)")
    
    # Parse content
    while True:
        match = exp_until_bold.search(text)
        
        if len(match.group()) > 0:
            raw_entries = match.group().split("\n\n")
            for raw_e in raw_entries:
                movie_script.add_entry(raw_e, False)
            text = text[match.end():]
        else:
            bold_match = exp_bold.search(text)
            
            if bold_match == None and len(match.group()) == 0:
                break

            if bold_match != None:
                text = text[bold_match.end() + 4:]
                movie_script.add_entry(bold_match.group(), True)

    movie_script.finalize()    
    
    return movie_script
    
""" Computes parsed data for the given movie. """
def parse_movie(movie):
    raw_script = script_fetcher.get_raw_script(movie)
    return None if raw_script == None else parse_script(movie, raw_script)

