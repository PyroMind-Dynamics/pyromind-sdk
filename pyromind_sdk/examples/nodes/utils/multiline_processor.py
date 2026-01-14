"""
Multiline text processing function example
Processes multiline input text, performs statistics and formatting
"""


def process_multiline_text(text: str) -> dict:
    """
    Process multiline text input
    
    Args:
        text: Multiline text string
        
    Returns:
        Dictionary containing processing results:
        - line_count: Number of lines
        - word_count: Number of words
        - char_count: Number of characters
        - processed_text: Processed text (line numbers added to each line)
    """
    lines = text.strip().split('\n')
    line_count = len(lines)
    
    # Count words (split by spaces)
    words = text.split()
    word_count = len(words)
    
    # Count characters
    char_count = len(text)
    
    # Processed text: add line numbers to each line
    processed_lines = []
    for i, line in enumerate(lines, 1):
        processed_lines.append(f"{i:3d}: {line}")
    processed_text = '\n'.join(processed_lines)
    
    return {
        "line_count": line_count,
        "word_count": word_count,
        "char_count": char_count,
        "processed_text": processed_text
    }

