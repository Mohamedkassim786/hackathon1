import requests
try:
    response = requests.post("http://localhost:11434/api/generate", json={"model": "llama3", "prompt": "Hi", "stream": False})
    if response.status_code == 200:
        print("SUCCESS: Ollama llama3 is responding.")
    else:
        print(f"FAILURE: Ollama returned status code {response.status_code}")
except Exception as e:
    print(f"FAILURE: Could not connect to Ollama: {e}")
