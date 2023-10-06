import re
import html
import numpy as np
import pandas as pd
import spacy    
from spacy.tokens import Token, Span

EMOJI_PATTERN = re.compile(
    "(["
    "\U0001F1E0-\U0001F1FF"  # flags (iOS)
    "\U0001F300-\U0001F5FF"  # symbols & pictographs
    "\U0001F600-\U0001F64F"  # emoticons
    "\U0001F680-\U0001F6FF"  # transport & map symbols
    "\U0001F700-\U0001F77F"  # alchemical symbols
    "\U0001F780-\U0001F7FF"  # Geometric Shapes Extended
    "\U0001F800-\U0001F8FF"  # Supplemental Arrows-C
    "\U0001F900-\U0001F9FF"  # Supplemental Symbols and Pictographs
    "\U0001FA00-\U0001FA6F"  # Chess Symbols
    "\U0001FA70-\U0001FAFF"  # Symbols and Pictographs Extended-A
    "\U00002702-\U000027B0"  # Dingbats
    "])"
)

EMOTICON_PATTERN = re.compile("<a:[^:]+:\d+>")

url_regex_string = r"(?:https?://|www\.)[^\s]+"
url_regex = re.compile(url_regex_string)

def replace_empty_strings(text):
    # Replace empty strings with NaN
    if not text or text.isspace():
        return np.nan
    else:
        return text

def clean_content(text):
    """
    Given a string of content, split it into lines, strip leading and trailing whitespace from each line,
    remove any blank lines, and return the resulting lines as a single string joined by newline characters.
    """
    if isinstance(text, str):
        lines = [line.strip() for line in text.split("\n") if line.strip()]
        cleaned_string = "\n".join(lines)
        return cleaned_string

def strip_emojis(text):
    # Remove all Unicode emojis from the text
    text = EMOJI_PATTERN.sub(r'', text)
    return EMOTICON_PATTERN.sub(r'', text)

def strip_emoticons(text):
    # Define the regular expression to match emoticons
    emoticon_pattern = r':\w+:'
    # Use the re.sub() function to replace emoticons with an empty string
    stripped_text = re.sub(emoticon_pattern, '', text)
    # Return the stripped text
    return stripped_text

def prepare(text, pipeline):
    # Return np.nan if text is NaN
    if isinstance(text, float) and np.isnan(text):
        return np.nan
    
    # Apply the functions in the pipeline to the text
    for function in pipeline:
        text = function(text)
    
    return text

def clean(text):
    # convert html escapes like &amp; to characters.
    text = html.unescape(text) 
    # tags like <tab>
    text = re.sub(r'<[^<>]*>', ' ', text)
    # markdown URLs like [Some text](https://....)
    text = re.sub(r'\[([^\[\]]*)\]\([^\(\)]*\)', r'\1', text)
    # text or code in brackets like [0]
    text = re.sub(r'\[[^\[\]]*\]', ' ', text)
    # standalone sequences of specials, matches &# but not #cool
    text = re.sub(r'(?:^|\s)[&#<>{}\[\]+|\\:-]{1,}(?:\s|$)', ' ', text)
    # standalone sequences of hyphens like --- or ==
    text = re.sub(r'(?:^|\s)[\-=\+]{2,}(?:\s|$)', ' ', text)
    # sequences of white spaces
    text = re.sub(r'\s+', ' ', text)
    return text.strip()
    

def display_nlp(doc, include_punct=False):
    """Generate data frame for visualization of spaCy tokens."""
    rows = []
    for i, t in enumerate(doc):
        if not t.is_punct or include_punct:
            row = {'token': i,  'text': t.text, 'lemma_': t.lemma_, 
                   'is_stop': t.is_stop, 'is_alpha': t.is_alpha,
                   'pos_': t.pos_, 'dep_': t.dep_, 
                   'ent_type_': t.ent_type_, 'ent_iob_': t.ent_iob_}
            rows.append(row)
    
    df = pd.DataFrame(rows).set_index('token')
    df.index.name = None
    return df