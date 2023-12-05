from flask import Flask, jsonify, request, send_file, send_from_directory
from io import BytesIO
from yt_dlp import YoutubeDL
import json
from ytmusicapi import YTMusic
import dotenv
from contextlib import redirect_stdout
from recommendation.recommendor import getRecommendations
import spotipy
import os

dotenv.load_dotenv()
spotify_client_id = os.getenv("SPOTIFY_CLIENT_ID")
spotify_client_secret = os.getenv("SPOTIFY_CLIENT_SECRET")
sp = spotipy.Spotify(client_credentials_manager=spotipy.oauth2.SpotifyClientCredentials(
    client_id=spotify_client_id,
    client_secret=spotify_client_secret
))
yt = YTMusic()

app = Flask(__name__,
            static_url_path='/',
            static_folder='frontend/build/')

def search_songs(search_term):
    results = sp.search(q=search_term, type='track', limit=10)

    data = []
    for track in results["tracks"]["items"]:
        track_name = track["name"]
        track_id = track["id"]
        preview_url = track["preview_url"]
        artist_name = track["artists"][0]["name"]
        thumbnail_url = track['album']['images'][0]['url']
        data.append({
            "title": track_name,
            "artist": artist_name,
            "image": thumbnail_url,
            "id": track_id,
            "preview_url": preview_url
        })

    return data

def get_youtube_link(song, artist):
    youtube_query = f"{song} {artist}"
    search_results = yt.search(youtube_query, "songs")

    with open("youtube_results.json", "w") as file:
        json.dump(search_results, file, indent=2)

    return search_results[0]['videoId']

def get_audio_features(trackId):
    results = sp.audio_features(trackId)
    print(results)
    return results[0]

def get_track_metadata(trackId_list):
    results = sp.tracks(trackId_list)

    data = []
    for track in results["tracks"]:
        track_name = track["name"]
        track_id = track["id"]
        preview_url = track["preview_url"]
        artist_name = track["artists"][0]["name"]
        thumbnail_url = track['album']['images'][0]['url']
        data.append({
            "title": track_name,
            "artist": artist_name,
            "image": thumbnail_url,
            "id": track_id,
            "preview_url": preview_url
        })

    return data


@app.route('/')
def home():
    return send_from_directory('frontend/build', 'index.html')

@app.route('/api/search', methods=["POST"])
def search():
    search = request.form['search_box']
    search_results = search_songs(search)
    return jsonify(search_results), 200

@app.route('/api/stream')
def stream():
    artist = request.args.get("artist")
    song = request.args.get("song")
    song_yt_id = get_youtube_link(song, artist)
    youtube_url = f"https://www.youtube.com/watch?v={song_yt_id}"
    ctx = {
        "outtmpl": "-",
        "logtostderr": True,
        "format": "mp3/bestaudio/best",
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3'
        }]
    }
    buffer = BytesIO()
    with redirect_stdout(buffer), YoutubeDL(ctx) as ytdl:
        ytdl.download([youtube_url])

    return send_file(buffer, mimetype="audio/mpeg")

@app.route('/api/recommend/<trackId>')
def recommend(trackId):
    audio_features = get_audio_features(trackId)

    keys = ["acousticness","danceability","duration_ms","energy","instrumentalness","key","liveness","loudness","mode","speechiness","tempo","time_signature","valence"]

    query_vector = [audio_features.get(key) for key in keys]
    recommendations = getRecommendations(query_vector=query_vector)

    song_data = get_track_metadata([track.get("id") for track in recommendations])

    return jsonify(song_data)


if __name__ == '__main__':
    app.run(debug=True)