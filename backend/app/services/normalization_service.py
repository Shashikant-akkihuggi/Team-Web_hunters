import re
import unicodedata

class TextNormalizationError(Exception):
    pass

class EmptyDocumentError(TextNormalizationError):
    pass

def normalize_unicode(text: str) -> str:
    """Standardizes unicode characters using NFKC normalization and cleans control characters."""
    if not text:
        return ""
    # Standard NFKC normalization
    normalized = unicodedata.normalize("NFKC", text)

    # Normalize directional quotes and special apostrophes
    normalized = normalized.replace("“", '"').replace("”", '"').replace("‘", "'").replace("’", "'")
    # Normalize unicode dashes (em-dash, en-dash, minus)
    normalized = normalized.replace("—", " - ").replace("–", " - ").replace("−", "-")

    # Filter out unprintable control characters, keeping newline, carriage return, tab
    cleaned = "".join(
        ch for ch in normalized
        if ch in ("\n", "\r", "\t") or (unicodedata.category(ch)[0] != "C")
    )
    return cleaned

def normalize_whitespace(text: str) -> str:
    """
    Normalizes whitespace while strictly preserving meaningful paragraph breaks:
    - Normalizes line endings to \n
    - Strips trailing whitespace per line
    - Collapses horizontal spaces and tabs into a single space
    - Collapses 3+ consecutive newlines into 2 (preserves standard paragraph break \n\n)
    """
    if not text:
        return ""

    # Unify line endings
    text = text.replace("\r\n", "\n").replace("\r", "\n")

    # Clean line by line
    lines = text.split("\n")
    cleaned_lines = []
    for line in lines:
        # Collapse multiple inline spaces and tabs into a single space
        collapsed = re.sub(r"[ \t]+", " ", line).strip()
        cleaned_lines.append(collapsed)

    joined = "\n".join(cleaned_lines)

    # Collapse 3 or more consecutive newlines to at most 2 newlines
    normalized = re.sub(r"\n{3,}", "\n\n", joined).strip()
    return normalized

def normalize_extracted_text(raw_text: str) -> str:
    """
    Full text normalization pipeline:
    1. Unicode cleanup
    2. Whitespace and paragraph boundary normalization
    3. Checks for empty content
    """
    if not raw_text or not raw_text.strip():
        raise EmptyDocumentError("Document contains no readable text content.")

    unicode_clean = normalize_unicode(raw_text)
    normalized = normalize_whitespace(unicode_clean)

    if not normalized or len(normalized.strip()) == 0:
        raise EmptyDocumentError("Document contains only whitespace or unreadable control characters.")

    return normalized
