from dotenv import load_dotenv
from flask import Flask, request, redirect
import pandas as pd
import webbrowser
import threading
import time
import os
import base64
import requests
from requests import post,get
from datetime import datetime, timedelta
import json
load_dotenv()

client_id = os.getenv("CLIENT_ID")
client_secret = os.getenv("CLIENT_SECRET")
redirect_uri = os.getenv("REDIRECT_URI")
scope = 'user-top-read'


# auth_url = f'https://accounts.spotify.com/authorize?client_id={client_id}&response_type=code&redirect_uri={redirect_uri}&scope={scope}'
# webbrowser.open(auth_url)
# # print(auth_url)
# # After authorization, you will be redirected to the redirect_uri with a code parameter.
# auth_code = input('Enter the authorization code from the URL: ')
# # auth_code = 'AQAr4CVMMQ9zGiwYgovcOtisDkJ5hqB-grErJHnBH5GEM7iwhPu8hajONC0GxRYz3oRg6QyiC7rQ2MJVRqGcJbC5E_FajEv6TQe9ZCQrve_zH91KBM-IX1YgPiqjGNE37xFgBHHGU6AR8QhdE0H0rdEHRGXvepTwbtZALB9Ur5APMzLm9kpD6UY5Zreuk2yJ5A'
# # Open the URL in the web browser
# # webbrowser.open(auth_url)

app = Flask(__name__)

auth_code = None

@app.route('/')
def index():
    auth_url = f'https://accounts.spotify.com/authorize?client_id={client_id}&response_type=code&redirect_uri={redirect_uri}&scope={scope}'
    return redirect(auth_url)

@app.route('/callback')
def callback():
    global auth_code
    auth_code = request.args.get('code')
    return "Authorization code received. You can close this window."

def run_flask_app():
    app.run(port=8888)

# Route to shutdown the Flask server
@app.route('/shutdown', methods=['POST'])
def shutdown():
    print("Shutting down server...")
    os._exit(0)  # Forcefully terminate the Python process

    # This code won't execute because the process is terminated
    return 'Server shutting down...'


# Step 1: Start Flask in a separate thread
threading.Thread(target=run_flask_app).start()
time.sleep(1)  # Give the server a second to start

# Step 2: Open the browser to get the authorization code
webbrowser.open('http://localhost:8888/')
while auth_code is None:
    time.sleep(1)  # Wait for the authorization code


def get_token():
    auth_string = client_id + ":" + client_secret
    auth_bytes =  auth_string.encode("utf-8")
    auth_base64 = str(base64.b64encode(auth_bytes) , "utf-8")

    url = "https://accounts.spotify.com/api/token"
    headers = {
        "Authorization": "Basic " + auth_base64,
        "Content-Type": "application/x-www-form-urlencoded" 
    }
    data = {
        "grant_type": "authorization_code",
        "redirect_uri": redirect_uri,
        "code" : auth_code
        }
    result = post(url, headers=headers, data=data)
    json_result = json.loads(result.content)
    token = json_result["access_token"]
    return token

def get_auth_header(token):
    return {"Authorization" : "Bearer " + token}

# Function to stop the Flask server
def stop_flask_server():
    shutdown_url = 'http://localhost:8888/shutdown'
    response = requests.post(shutdown_url)
    print(response.text)  # Print the server response

def search_artist(token,artist_name):
    headers = get_auth_header(token)
    url = "https://api.spotify.com/v1/search"
    query = f"?q={artist_name}&type=artist&limit=1"

    query_url = url + query

    result = get(query_url, headers=headers)
    json_result = json.loads(result.content)["artists"]["items"]

    if len(json_result) == 0:
        print("Artist does not exists..")
        return None
    
    return json_result[0]

def songs_by_artist(token, artist_id):
    url = f"https://api.spotify.com/v1/artists/{artist_id}/top-tracks"
    headers = get_auth_header(token)

    result = get(url,headers=headers)
    json_result = json.loads(result.content)["tracks"]

    return json_result

def my_top_tracks(token,time_range='medium_term'):
    url = f"https://api.spotify.com/v1/me/top/tracks?time_range={time_range}&limit=50"
    headers = get_auth_header(token)

    result = get(url,headers=headers)
    json_result = json.loads(result.content)["items"]
    # print(json_result)
    return json_result


token = get_token() 
# result = search_artist(token,"Karthik")
# artist_id = result["id"]
# artist_name = result["name"]



# print(artist_name)

time_range = 'short_term'
songs = my_top_tracks(token,time_range)
# print(songs)
for idx, song in enumerate(songs):
    print(f"{idx+1}. {song['name']}")


# Function to fetch audio features for tracks
def get_audio_features(token, track_ids):
    url = f"https://api.spotify.com/v1/audio-features"
    headers = get_auth_header(token)
    response = requests.get(url, headers=headers, params={"ids": ",".join(track_ids)})
    return response.json()['audio_features']


# Extract track IDs
track_ids = [track['id'] for track in songs]

# Fetch audio features
audio_features = get_audio_features(token, track_ids)

# Create a DataFrame with track info and audio features
track_data = []
for track, features in zip(songs, audio_features):
    track_info = {
        "name": track['name'],
        "artists": ", ".join(artist['name'] for artist in track['artists']),
        "id": track['id'],
        "popularity": track['popularity']
    }
    track_info.update(features)
    track_data.append(track_info)

df = pd.DataFrame(track_data)
print(df.head())

df.to_csv('myTracksforAnalysisJuly9.csv', index=False)


# Stop the Flask server
# Call the function to stop the server
stop_flask_server()
