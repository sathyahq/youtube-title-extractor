# YouTube Title Extractor & Generator

Enter a keyword, see top-performing YouTube titles, analyze what works, and generate optimized titles. No login required.

## How to Run (on your computer)

1. Make sure you have Python installed
2. Open your terminal and run these commands one by one:

```
git clone https://github.com/sathyahq/youtube-title-extractor.git
cd youtube-title-extractor
pip install -r requirements.txt
streamlit run app.py
```

3. The app opens in your browser automatically

## How to Deploy (free, online)

Deploy on **Streamlit Community Cloud** so you can access it from anywhere:

1. Go to [share.streamlit.io](https://share.streamlit.io)
2. Sign in with your GitHub account
3. Click **New app**
4. Select this repo (`sathyahq/youtube-title-extractor`)
5. Set **Main file path** to `app.py`
6. Click **Deploy**

Done. You get a public URL you can bookmark and use anytime.

## What It Does

1. **Scrape** — Enter a keyword, get the top YouTube videos with titles, views, likes, duration, etc.
2. **Analyze** — See which title patterns (questions, how-tos, numbers, etc.) get the most views
3. **Generate** — Get AI-powered title suggestions based on what's actually working

## Features

- View count, likes, duration, upload date, and subscriber count
- Title pattern performance charts
- Title length sweet spot analysis
- High-view vs low-view word comparison
- AI-powered title generation (free Gemini API key, optional)
- Template-based title generation (no API key needed)
- Download results as CSV

## Gemini API Key (optional, free)

For AI-powered title generation, get a free API key:

1. Go to [Google AI Studio](https://aistudio.google.com/apikey)
2. Sign in with your Google account
3. Click **Get API Key**
4. Paste it in the sidebar of the app
