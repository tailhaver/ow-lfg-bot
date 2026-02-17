from rich.console import Console
from rich.highlighter import NullHighlighter

console = Console(highlighter=NullHighlighter())

def print(*args, **kwargs):
    return console.print(*args, **kwargs)