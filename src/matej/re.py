import re


ANSI = re.compile(r'(?:\x1B[@-Z\\-_]|[\x80-\x9A\x9C-\x9F]|(?:\x1B\[|\x9B)[0-?]*[ -/]*[@-~])', re.IGNORECASE)
FLOAT = re.compile(r'[-+]?\d*\.?\d+([eE][-+]?\d+)?')