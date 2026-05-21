import re


def clean_text(text: str) -> str:
    """
    Clean extracted PDF/DOCX text before chunking.

    This removes:
    - repeated dotted leaders like ............
    - repeated new lines \n
    - excessive spaces
    - page/footer noise
    - broken hyphenated words
    """

    if not text:
        return ""

    # Remove null characters
    text = text.replace("\x00", " ")

    # Fix common encoding issue
    text = text.replace("�", "-")

    # Normalize different newline types
    text = text.replace("\r\n", "\n")
    text = text.replace("\r", "\n")

    # Join broken words caused by PDF line breaks
    # Example: green-\nhouse -> greenhouse
    text = re.sub(r"(\w)-\n(\w)", r"\1\2", text)

    # Replace all newlines with space
    text = re.sub(r"\n+", " ", text)

    # Remove dotted leaders from table of contents
    # Example: Foreword....................v -> Foreword v
    text = re.sub(r"\.{4,}", " ", text)

    # Remove spaced dotted leaders
    # Example: . . . . . . . . .
    text = re.sub(r"(?:\s*\.\s*){4,}", " ", text)

    # Remove long repeated dash/underscore lines
    text = re.sub(r"[-_]{4,}", " ", text)

    # Remove repeated bullet-like symbols
    text = re.sub(r"[•·▪●]{2,}", " ", text)

    # Remove repeated copyright/page footer noise if present
    text = re.sub(r"©\s*ISO\s*2018\s*[-–—]?\s*All rights reserved", " ", text, flags=re.IGNORECASE)

    # Remove excessive spaces
    text = re.sub(r"[ \t]+", " ", text)

    # Remove space before punctuation
    text = re.sub(r"\s+([.,;:!?])", r"\1", text)

    # Remove repeated punctuation, but keep normal full stops
    text = re.sub(r"\.{2,}", ".", text)

    return text.strip()