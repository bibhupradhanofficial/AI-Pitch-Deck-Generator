import requests
import time
import json

s = time.time()
with open("test_stream_out.txt", "w", encoding="utf-8") as f:
    def p(text):
        f.write(f"[{time.time()-s:.2f}] {text}\n")
        f.flush()

    p("Connecting...")
    try:
        r = requests.post("http://127.0.0.1:8080/generate", 
            json={"idea": "a startup that provides AI-driven personal finance advice", "tone": "professional"}, stream=True, timeout=60)

        for line in r.iter_lines():
            if line:
                p(line.decode('utf-8'))
    except Exception as e:
        p(f"Request failed: {e}")
    p("Done!")
