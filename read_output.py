
with open('bz_debug_output.txt', 'rb') as f:
    content = f.read()
    # Try different encodings
    for encoding in ['utf-8', 'utf-16', 'utf-16-le', 'cp1252']:
        try:
           decoded = content.decode(encoding)
           print(f"--- Decoded with {encoding} ---")
           print(decoded[:2000])
           break
        except:
           pass
