
import os
import json
import csv
from datetime import datetime
from flask import Flask, request, render_template, send_file, redirect, url_for, flash
from werkzeug.utils import secure_filename
import logging

app = Flask(__name__)
app.secret_key = 'supersecretkey'
UPLOAD_FOLDER = 'uploads'
OUTPUT_FOLDER = 'output'
ALLOWED_EXTENSIONS = {'log'}

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['OUTPUT_FOLDER'] = OUTPUT_FOLDER

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(OUTPUT_FOLDER, exist_ok=True)

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def process_log_file(filepath):
    filtered_transactions = []
    with open(filepath, 'r') as file:
        for line in file:
            try:
                data = json.loads(line.strip())
                if isinstance(data, list) and data:
                    data = data[0]
                if isinstance(data, dict):
                    transactions = (
                        data.get('data', {}).get('pending', {}).get('transactions', []) +
                        data.get('data', {}).get('history', {}).get('transactions', [])
                    )
                    for transaction in transactions:
                        if transaction.get("transaction_status") not in ["CANCELLED", "DEPOSITED"]:
                            filtered_transaction = {
                                "amount": transaction['amount']['value'],
                                "email": transaction.get("recipient", {}).get("email"),
                                "reference_number": transaction.get("reference_number")
                            }
                            if filtered_transaction:
                                filtered_transactions.append(filtered_transaction)
            except json.JSONDecodeError:
                logging.warning(f"Skipping line due to JSON error: {line}")
    return filtered_transactions

@app.route("/", methods=['GET', 'POST'])
def upload_file():
    if request.method == 'POST':
        if 'file' not in request.files:
            flash('No file part')
            return redirect(request.url)
        file = request.files['file']
        if file.filename == '':
            flash('No selected file')
            return redirect(request.url)
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(filepath)
            
            transactions = process_log_file(filepath)
            output_csv = os.path.join(app.config['OUTPUT_FOLDER'], f'filtered_transactions_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv')
            
            with open(output_csv, 'w', newline='') as csvfile:
                writer = csv.DictWriter(csvfile, fieldnames=["amount", "email", "reference_number"])
                writer.writeheader()
                writer.writerows(transactions)
            
            return render_template("display.html", transactions=transactions, csv_file=output_csv)

    return render_template("upload.html")

@app.route("/download/<path:filename>")
def download_file(filename):
    return send_file(filename, as_attachment=True)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
