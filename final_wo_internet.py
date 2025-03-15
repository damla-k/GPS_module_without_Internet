from flask import Flask, request, jsonify, render_template_string, send_file
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import os
import serial
import requests
import threading
import json

app = Flask(__name__)

# Database configuration
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///gps_data.db'  # SQLite database file
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# Define the GPS data model
class GPSData(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    timestamp = db.Column(db.String(20), nullable=False)
    latitude = db.Column(db.Float, nullable=False)
    longitude = db.Column(db.Float, nullable=False)
    altitude = db.Column(db.Float, nullable=False)
    speed = db.Column(db.Float, nullable=False)
    satellites = db.Column(db.Integer, nullable=False)

# Create the database and tables (run this once)
with app.app_context():
    db.create_all()

# Function to save GPS data as an HTML file
def save_gps_data():
    try:
        # Fetch all GPS data from the database
        gps_data = GPSData.query.all()

        html_content = '''
        <!DOCTYPE html>
        <html>
        <head>
            <title>GPS Data Export</title>
        </head>
        <body>
            <h1>GPS Data History</h1>
            <table border="1">
                <tr>
                    <th>Timestamp</th>
                    <th>Latitude</th>
                    <th>Longitude</th>
                    <th>Altitude</th>
                    <th>Speed</th>
                    <th>Satellites</th>
                </tr>
        '''

        for entry in gps_data:
            html_content += f'''
                <tr>
                    <td>{entry.timestamp}</td>
                    <td>\t"{entry.latitude}"</td>
                    <td>\t"{entry.longitude}"</td>
                    <td>\t"{entry.altitude}"</td>
                    <td>\t"{entry.speed}"</td>
                    <td>\t"{entry.satellites}"</td>
                </tr>
            '''

        html_content += '''
            </table>
        </body>
        </html>
        '''

        # Save the HTML content to a file
        file_path = 'gps_data_export.html'
        with open(file_path, 'w') as f:
            f.write(html_content)
    except Exception as e:
        print(f"Error saving file: {e}")

@app.route('/update', methods=['POST'])
def update():
    try:
        data = request.get_json()  # Parse JSON data
        print("Received data:", data)  # Debug: Print received data

        if not data:
            return "Invalid JSON data", 400

        # Validate required fields
        required_fields = ["latitude", "longitude", "altitude", "speed", "satellites"]
        if not all(key in data for key in required_fields):
            print("Missing data in request:", data)  # Debug: Print missing fields
            return "Missing data in request", 400

        # Add a timestamp to the GPS data
        data["timestamp"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # Save the GPS data to the database
        new_entry = GPSData(
            timestamp=data["timestamp"],
            latitude=data["latitude"],
            longitude=data["longitude"],
            altitude=data["altitude"],
            speed=data["speed"],
            satellites=data["satellites"]
        )
        db.session.add(new_entry)
        db.session.commit()

        # Save the GPS data as an HTML file
        save_gps_data()

        return "Data updated", 200
    except Exception as e:
        print("Error processing request:", e)  # Debug: Print exception
        return f"Error processing request: {e}", 500

@app.route('/history', methods=['GET'])
def history():
    # Fetch all GPS data from the database
    gps_data = GPSData.query.all()
    # Convert the data to a list of dictionaries
    history_data = [{
        "timestamp": entry.timestamp,
        "latitude": entry.latitude,
        "longitude": entry.longitude,
        "altitude": entry.altitude,
        "speed": entry.speed,
        "satellites": entry.satellites
    } for entry in gps_data]
    return jsonify(history_data)

@app.route('/download', methods=['GET'])
def download():
    # Provide the file for download
    return send_file('gps_data_export.html', as_attachment=True)

@app.route('/')
def index():
    # Serve an HTML page with JavaScript for dynamic updates
    return render_template_string('''
        <!DOCTYPE html>
        <html>
        <head>
            <title>ESP32 GPS Data</title>
            <style>
                table {
                    width: 100%;
                    border-collapse: collapse;
                }
                table, th, td {
                    border: 1px solid black;
                }
                th, td {
                    padding: 8px;
                    text-align: left;
                }
                th {
                    background-color: #f2f2f2;
                }
            </style>
            <script>
                function fetchData() {
                    fetch('/history')
                        .then(response => response.json())
                        .then(data => {
                            const tableBody = document.getElementById('gpsTableBody');
                            tableBody.innerHTML = ''; // Clear existing rows

                            data.forEach(entry => {
                                const row = document.createElement('tr');
                                row.innerHTML = `
                                    <td>${entry.timestamp || 'N/A'}</td>
                                    <td>${entry.latitude || 'N/A'}</td>
                                    <td>${entry.longitude || 'N/A'}</td>
                                    <td>${entry.altitude || 'N/A'}</td>
                                    <td>${entry.speed || 'N/A'}</td>
                                    <td>${entry.satellites || 'N/A'}</td>
                                `;
                                tableBody.appendChild(row);
                            });
                        })
                        .catch(error => console.error('Error fetching data:', error));
                }

                // Fetch data every 5 seconds
                setInterval(fetchData, 1000);

                // Fetch data immediately when the page loads
                window.onload = fetchData;
            </script>
        </head>
        <body>
            <h1>ESP32 GPS Data</h1>
            <table>
                <thead>
                    <tr>
                        <th>Timestamp</th>
                        <th>Latitude</th>
                        <th>Longitude</th>
                        <th>Altitude</th>
                        <th>Speed</th>
                        <th>Satellites</th>
                    </tr>
                </thead>
                <tbody id="gpsTableBody">
                    <!-- Rows will be dynamically inserted here -->
                </tbody>
            </table>
            <br>
            <a href="/history">View History (JSON)</a>
            <br>
            <a href="/download">Download GPS Data as HTML</a>
        </body>
        </html>
    ''')

# Serial communication thread
def serial_thread():
    ser = serial.Serial('COM6', 115200, timeout=1)  #COM port is subject to change
    while True:
        if ser.in_waiting > 0:
            line = ser.readline().decode('utf-8').strip()
            print("Received raw data:", line)  # Debug: Print raw data

            try:
                # Validate JSON data
                json_data = json.loads(line)
                print("Parsed JSON data:", json_data)  # Debug: Print parsed JSON

                # Send data to Flask server
                response = requests.post('http://172.16.25.250:5000/update', json=json_data)
                print("Server response:", response.status_code)  # Debug: Print server response
            except json.JSONDecodeError as e:
                print("Invalid JSON data:", e)
            except Exception as e:
                print("Error sending data to server:", e)

# Start the serial thread
threading.Thread(target=serial_thread, daemon=True).start()

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)