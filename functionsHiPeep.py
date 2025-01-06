import base64
import datetime
import json
import os
import pprint
import random

import matplotlib.pyplot as plt
from matplotlib.patches import Circle
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet
import sqlite3
import math


def fetch_row_as_dict(db_file, table_name, pk_column, pk_value):
    conn = sqlite3.connect(db_file)
    cursor = conn.cursor()

    query = f"SELECT * FROM {table_name} WHERE {pk_column} = ?"
    cursor.execute(query, (pk_value,))
    row = cursor.fetchone()
    # row = cursor.fetchall()

    if row is None:
        return None  # Handle the case where the row doesn't exist

    # Get column names directly from the cursor description
    column_names = [description[0] for description in cursor.description]

    # Create a dictionary from the row tuple
    row_dict = dict(zip(column_names, row))
    conn.close()
    return row_dict


def fetch_all_as_dict(db_file, table_name, pk_column, pk_value):
    conn = sqlite3.connect(db_file)
    cursor = conn.cursor()

    query = f"SELECT * FROM {table_name} WHERE {pk_column} = ?"
    cursor.execute(query, (pk_value,))
    all = cursor.fetchall()
    # row = cursor.fetchall()

    if all is None:
        return None  # Handle the case where the row doesn't exist

    # Get column names directly from the cursor description
    column_names = [description[0] for description in cursor.description]

    # Create a dictionary from the row tuple
    result = {}
    for i, row in enumerate(all, 1):
        row_dict = dict(zip(column_names, row))
        result[i] = row_dict

    conn.close()
    return result


def fetch_all_as_dict_with_condition(db_file, table_name, pk_column, condition, value):
    """Fetches all rows from a table based on a specified condition and returns them as a dictionary.

    Args:
        db_file: The path to the SQLite database file.
        table_name: The name of the table to query.
        pk_column: The name of the column to apply the condition to.
        condition: The comparison operator (e.g., '>', '<', '>=', '<=', '=').
        value: The value to compare against.

    Returns:
        A dictionary containing the fetched rows, where the keys are integers (row numbers) and the values are dictionaries representing each row.
        Returns None if no rows are found.
    """

    try:
        conn = sqlite3.connect(db_file)
        cursor = conn.cursor()

        query = f"SELECT * FROM {table_name} WHERE {pk_column} {condition} ?"
        cursor.execute(query, (value,))
        rows = cursor.fetchall()

        if not rows:
            return None

        # Get column names directly from the cursor description
        column_names = [description[0] for description in cursor.description]

        # Create a dictionary of dictionaries, where each inner dictionary represents a row
        result = {i: dict(zip(column_names, row)) for i, row in enumerate(rows, 1)}

        return result

    except sqlite3.Error as e:
        print(f"Error fetching data: {e}")
        return None
    finally:
        if conn:
            conn.close()


def update_sql(db_file, table_name, pk_column, pk_value, column_to_update, new_value):
    conn = sqlite3.connect(db_file)
    cursor = conn.cursor()

    query = f"UPDATE {table_name} SET {column_to_update} = ? WHERE {pk_column} = ?"
    cursor.execute(query, (new_value, pk_value))

    conn.commit()  # Commit the changes
    conn.close()
    print(f'updated the database {db_file} table {table_name} '
          f'of primary key {pk_column} of value {pk_value} in column {column_to_update} with value {new_value}\n')


def encode_image_to_base64(filepath):
    """
    Helper function to encode an image file to a base64 string.
    """
    with open(filepath, "rb") as img_file:
        return base64.b64encode(img_file.read()).decode('utf-8')


def is_within_valid_time_frames(time_frames):
    """
    Checks if the current date and time falls within any of the specified valid time frames.

    Args:
        time_frames: A dictionary containing the valid time frames in the following format:
            {
                'fromDates': ['2024-11-23', '2024-11-24', ...],
                'fromTimes': ['09:00', '09:15', ...],
                'toDates': ['2024-11-23', '2024-11-24', ...],
                'toTimes': ['21:00', '23:15', ...],
            }

    Returns:
        True if the current date and time is within a valid time frame, False otherwise.
    """

    current_datetime = datetime.datetime.now()
    current_date = current_datetime.date()
    current_time = current_datetime.time()

    for i in range(len(time_frames['fromDates'])):
        from_date = datetime.datetime.strptime(time_frames['fromDates'][i], '%Y-%m-%d').date()
        from_time = datetime.datetime.strptime(time_frames['fromTimes'][i], '%H:%M').time()
        to_date = datetime.datetime.strptime(time_frames['toDates'][i], '%Y-%m-%d').date()
        to_time = datetime.datetime.strptime(time_frames['toTimes'][i], '%H:%M').time()

        # print(f'fromDate:{from_date}, currentDate:{current_date}, toDate:{to_date}')
        # print(f'fromTime:{from_time}, currentTime:{current_time}, toTime:{to_time}')

        if (current_date >= from_date and current_time >= from_time) and \
                (current_date <= to_date and current_time <= to_time):
            return True

    return False


def validAdToRun(location):
    adsInQueue = fetch_all_as_dict_with_condition('mooh.db', 'adOrders', 'runTime', '>', 0)
    if adsInQueue:
        for items in adsInQueue:
            timeFrames = {'fromDates': json.loads(adsInQueue[items]['fromDates']),
                          'fromTimes': json.loads(adsInQueue[items]['fromTimes']),
                          'toDates': json.loads(adsInQueue[items]['toDates']),
                          'toTimes': json.loads(adsInQueue[items]['toTimes'])}

            center = tuple(map(float, list(adsInQueue[items]['center'].split(','))))
            with_in_timeFrame = is_within_valid_time_frames(timeFrames)
            with_in_radius = haversine_distance(center, location) <= int(adsInQueue[items]['radius'])
            print(adsInQueue[items]['adId'], with_in_timeFrame, with_in_radius)
            if with_in_timeFrame and with_in_radius:
                return adsInQueue[items]
        else:
            return None


def haversine_distance(coord1, coord2):
    """
    Calculate the Haversine distance between two latitude-longitude points.

    Args:
      coord1 (tuple): The (latitude, longitude) of the first point in decimal degrees.
      coord2 (tuple): The (latitude, longitude) of the second point in decimal degrees.

    Returns:
      float: Distance between the points in kilometers.
    """
    R = 6371  # Earth's radius in kilometers

    lat1, lon1 = map(math.radians, coord1)
    lat2, lon2 = map(math.radians, coord2)

    dlat = lat2 - lat1
    dlon = lon2 - lon1

    a = math.sin(dlat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

    return R * c


def calculate_distances(coords):
    """
    Calculate distances between consecutive latitude-longitude pairs.

    Args:
      coords (list of tuples): List of (latitude, longitude) tuples.

    Returns:
      list of floats: Distances in kilometers between consecutive points.
    """
    distances = []
    if len(coords) == 1:
        return 0.2
    else:
        for i in range(len(coords) - 1):
            distance = haversine_distance(coords[i], coords[i + 1])
            distances.append(round(distance, 2))
    return round(sum(distances), 2)


def route_log_by_adId(adId):
    route_logs = fetch_all_as_dict('mooh.db', 'trackerLog', 'adId', adId)
    adLog = fetch_row_as_dict('mooh.db', 'adOrders', 'adId', adId)
    poster = adLog['fileUploaded']

    log = {}

    # Process each log entry
    for items in route_logs:
        # Parse location data into a list of (x, y) tuples
        coordinates = []

        for pair in route_logs[items]['locs'].rstrip('*').split('*'):
            if pair:  # Ensure the pair is not empty
                x, y = map(float, pair.split(':'))
                coordinates.append((x, y))

        # Store data in the dictionary
        if len(coordinates) != 0:
            log[str(route_logs[items]['routeId'])] = {
                "locs": coordinates,
                "times": route_logs[items]['times'].rstrip('*').split('*'),
                "distance": calculate_distances(coordinates),
                "runtime": len(route_logs[items]['times'].rstrip('*').split('*')) * 30,
                "carId": route_logs[items]['carId']
            }

    total_distance = 0
    total_time = 0
    for items in log:
        total_distance += log[items]['distance']
        total_time += log[items]['runtime']

    return log, round(total_distance, 2), total_time, poster


def route_log_by_carId(carId):
    conn = sqlite3.connect('mooh.db')
    cursor = conn.cursor()

    # Query the database for records with the given adId
    query = "SELECT * FROM trackerLog WHERE carId = ?"
    cursor.execute(query, (carId,))
    routes_logs = cursor.fetchall()

    log = {}

    # Process each log entry
    for items in routes_logs:
        route_id, carId, adId, locs, times = items

        # Parse location data into a list of (x, y) tuples
        coordinates = []
        for pair in locs.rstrip('*').split('*'):
            if pair:  # Ensure the pair is not empty
                x, y = map(float, pair.split(':'))
                coordinates.append((x, y))

        # Store data in the dictionary
        if len(coordinates) != 0:
            log[str(route_id)] = {
                "locs": coordinates,
                "times": times.rstrip('*').split('*'),
                "distance": calculate_distances(coordinates),
                "runtime": len(times.rstrip('*').split('*')) * 30,
                "adId": adId,
                "poster": fetch_row_as_dict('mooh.db', 'adOrders', 'adId', adId)['fileUploaded']
            }

    conn.close()  # Close the database connection

    total_distance = 0
    total_time = 0
    for items in log:
        total_distance += log[items]['distance']
        total_time += log[items]['runtime']

    return log, round(total_distance, 2), total_time


def save_plot_as_image(list_of_tuples_of_xys, center, radius, file_name):
    """
    Saves the route graph as an image file with accurate rendering.
    """
    x_values, y_values = zip(*list_of_tuples_of_xys)

    # Create the figure and axis
    plt.figure()  # Start a new figure
    plt.plot(x_values, y_values, marker='*')  # Plot points and line

    plt.xlabel('Latitude')
    plt.ylabel('Longitude')
    plt.grid(True)

    # Create the circle object
    circle = Circle(xy=center, radius=radius * 0.01, color='grey', fill=False)

    # Add the circle to the plot
    ax = plt.gca()  # Get the current axis
    ax.add_patch(circle)

    # Highlight the center of the circle
    plt.scatter(center[0], center[1], color='red', s=100)  # Center marker

    # Ensure equal aspect ratio
    ax.set_aspect("equal")

    # Save the plot as an image
    plt.savefig(file_name, format='png', dpi=300)  # Save with high resolution
    plt.close()  # Close the plot to avoid overlap


def generate_report_for_adId(adId):
    """
    Creates a PDF report with route logs, distances, and graphs.
    """

    logs, total_distance, total_runtime, poster = route_log_by_adId(adId)
    adData = fetch_row_as_dict('mooh.db', 'adOrders', 'adID', 8)
    center = tuple(map(float, adData['center'].split(',')))

    doc = SimpleDocTemplate('adReportFile.pdf', pagesize=letter)
    styles = getSampleStyleSheet()

    elements = [Paragraph("Route Logs Report", styles['Title']), Spacer(1, 12)]

    # Add summary
    summary = f"Total Distance: {total_distance} km<br/>Total Runtime: {total_runtime} seconds"
    elements.append(Paragraph(summary, styles['Normal']))
    elements.append(Spacer(1, 12))
    elements.append(Image(poster, width=400, height=300))

    # Add route details
    for route_id, details in logs.items():
        elements.append(Paragraph(f"Route ID: {route_id}", styles['Heading2']))
        elements.append(Paragraph(f"car ID: {details['carId']}", styles['Normal']))
        elements.append(Paragraph(f"Distance: {details['distance']} km", styles['Normal']))
        elements.append(Paragraph(f"Runtime: {details['runtime']} seconds", styles['Normal']))
        elements.append(Paragraph(f"Coordinates: {details['locs']}", styles['Normal']))
        elements.append(Paragraph(f"Timestamps: {details['times']}", styles['Normal']))

        # Add route graph
        graph_image = f"routes/route_{route_id}.png"
        save_plot_as_image(details['locs'], center, int(adData['radius']), graph_image)
        elements.append(Image(graph_image, width=400, height=300))
        elements.append(Spacer(1, 12))
        print(route_id)

    # Build the PDF
    doc.build(elements)
    print(f"PDF report generated")


def generate_report_for_carId(carId):
    """
    Creates a PDF report with route logs, distances, and graphs.
    """

    logs, total_distance, total_runtime = route_log_by_carId(carId)

    doc = SimpleDocTemplate('carReportFile.pdf', pagesize=letter)
    styles = getSampleStyleSheet()

    elements = []

    # Add Title
    elements.append(Paragraph(f"{carId} Log Report", styles['Title']))
    elements.append(Spacer(1, 12))

    # Add summary
    summary = f"Total Distance: {total_distance} km<br/>Total Runtime: {total_runtime} seconds"
    elements.append(Paragraph(summary, styles['Normal']))
    elements.append(Spacer(1, 12))

    # Add route details
    for route_id, details in logs.items():
        elements.append(Paragraph(f"Route ID: {route_id}", styles['Heading2']))
        elements.append(Paragraph(f"Distance: {details['distance']} km", styles['Normal']))
        elements.append(Paragraph(f"Runtime: {details['runtime']} seconds", styles['Normal']))
        elements.append(Paragraph(f"Coordinates: {details['locs']}", styles['Normal']))
        elements.append(Paragraph(f"Timestamps: {details['times']}", styles['Normal']))

        # Add route graph
        poster = details['poster']
        elements.append(Image(poster, width=400, height=300))
        elements.append(Spacer(1, 12))

    # Build the PDF
    doc.build(elements)
    print(f"PDF report generated")


def save_adOrders_to_db(data):
    """
    Saves the given dictionary data to an SQL database, updating existing records if necessary.

    Args:
        data: A dictionary containing the ad information.

    Returns:
        The newly generated adId, or the existing adId if the record was updated.
    """

    conn = sqlite3.connect('mooh.db')
    cursor = conn.cursor()

    # Check for existing ad with the same user, center, and fileUploaded
    cursor.execute('''
        SELECT adId FROM adOrders
        WHERE user = ? AND center = ? AND fileUploaded = ?
    ''', (data['user'], data['center'], data['fileUploaded']))
    existing_ad = cursor.fetchone()

    if existing_ad:
        # Update the existing record if necessary
        if data.get('fromDates') or data.get('fromTimes') or \
                data.get('toDates') or data.get('toTimes') or \
                data.get('runTimes') or data.get('radius'):
            cursor.execute('''
                UPDATE adOrders
                SET fromDates = ?, fromTimes = ?, toDates = ?, toTimes = ?, runTime = ?, radius = ?
                WHERE adId = ?
            ''', (
                json.dumps(data.get('fromDates', [])),
                json.dumps(data.get('fromTimes', [])),
                json.dumps(data.get('toDates', [])),
                json.dumps(data.get('toTimes', [])),
                data.get('runTime'),
                data.get('radius'),
                existing_ad[0]
            ))
            conn.commit()
            return existing_ad[0]
        else:
            return existing_ad[0]  # No need to update, return the existing adId

    # Insert the new ad
    try:
        cursor.execute('''
            INSERT INTO adOrders (user, center, email, fileUploaded, fromDates, fromTimes, radius, runTime, toDates, toTimes)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (data['user'], data['center'], data['email'], data['fileUploaded'],
              json.dumps(data['fromDates']), json.dumps(data['fromTimes']), data['radius'], data['runTime'],
              json.dumps(data['toDates']), json.dumps(data['toTimes'])))
        conn.commit()
        new_id = cursor.lastrowid
        return new_id
    except sqlite3.Error as e:
        print(f"Error saving data: {e}")
        return None
    finally:
        conn.close()


def pick_random_memejpg(folder_path):
    """
    Randomly selects a .jpg file from the specified folder.

    :param folder_path: Path to the folder containing .jpg files.
    :return: The full path to the randomly selected .jpg file, or None if no .jpg files are found.
    """
    try:
        # Get a list of all .jpg files in the folder
        jpg_files = [file for file in os.listdir(folder_path) if file.lower().endswith('.jpg')]

        if not jpg_files:
            print("No .jpg files found in the specified folder.")
            return None

        # Randomly select a .jpg file
        random_file = random.choice(jpg_files)
        return os.path.join(folder_path, random_file)

    except Exception as e:
        print(f"Error: {e}")
        return None
