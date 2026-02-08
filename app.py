import os
import re
import pandas as pd
from flask import Flask, request, send_file, jsonify
from flask_cors import CORS
import zipfile
from io import BytesIO

app = Flask(__name__)

# UPDATED: Explicitly allow the React origin
CORS(app, resources={r"/*": {"origins": "*"}})

def classify_operator(mobile):
    mobile = str(mobile).strip().split('.')[0]
    ntc_regex = r"9[78][456][0-9]{7}"
    ncell_regex1 = r"98[012][0-9]{7}"
    ncell_regex2 = r"97[01][0-9]{7}"
    sc_regex1 = r"96[12][0-9]{7}"
    sc_regex2 = r"988[0-9]{7}"

    if re.fullmatch(ntc_regex, mobile):
        return "NTC"
    elif re.fullmatch(ncell_regex1, mobile) or re.fullmatch(ncell_regex2, mobile):
        return "NCELL"
    elif re.fullmatch(sc_regex1, mobile) or re.fullmatch(sc_regex2, mobile):
        return "SMARTCELL"
    else:
        return "OTHER"

@app.route('/process-excel', methods=['POST'])
def process_excel():
    if 'file' not in request.files:
        return jsonify({"error": "No file uploaded"}), 400

    file = request.files['file']
    phone_col = request.form.get('column_name', 'Mobile')

    try:
        df = pd.read_excel(file)
        df.columns = df.columns.astype(str).str.strip()

        if phone_col not in df.columns:
            return jsonify({"error": f"Column '{phone_col}' not found."}), 400

        df['Operator'] = df[phone_col].apply(classify_operator)

        memory_file = BytesIO()
        with zipfile.ZipFile(memory_file, 'w') as zf:
            for op in ['NTC', 'NCELL', 'SMARTCELL', 'OTHER']:
                subset = df[df['Operator'] == op].drop(columns=['Operator'])
                if not subset.empty:
                    output = BytesIO()
                    subset.to_excel(output, index=False)
                    zf.writestr(f"{op.lower()}_numbers.xlsx", output.getvalue())

        memory_file.seek(0)
        return send_file(memory_file, mimetype='application/zip', as_attachment=True, download_name='split_numbers.zip')

    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    # UPDATED: Changed port to 5001 to avoid AirPlay conflict
    app.run(host='0.0.0.0', port=5001, debug=True)
