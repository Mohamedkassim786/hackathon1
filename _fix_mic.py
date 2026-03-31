with open("app.py", "r", encoding="utf-8") as f:
    content = f.read()

# The old startListening doesn't have the guard or manualStop logic,
# and stopListening doesn't call stopListeningUI.
# We replace the exact block between the closing brace of buildRec and the onclick handler.

old = """  function startListening(){{
    if(listening) return; // guard: already on
    try {{
      recognition = buildRec();
      recognition.start();
      listening = true;
      document.getElementById('micBtn').classList.add('listening');
      document.getElementById('micBtn').innerText = '\U0001f534';
      document.getElementById('micLabel').innerText = 'LISTENING\u2026';
      document.getElementById('micStatus').innerText = 'Speak now \u2014 stops on silence';
    }} catch(e) {{
      document.getElementById('micStatus').innerText = 'Could not start mic: ' + e.message;
    }}
  }}

  function stopListening(){{
    listening = false;
    document.getElementById('micBtn').classList.remove('listening');
    document.getElementById('micBtn').innerText = '\U0001f399\ufe0f';
    document.getElementById('micLabel').innerText = 'TAP TO SPEAK';
  }}"""

new = """  function startListening(){{
    if(listening) return; // guard: already on
    try {{
      manualStop = false;
      recognition = buildRec();
      recognition.start();
      listening = true;
      document.getElementById('micBtn').classList.add('listening');
      document.getElementById('micBtn').innerText = '\U0001f534';
      document.getElementById('micLabel').innerText = 'LISTENING\u2026';
      document.getElementById('micStatus').innerText = 'Speak now \u2014 always listening';
    }} catch(e) {{
      document.getElementById('micStatus').innerText = 'Mic error: ' + e.message;
    }}
  }}

  // Reset visual state only
  function stopListeningUI(){{
    listening = false;
    document.getElementById('micBtn').classList.remove('listening');
    document.getElementById('micBtn').innerText = '\U0001f399\ufe0f';
    document.getElementById('micLabel').innerText = 'TAP TO SPEAK';
  }}

  // Full manual stop (prevents onend from restarting)
  function stopListening(){{
    manualStop = true;
    try{{ if(recognition) recognition.stop(); }}catch(e){{}}
    stopListeningUI();
  }}"""

if old in content:
    content = content.replace(old, new, 1)
    print("Replacement applied successfully")
else:
    # Try with the version that doesn't have the guard comment
    old2 = """  function startListening(){{
    try {{
      recognition = buildRec();
      recognition.start();
      listening = true;
      document.getElementById('micBtn').classList.add('listening');
      document.getElementById('micBtn').innerText = '\U0001f534';
      document.getElementById('micLabel').innerText = 'LISTENING\u2026';
      document.getElementById('micStatus').innerText = 'Speak now \u2014 stops on silence';
    }} catch(e) {{
      document.getElementById('micStatus').innerText = 'Could not start mic: ' + e.message;
    }}
  }}

  function stopListening(){{
    listening = false;
    document.getElementById('micBtn').classList.remove('listening');
    document.getElementById('micBtn').innerText = '\U0001f399\ufe0f';
    document.getElementById('micLabel').innerText = 'TAP TO SPEAK';
  }}"""
    if old2 in content:
        content = content.replace(old2, new, 1)
        print("Replacement (v2) applied successfully")
    else:
        print("ERROR: Could not find target block.")
        # Print the lines around startListening for debugging
        lines = content.split('\n')
        for i, l in enumerate(lines):
            if 'startListening' in l and 'function' in l:
                print(f"Line {i+1}: {repr(l)}")

with open("app.py", "w", encoding="utf-8") as f:
    f.write(content)

# Verify syntax
import ast
try:
    ast.parse(content)
    print("Syntax: OK")
except SyntaxError as e:
    print(f"Syntax ERROR: {e}")
