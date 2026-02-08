import os
import re
import pandas as pd
from flask import Flask, request, send_file, jsonify
from flask_cors import CORS
import zipfile
from io import BytesIO

app = Flask(__name__)
# Allow your specific domain
CORS(app, resources={r"/*": {"origins": "https://telesplit.yajtech.com"}})

def classify_operator(mobile):
    # Handle empty or NaN values
    if pd.isna(mobile) or str(mobile).strip() == "":
        return "OTHER"

    # Convert to string and remove .0 if it's a float
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
    # Get column name and strip any extra spaces
    phone_col = request.form.get('column_name', 'Mobile').strip()

    try:
        # engine='openpyxl' ensures it uses the right library
        df = pd.read_excel(file, engine='openpyxl')

        # Clean the column headers (remove spaces, convert to list)
        df.columns = [str(c).strip() for c in df.columns]

        if phone_col not in df.columns:
            return jsonify({
                "error": f"Column '{phone_col}' not found. Found columns: {list(df.columns)}"
            }), 400

        # Classify
        df['Operator'] = df[phone_col].apply(classify_operator)

        memory_file = BytesIO()
        with zipfile.ZipFile(memory_file, 'w') as zf:
            processed_any = False
            for op in ['NTC', 'NCELL', 'SMARTCELL', 'OTHER']:
                subset = df[df['Operator'] == op].drop(columns=['Operator'])
                if not subset.empty:
                    processed_any = True
                    output = BytesIO()
                    subset.to_excel(output, index=False)
                    zf.writestr(f"{op.lower()}_numbers.xlsx", output.getvalue())

            if not processed_any:
                return jsonify({"error": "No numbers were processed. Check your file format."}), 400

        memory_file.seek(0)
        return send_file(
            memory_file,
            mimetype='application/zip',
            as_attachment=True,
            download_name='split_numbers.zip'
        )

    except Exception as e:
        # This will return the EXACT error message to your React frontend
        print(f"Error occurred: {str(e)}")
        return jsonify({"error": f"Server Error: {str(e)}"}), 500

if __name__ == '__main__':
    # For Nginx proxy, 127.0.0.1 is best
    app.run(host='127.0.0.1', port=5001)