"""Pulse — Spotify analytics with direct playback and track sharing."""
from __future__ import annotations

from pathlib import Path
from urllib.parse import quote_plus

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
import streamlit.components.v1 as components

st.set_page_config(page_title="Pulse | Spotify Intelligence", page_icon="♫", layout="wide")

ROOT = Path(__file__).parent
DATA_PATH = ROOT / "data" / "dataset.csv"
FEATURES = ["danceability", "energy", "valence", "acousticness", "instrumentalness", "liveness", "speechiness"]


@st.cache_data(show_spinner=False)
def load_data(uploaded_file=None) -> pd.DataFrame:
    """Load a Spotify-style CSV and prepare fields used by the dashboard."""
    source = uploaded_file if uploaded_file is not None else DATA_PATH
    frame = pd.read_csv(source).drop(columns=["Unnamed: 0"], errors="ignore")
    required = {"track_id", "track_name", "artists", "duration_ms", "popularity", "track_genre", "explicit"}
    missing = required.difference(frame.columns)
    if missing:
        raise ValueError(f"Missing required column(s): {', '.join(sorted(missing))}")
    frame = frame.drop_duplicates("track_id").copy()
    frame["duration_min"] = pd.to_numeric(frame["duration_ms"], errors="coerce").fillna(0) / 60_000
    frame["artists"] = frame["artists"].fillna("Unknown artist")
    frame["track_name"] = frame["track_name"].fillna("Untitled")
    frame["album_name"] = frame.get("album_name", pd.Series("Unknown album", index=frame.index)).fillna("Unknown album")
    frame["spotify_url"] = "https://open.spotify.com/track/" + frame["track_id"].astype(str)
    return frame


def chart_style(fig: go.Figure, height: int = 370) -> go.Figure:
    fig.update_layout(height=height, margin=dict(l=10, r=10, t=38, b=10), paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", font=dict(color="#B7C4D8", family="Inter, sans-serif"), title_font=dict(color="#F7FAFF", size=16), legend=dict(orientation="h", y=1.08, x=0), xaxis=dict(gridcolor="rgba(255,255,255,.07)", zeroline=False), yaxis=dict(gridcolor="rgba(255,255,255,.07)", zeroline=False))
    return fig


def metric(label: str, value: str, note: str, accent: str = "#1ed760") -> None:
    st.markdown(f'<div class="metric-card"><p>{label}</p><h2>{value}</h2><span style="color:{accent}">●</span> {note}</div>', unsafe_allow_html=True)


def spotify_search_url(track: pd.Series) -> str:
    return "https://open.spotify.com/search/" + quote_plus(f"{track['track_name']} {track['artists']}")


def track_player(track: pd.Series) -> None:
    """Show Spotify's official embed plus resilient direct/search links.

    Notes:
    - Streamlit cannot force autoplay inside Spotify's iframe.
    - We add validation + fallbacks so the user still gets playable links when
      embedding is blocked.
    """

    track_id = str(track.get("track_id", "")).strip()
    spotify_url = str(track.get("spotify_url", "")).strip()

    st.markdown(
        "<div class='section-title'>NOW PLAYING <span>Spotify controls</span></div>",
        unsafe_allow_html=True,
    )

    info, player = st.columns([1, 1.55], vertical_alignment="center")

    with info:
        explicit = " · EXPLICIT" if bool(track.get("explicit", False)) else ""
        track_name = str(track.get("track_name", "Untitled"))
        artists = str(track.get("artists", "Unknown artist"))
        album_name = str(track.get("album_name", "Unknown album"))
        track_genre = str(track.get("track_genre", "")).title()
        duration_min = float(track.get("duration_min", 0.0) or 0.0)
        popularity = int(float(track.get("popularity", 0) or 0))

        st.markdown(
            f"<div class='now-playing'>"
            f"<p>SELECTED TRACK{explicit}</p>"
            f"<h2>{track_name}</h2>"
            f"<h3>{artists}</h3>"
            f"<span>{album_name} · {track_genre} · {duration_min:.1f} min</span>"
            f"</div>",
            unsafe_allow_html=True,
        )

        left, right = st.columns(2)
        with left:
            if spotify_url:
                st.link_button("▶ Open in Spotify", spotify_url, use_container_width=True)
            else:
                st.button("▶ Open in Spotify", disabled=True, use_container_width=True)

        with right:
            st.link_button(
                "⌕ Search Spotify",
                spotify_search_url(track),
                use_container_width=True,
            )

        st.caption(
            f"Popularity {popularity}/100 · Spotify opens in its app or web player."
        )
        if spotify_url:
            st.code(spotify_url, language=None)

    with player:
        if not track_id:
            st.warning("Missing Spotify track_id for this row. Use the ‘Open in Spotify’ link." )
            return

        # The iframe uses the dataset's Spotify ID; Spotify controls availability by region/account.
        embed_src = f"https://open.spotify.com/embed/track/{track_id}?utm_source=generator"
        st.write("")
        components.html(
            f'<iframe '
            f'style="border-radius:14px" '
            f'src="{embed_src}" '
            f'width="100%" height="352" '
            f'frameBorder="0" '
            f'allowfullscreen="" '
            f'allow="autoplay; clipboard-write; encrypted-media; fullscreen; picture-in-picture" '
            f'loading="lazy"></iframe>',
            height=365,
        )



def sidebar(frame: pd.DataFrame) -> tuple[pd.DataFrame, str]:
    with st.sidebar:
        st.markdown("<div class='brand'>PULSE<span>♫</span></div><p class='brand-sub'>SPOTIFY INTELLIGENCE</p>", unsafe_allow_html=True)
        page = st.radio("Navigate", ["Overview", "Explore tracks", "Audio DNA", "Genre intelligence", "Data studio"], label_visibility="collapsed")
        st.markdown("<p class='side-label'>DISCOVERY FILTERS</p>", unsafe_allow_html=True)
        genres = sorted(frame["track_genre"].dropna().unique())
        chosen_genres = st.multiselect("Genres", genres, placeholder="All genres")
        popularity = st.slider("Popularity range", 0, 100, (0, 100))
        explicit = st.toggle("Explicit tracks only")
        st.markdown("<div class='sidebar-tip'>LIVE CATALOGUE<br><b>114K audio fingerprints</b></div>", unsafe_allow_html=True)
    filtered = frame[frame["popularity"].between(*popularity)].copy()
    if chosen_genres: filtered = filtered[filtered["track_genre"].isin(chosen_genres)]
    if explicit: filtered = filtered[filtered["explicit"]]
    return filtered, page


def overview(df: pd.DataFrame) -> None:
    st.markdown("<div class='eyebrow'>CATALOGUE INTELLIGENCE · JULY 2026</div><h1>Find the sound behind<br><em>the signal.</em></h1><p class='lead'>A high-resolution view of Spotify’s audio universe—built for curious listeners, creators, and music teams.</p>", unsafe_allow_html=True)
    a, b, c, d = st.columns(4)
    with a: metric("TRACKS IN SCOPE", f"{len(df):,}", "filtered catalogue")
    with b: metric("AVG. POPULARITY", f"{df.popularity.mean():.1f}", "out of 100", "#8e77ff")
    with c: metric("GENRES EXPLORED", f"{df.track_genre.nunique()}", "distinct scenes", "#46c7e8")
    with d: metric("EXPLICIT SHARE", f"{df.explicit.mean():.0%}", "of tracks", "#ff6b87")
    st.markdown("<div class='section-title'>THE CURRENT PULSE <span>Popularity by genre</span></div>", unsafe_allow_html=True)
    top = df.groupby("track_genre", as_index=False).agg(popularity=("popularity", "mean"), tracks=("track_id", "size")).query("tracks >= 30").nlargest(12, "popularity").sort_values("popularity")
    fig = px.bar(top, x="popularity", y="track_genre", orientation="h", text="popularity", color="popularity", color_continuous_scale=["#26314c", "#1ed760"])
    fig.update_traces(texttemplate="%{text:.1f}", textposition="outside", marker_line_width=0); fig.update_layout(coloraxis_showscale=False, yaxis_title=None, xaxis_title="Average popularity")
    st.plotly_chart(chart_style(fig, 430), use_container_width=True, config={"displayModeBar": False})


def explore(df: pd.DataFrame) -> None:
    st.markdown("<div class='eyebrow'>TRACK DISCOVERY</div><h1>Explore and <em>play.</em></h1><p class='lead'>Choose a track to launch Spotify’s full player, then open it directly in Spotify.</p>", unsafe_allow_html=True)
    query = st.text_input("Search track or artist", placeholder="Try ‘Taylor’, ‘Blinding’, or ‘Lofi’")
    data = df[df["track_name"].str.contains(query, case=False, na=False) | df["artists"].str.contains(query, case=False, na=False)] if query else df
    sort = st.selectbox("Rank tracks by", ["popularity", "danceability", "energy", "tempo"], index=0)
    results = data.nlargest(250, sort).reset_index(drop=True)
    if results.empty:
        st.info("No tracks match this search."); return
    labels = results.apply(lambda r: f"{r['track_name']} — {r['artists']}  ·  {int(r['popularity'])}%", axis=1)
    selected_label = st.selectbox("Select a song to play", labels, label_visibility="collapsed")
    track = results.iloc[labels[labels == selected_label].index[0]]
    track_player(track)
    st.markdown("<div class='section-title'>RESULTS <span>Top 250 shown for speed</span></div>", unsafe_allow_html=True)
    cols = ["track_name", "artists", "album_name", "track_genre", "popularity", "duration_min", "spotify_url"]
    st.dataframe(results[cols].rename(columns={"duration_min": "minutes", "spotify_url": "play in Spotify"}), use_container_width=True, height=430, hide_index=True, column_config={"popularity": st.column_config.ProgressColumn("Popularity", min_value=0, max_value=100, format="%d"), "minutes": st.column_config.NumberColumn("Minutes", format="%.1f"), "play in Spotify": st.column_config.LinkColumn("Play", display_text="Open ↗")})


def audio_dna(df: pd.DataFrame) -> None:
    st.markdown("<div class='eyebrow'>AUDIO FINGERPRINT</div><h1>Decode the <em>feeling.</em></h1>", unsafe_allow_html=True)
    left, right = st.columns([1, 1.7])
    with left:
        selected = st.selectbox("Choose a genre", sorted(df.track_genre.unique())); profile = df[df.track_genre == selected][FEATURES].mean()
        fig = go.Figure(go.Scatterpolar(r=list(profile.values) + [profile.iloc[0]], theta=[x.title() for x in FEATURES] + [FEATURES[0].title()], fill="toself", line_color="#1ed760", fillcolor="rgba(30,215,96,.22)")); fig.update_layout(polar=dict(bgcolor="rgba(0,0,0,0)", radialaxis=dict(visible=True, range=[0, 1], gridcolor="rgba(255,255,255,.13)"), angularaxis=dict(gridcolor="rgba(255,255,255,.13)")), paper_bgcolor="rgba(0,0,0,0)", font=dict(color="#d8e0ec"), height=430, margin=dict(l=30,r=30,t=30,b=30), showlegend=False); st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})
    with right:
        sample = df.sample(min(6000, len(df)), random_state=42); fig = px.scatter(sample, x="energy", y="valence", color="popularity", size="danceability", hover_data=["track_name", "artists", "track_genre"], color_continuous_scale=["#30415e", "#8e77ff", "#1ed760"], labels={"valence":"Positivity", "energy":"Energy"}); st.plotly_chart(chart_style(fig, 430), use_container_width=True, config={"displayModeBar": False})


def genre_intelligence(df: pd.DataFrame) -> None:
    st.markdown("<div class='eyebrow'>SCENE MAPPING</div><h1>Genres in <em>context.</em></h1>", unsafe_allow_html=True); grouped = df.groupby("track_genre", as_index=False).agg(tracks=("track_id", "size"), popularity=("popularity", "mean"), energy=("energy", "mean"), danceability=("danceability", "mean")); c1, c2 = st.columns(2)
    with c1: st.plotly_chart(chart_style(px.scatter(grouped, x="energy", y="danceability", size="tracks", color="popularity", hover_name="track_genre", color_continuous_scale=["#8e77ff", "#1ed760"], labels={"energy":"Energy", "danceability":"Danceability"})), use_container_width=True, config={"displayModeBar": False})
    with c2:
        fig = px.treemap(grouped.nlargest(35, "tracks"), path=["track_genre"], values="tracks", color="popularity", color_continuous_scale=["#252f48", "#1ed760"]); fig.update_layout(margin=dict(l=0,r=0,t=25,b=0), paper_bgcolor="rgba(0,0,0,0)", font=dict(color="#eaf0f8")); st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})


def data_studio(df: pd.DataFrame) -> None:
    st.markdown("<div class='eyebrow'>DATA STUDIO</div><h1>Trust the <em>data.</em></h1>", unsafe_allow_html=True); c1, c2 = st.columns([1, 1.8])
    with c1:
        st.markdown("<div class='mini-card'><b>Data quality</b><br><span>Complete audio-feature rows</span><h2>" + f"{(1-df[FEATURES].isna().mean().mean()):.1%}" + "</h2></div>", unsafe_allow_html=True); st.markdown("<div class='mini-card'><b>Spotify playback</b><br><span>Embedded player & direct links</span><h2>Ready</h2></div>", unsafe_allow_html=True); st.download_button("Download filtered CSV", df.to_csv(index=False).encode("utf-8"), "spotify_filtered.csv", "text/csv", use_container_width=True)
    with c2: st.plotly_chart(chart_style(px.imshow(df[FEATURES + ["popularity", "tempo"]].corr(), text_auto=".2f", color_continuous_scale="RdBu", zmin=-1, zmax=1, aspect="auto"), 480), use_container_width=True, config={"displayModeBar": False})


def main() -> None:
    st.markdown("<style>" + (ROOT / "assets" / "style.css").read_text(encoding="utf-8") + "</style>", unsafe_allow_html=True)
    with st.sidebar: upload = st.file_uploader("Replace catalogue", type="csv", label_visibility="collapsed")
    try: data = load_data(upload)
    except Exception as exc: st.error(f"We couldn't read this CSV: {exc}"); st.stop()
    data, page = sidebar(data)
    if data.empty: st.warning("No tracks match the active filters. Widen the filters and try again."); return
    {"Overview": overview, "Explore tracks": explore, "Audio DNA": audio_dna, "Genre intelligence": genre_intelligence, "Data studio": data_studio}[page](data)
    st.markdown("<div class='footer'>PULSE / SPOTIFY INTELLIGENCE <span>Designed for sound discovery</span></div>", unsafe_allow_html=True)


if __name__ == "__main__": main()
