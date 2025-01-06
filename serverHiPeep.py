import json
import os
import pprint

from flask import Flask, request, jsonify, send_file, render_template
from sandboxServerFunctions import *

app = Flask(__name__)


@app.route('/')
def home():
    return render_template('client.html')


# Configure the upload folder
UPLOAD_FOLDER = 'C:/Users/Vivek Reddy Gunna/adsServer/ServerCode/adFiles/'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

SERVER_IP = '127.0.0.1'  # Loopback address for local testing
SERVER_PORT = 5004
BUFFER_SIZE = 4096
IMAGE_FOLDER = 'adFiles/'  # Folder containing images to send
SENDING_INTERVAL = 30  # Interval between sending images (3 minutes = 180 seconds)


@app.route('/submit', methods=['POST', 'GET'])
def preview():
    file = request.files['adName']  # Access the file by its name in the form

    if file:
        filename = file.filename
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(file_path)

        logDict = {"user": request.form['client'],
                   "fromDates": json.loads(request.form['fromDate']),
                   "fromTimes": json.loads(request.form['fromTime']),
                   "toDates": json.loads(request.form['toDate']),
                   "toTimes": json.loads(request.form['toTime']),
                   "center": request.form['center'],
                   "radius": request.form['radius'],
                   "runTime": request.form['run_time'],
                   "email": request.form['email'],
                   "fileUploaded": file_path}

        k = save_adOrders_to_db(logDict)
        logDict['UniqueID'] = k
        pprint.pprint(logDict)
        return "success"
    else:
        return 'No file uploaded'


@app.route('/endpoint', methods=['POST'])
def handle_request():
    """
    Endpoint to handle JSON file uploads and send responses.
    """
    if 'file' not in request.files:
        return jsonify({"error": "No file part in the request"}), 400

    file = request.files['file']

    if file.mimetype != 'application/json':
        return jsonify({"error": "Uploaded file is not a JSON file"}), 400

    try:
        json_data = json.loads(file.read().decode('utf-8'))
        print("Received Client JSON data :", json_data['adId'])
    except json.JSONDecodeError:
        return jsonify({"error": "Invalid JSON file"}), 400

    # update sql database table "adsInQueue" with left over runtimes
    update_sql('mooh.db', 'adOrders', 'adId', int(json_data['adId']), 'runTime', json_data['runTime'])

    # update sql database table "tracker_log" with routes(list of (lat,long))
    conn = sqlite3.connect('mooh.db')
    cursor = conn.cursor()
    cursor.execute('''INSERT INTO trackerLog (carId, adId, locs, times) VALUES (?, ?, ?, ?)''',
                   (json_data['carId'], json_data['adId'], json_data['locs'], json_data['times']))
    conn.commit()
    conn.close()

    adToSend = validAdToRun(json_data['currentLocation'])
    print("sent Ad JSON data :", adToSend)

    if adToSend:
        # Embed image as base64 string in the JSON response
        image_base64 = encode_image_to_base64(adToSend['fileUploaded'])
        adToSend.update({
            "message": "Ad sent",
            "status": "success",
            "center": list(map(float, list(adToSend['center'].split(',')))),
            "runTime": int(adToSend["runTime"]),
            "radius": int(adToSend["radius"]),
            "image": image_base64})
        # update sql database table "adsInQueue" with left over runtimes
        update_sql('mooh.db', 'adOrders', 'adId', int(adToSend['adId']), 'runTime', 0)

        return jsonify(adToSend)
    else:
        # Embed image as base64 string in the JSON response
        # image_base64 = encode_image_to_base64(f'C:/Users/Vivek Reddy Gunna/adsServer/ServerCode/meme.jpg')
        image_base64 = encode_image_to_base64(pick_random_memejpg("C:/Users/Vivek Reddy Gunna/adsServer/"
                                                                  "ServerCode/memeFiles"))
        return jsonify({
            "message": "Meme Sent",
            "status": "success",
            "center": json_data['currentLocation'],
            "runTime": 100,
            "radius": 600,
            "adId": 0,
            "image": image_base64})


if __name__ == '__main__':
    # app.run(port=5004)
    app.run(host='192.168.0.157', port=5004)
