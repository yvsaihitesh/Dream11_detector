from flask import Flask, request, jsonify, render_template
import re
import nbformat
import papermill as pm
import requests

app = Flask(__name__)

# Google Programmable Search Engine credentials
GOOGLE_API_KEY = "AIzaSyALS0aDRLLoY37oYdCTtTwRSlPfUSdsvxg"
CX = "b160551c2e0194012"

def get_espn_id(player_name):
    query = f"site:espncricinfo.com/cricketers {player_name}"
    url = f"https://www.googleapis.com/customsearch/v1?q={query}&key={GOOGLE_API_KEY}&cx={CX}"
    
    response = requests.get(url)
    if response.status_code != 200:
        print(f"❌ HTTP Error: {response.status_code}")
        return None

    results = response.json().get("items", [])
    for item in results:
        link = item.get("link", "")
        print(f"[DEBUG] Link: {link}")
        match = re.search(r'/cricketers/[^/]+-(\d+)', link)
        if match:
            return match.group(1)

    print("❌ No matching link found")
    return None



@app.route('/')
def index():
    return render_template('index.html')

@app.route('/submit', methods=['POST'])
def submit():
    names = request.form.get('names')
    lines = names.strip().split('\n')
    player_input = []
    errors = []

    allowed_roles = {"BAT", "BOWL", "ALL", "WK"}

    for line in lines:
        parts = line.strip().split(',')
        if len(parts) == 2:
            name, role = parts[0].strip(), parts[1].strip().upper()

            if role not in allowed_roles:
                errors.append(f"❌ Invalid role for {name}: '{role}'. Must be one of {', '.join(allowed_roles)}.")
                continue

            pid = get_espn_id(name)
            if pid:
                player_input.append({
                    "name": name,
                    "role": role,
                    "id": pid
                })
            else:
                errors.append(f"❌ Could not find ESPN ID for {name}")
        else:
            errors.append(f"❌ Invalid format: '{line}'. Expected format is: Player Name,Role")

    # 🔍 Debug: print the valid players collected
    print("\n✅ Final player_input list:")
    for player in player_input:
        print(f"- {player['name']} ({player['role']}) ➝ ID: {player['id']}")

    if not player_input:
        return jsonify({"best11": "❌ No valid players found.\n" + "\n".join(errors)})

    try:
        pm.execute_notebook(
            'CricTensors.ipynb',
            'output.ipynb',
            parameters={'user_players': player_input}
        )
    except Exception as e:
        return jsonify({"best11": f"❌ Notebook execution failed:\n{str(e)}"})

    # Extract notebook output
    nb = nbformat.read('output.ipynb', as_version=4)
    output_text = ""
    for cell in nb.cells:
        if cell.cell_type == 'code':
            for output in cell.get('outputs', []):
                if output.output_type == 'stream' and 'Best 11' in output.text:
                    output_text += output.text

    if output_text.strip():
        return jsonify({"best11": output_text.strip()})
    else:
        return jsonify({"best11": "✅ Notebook ran, but no 'Best 11' output was found.\n" + "\n".join(errors)})

if __name__ == '__main__':
    app.run(debug=True)
