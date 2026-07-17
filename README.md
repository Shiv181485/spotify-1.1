# Pulse — Spotify Playback Upgrade

Run from this folder after installing dependencies:

```powershell
pip install -r requirements.txt
streamlit run app.py
```

Open **Explore tracks**, search or filter the catalogue, and select a song. The app shows Spotify's official embedded player and offers direct **Open in Spotify** and fallback **Search Spotify** links.

No Spotify credentials are required for this dataset because it already includes Spotify track IDs. Playback availability is controlled by Spotify and can vary by account and region.
