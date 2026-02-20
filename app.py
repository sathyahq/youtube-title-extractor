import streamlit as st
import yt_dlp
import pandas as pd
import re
import time
from collections import Counter
from datetime import datetime

# --- Page Setup ---
st.set_page_config(page_title="YouTube Title Extractor & Generator", layout="wide")

# --- Helper Functions ---

def format_number(n):
    if n is None:
        return "N/A"
    n = int(n)
    if n >= 1_000_000_000:
        return f"{n / 1_000_000_000:.1f}B"
    if n >= 1_000_000:
        return f"{n / 1_000_000:.1f}M"
    if n >= 1_000:
        return f"{n / 1_000:.1f}K"
    return str(n)


def format_duration(seconds):
    if seconds is None:
        return "N/A"
    seconds = int(seconds)
    h, m, s = seconds // 3600, (seconds % 3600) // 60, seconds % 60
    return f"{h}:{m:02d}:{s:02d}" if h > 0 else f"{m}:{s:02d}"


def scrape_youtube(keyword, n):
    """Scrape YouTube search results using yt-dlp."""
    # Step 1: Flat search to get video IDs (fast)
    with yt_dlp.YoutubeDL({'quiet': True, 'no_warnings': True, 'extract_flat': True, 'ignoreerrors': True}) as ydl:
        try:
            results = ydl.extract_info(f"ytsearch{n}:{keyword}", download=False)
        except Exception as e:
            st.error(f"Search failed: {e}")
            return []

    if not results or 'entries' not in results:
        return []

    entries = [e for e in results.get('entries', []) if e]
    videos = []
    progress = st.progress(0, text="Fetching video details...")

    # Step 2: Get full details for each video
    for i, entry in enumerate(entries):
        vid_id = entry.get('id') or entry.get('url')
        if not vid_id:
            continue
        url = vid_id if vid_id.startswith('http') else f"https://www.youtube.com/watch?v={vid_id}"
        progress.progress((i + 1) / len(entries), text=f"Fetching video {i + 1} of {len(entries)}...")

        try:
            with yt_dlp.YoutubeDL({'quiet': True, 'no_warnings': True, 'ignoreerrors': True}) as ydl:
                info = ydl.extract_info(url, download=False)
                if info and info.get('title'):
                    videos.append({
                        'title': info.get('title', 'N/A'),
                        'url': info.get('webpage_url', url),
                        'channel': info.get('channel') or info.get('uploader', 'N/A'),
                        'subscribers': info.get('channel_follower_count'),
                        'views': info.get('view_count'),
                        'likes': info.get('like_count'),
                        'comments': info.get('comment_count'),
                        'duration': info.get('duration'),
                        'upload_date': info.get('upload_date'),
                    })
        except Exception:
            continue

    progress.empty()
    return videos


def detect_patterns(title):
    """Detect title patterns."""
    patterns = []
    t = title.lower()
    if '?' in title:
        patterns.append('Question')
    if 'how to' in t or 'how i' in t:
        patterns.append('How-To')
    if re.search(r'\b\d+\b', title):
        patterns.append('Number/List')
    power = ['amazing','incredible','insane','shocking','secret','ultimate','best','worst',
             'crazy','unbelievable','genius','hack','trick','mistake','never','always',
             'must','truth','proven','powerful','essential','complete','perfect','simple',
             'easy','free']
    if any(w in t for w in power):
        patterns.append('Power Words')
    if any(w.isupper() and len(w) > 1 for w in title.split()):
        patterns.append('CAPS Emphasis')
    if '[' in title or '(' in title:
        patterns.append('Brackets')
    if re.search(r'\b20[12]\d\b', title):
        patterns.append('Year')
    if '|' in title or ' - ' in title:
        patterns.append('Separator')
    if not patterns:
        patterns.append('Simple/Direct')
    return patterns


def analyze(videos):
    """Analyze title patterns and performance."""
    pattern_stats = {}
    for v in videos:
        views = v.get('views') or 0
        for p in detect_patterns(v['title']):
            if p not in pattern_stats:
                pattern_stats[p] = {'total': 0, 'count': 0}
            pattern_stats[p]['total'] += views
            pattern_stats[p]['count'] += 1
    for p in pattern_stats:
        pattern_stats[p]['avg'] = pattern_stats[p]['total'] / pattern_stats[p]['count']

    buckets = [('Short (under 40)', 0, 40), ('Medium (40-60)', 40, 60),
               ('Long (60-80)', 60, 80), ('Very Long (80+)', 80, 999)]
    length_stats = {}
    for name, lo, hi in buckets:
        vl = [v.get('views') or 0 for v in videos if lo <= len(v['title']) < hi]
        if vl:
            length_stats[name] = {'avg': sum(vl) / len(vl), 'count': len(vl)}

    sorted_v = sorted(videos, key=lambda v: v.get('views') or 0, reverse=True)
    mid = max(len(sorted_v) // 2, 1)

    stop = {'the','a','an','in','on','at','to','for','of','and','or','but','is','are',
            'was','were','it','its','i','my','you','your','we','our','this','that',
            'with','from','by','as','not','no','do','if','so','be','he','she','they',
            'will','can','has','have','had','all','me','us','about','just','up','out',
            'what','when','how','why','which','who','where','than','more','most','very',
            'get','got','one','new','like','make','know','don','thing','way'}

    def wf(vlist):
        words = []
        for v in vlist:
            for w in re.findall(r'[a-zA-Z]+', v['title'].lower()):
                if w not in stop and len(w) > 2:
                    words.append(w)
        return Counter(words)

    return {
        'patterns': pattern_stats,
        'lengths': length_stats,
        'top_words': wf(sorted_v[:mid]).most_common(15),
        'bottom_words': wf(sorted_v[mid:]).most_common(15),
        'top5': sorted_v[:5],
        'total': len(videos),
        'avg_len': sum(len(v['title']) for v in videos) / len(videos),
    }


def generate_gemini(analysis, keyword, api_key, n=10):
    """Generate titles with Gemini AI."""
    try:
        from google import genai
        client = genai.Client(api_key=api_key)

        sorted_p = sorted(analysis['patterns'].items(), key=lambda x: x[1]['avg'], reverse=True)
        best = [p[0] for p in sorted_p[:3]]
        tops = '\n'.join([f"- {v['title']} ({format_number(v.get('views'))} views)" for v in analysis['top5']])
        words = ', '.join([w for w, _ in analysis['top_words'][:10]])

        prompt = f"""You are a YouTube title optimization expert. Based on real data, generate {n} optimized title suggestions for a video about "{keyword}".

TOP PERFORMING TITLES:
{tops}

INSIGHTS:
- Best patterns: {', '.join(best)}
- Optimal length: {int(analysis['avg_len'])} characters
- Top words: {words}

RULES:
1. Every title about "{keyword}"
2. Use winning patterns from the data
3. 40-70 characters
4. Click-worthy but NOT clickbait
5. Mix styles: questions, how-tos, lists, statements
6. Each title unique

Output ONLY numbered titles 1-{n}. No extra text."""

        for attempt in range(3):
            try:
                resp = client.models.generate_content(model="gemini-2.0-flash", contents=prompt)
                return resp.text
            except Exception as e:
                if "429" in str(e) or "quota" in str(e).lower():
                    time.sleep(30 * (attempt + 1))
                else:
                    return f"Error: {e}"
        return "Error: Rate limited. Please wait a minute and try again."
    except ImportError:
        return "Error: google-genai not installed. Run: pip install google-genai"
    except Exception as e:
        return f"Error: {e}"


def generate_templates(keyword, n=10):
    """Generate titles using templates (no API needed)."""
    kw = keyword.strip()
    year = datetime.now().year
    templates = [
        f"How to {kw} - Complete Guide for Beginners",
        f"{kw}: Everything You Need to Know ({year})",
        f"7 {kw} Tips That Actually Work",
        f"Why {kw} Is More Important Than You Think",
        f"The ULTIMATE Guide to {kw} (Step by Step)",
        f"I Tried {kw} for 30 Days - Here's What Happened",
        f"{kw} Explained in 10 Minutes",
        f"Stop Making These {kw} Mistakes",
        f"The Truth About {kw} Nobody Tells You",
        f"{kw} Tutorial: From Zero to Pro",
        f"5 {kw} Secrets the Pros Don't Share",
        f"What Is {kw}? Simple Explanation for Beginners",
        f"BEST {kw} Strategy That Works Every Time",
        f"{kw} for Beginners: Start Here ({year})",
        f"10 Common {kw} Mistakes and How to Fix Them",
        f"Why Most People Fail at {kw}",
        f"{kw} in {year}: What Has Changed?",
        f"Master {kw} With These Simple Steps",
        f"The Only {kw} Guide You Will Ever Need",
        f"{kw}: Beginner to Advanced in One Video",
    ]
    return '\n'.join([f"{i+1}. {t}" for i, t in enumerate(templates[:n])])


# =============================================
# MAIN APP UI
# =============================================

st.title("YouTube Title Extractor & Generator")
st.markdown("Enter a keyword to find top-performing YouTube titles, analyze what works, and generate optimized titles.")

# --- Sidebar ---
with st.sidebar:
    st.header("Settings")
    gemini_key = st.text_input(
        "Gemini API Key (optional)",
        type="password",
        help="Get a free key from Google AI Studio (aistudio.google.com/apikey). Makes title generation much better.",
    )
    num_results = st.slider("Videos to scrape", 5, 30, 15)
    num_titles = st.slider("Titles to generate", 5, 20, 10)
    st.divider()
    st.markdown("**How to get a free Gemini API key:**")
    st.markdown("1. Go to [Google AI Studio](https://aistudio.google.com/apikey)")
    st.markdown("2. Sign in with Google")
    st.markdown("3. Click **Get API Key**")
    st.markdown("4. Copy and paste it above")

# --- Search ---
keyword = st.text_input(
    "Enter your keyword or topic",
    placeholder="e.g. productivity tips, learn guitar, meal prep ideas",
)

if st.button("Search & Analyze", type="primary", use_container_width=True):
    if not keyword.strip():
        st.warning("Please enter a keyword.")
    else:
        videos = scrape_youtube(keyword.strip(), num_results)
        if videos:
            st.session_state['videos'] = videos
            st.session_state['search_keyword'] = keyword.strip()
        else:
            st.error("No results found. Try a different keyword.")

# --- Show Results ---
if 'videos' in st.session_state:
    videos = st.session_state['videos']
    kw = st.session_state.get('search_keyword', '')

    # ---- Results Table ----
    st.divider()
    st.subheader(f"Top {len(videos)} Videos for \"{kw}\"")

    df = pd.DataFrame([{
        'Title': v['title'],
        'Channel': v['channel'],
        'Views': v.get('views') or 0,
        'Likes': v.get('likes') or 0,
        'Duration': format_duration(v.get('duration')),
        'Subs': format_number(v.get('subscribers')),
    } for v in videos])

    st.dataframe(
        df,
        use_container_width=True,
        hide_index=True,
        column_config={
            "Views": st.column_config.NumberColumn(format="%d"),
            "Likes": st.column_config.NumberColumn(format="%d"),
        },
    )

    # Download CSV
    csv_data = df.to_csv(index=False)
    st.download_button("Download as CSV", csv_data, f"youtube_titles_{kw}.csv", "text/csv")

    # ---- Analysis ----
    analysis = analyze(videos)

    st.divider()
    st.subheader("Title Analysis")

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("**Which title styles get the most views?**")
        sorted_patterns = sorted(analysis['patterns'].items(), key=lambda x: x[1]['avg'], reverse=True)
        pat_df = pd.DataFrame([{
            'Pattern': p,
            'Avg Views': int(s['avg']),
            'Videos': s['count'],
        } for p, s in sorted_patterns])
        st.bar_chart(pat_df, x='Pattern', y='Avg Views')

    with col2:
        st.markdown(f"**Title length sweet spot** (avg: {int(analysis['avg_len'])} chars)")
        if analysis['lengths']:
            len_df = pd.DataFrame([{
                'Length': name,
                'Avg Views': int(s['avg']),
                'Videos': s['count'],
            } for name, s in analysis['lengths'].items()])
            st.bar_chart(len_df, x='Length', y='Avg Views')

    # Word comparison
    col3, col4 = st.columns(2)
    with col3:
        st.markdown("**Common words in high-view titles**")
        if analysis['top_words']:
            st.markdown(' '.join([f'`{w}` ({c})' for w, c in analysis['top_words']]))
    with col4:
        st.markdown("**Common words in lower-view titles**")
        if analysis['bottom_words']:
            st.markdown(' '.join([f'`{w}` ({c})' for w, c in analysis['bottom_words']]))

    # Top 5
    st.markdown("---")
    st.markdown("**Top 5 best performing titles**")
    for i, v in enumerate(analysis['top5'], 1):
        pats = ', '.join(detect_patterns(v['title']))
        st.markdown(f"{i}. **{v['title']}** — {format_number(v.get('views'))} views · _{pats}_")

    # ---- Title Generation ----
    st.divider()
    st.subheader("Generate Optimized Titles")

    gen_keyword = st.text_input("Generate titles about:", value=kw, key="gen_kw")

    if st.button("Generate Titles", type="primary"):
        if not gen_keyword.strip():
            st.warning("Enter a keyword above.")
        else:
            if gemini_key:
                with st.spinner("Generating AI-powered titles with Gemini..."):
                    result = generate_gemini(analysis, gen_keyword.strip(), gemini_key, num_titles)
            else:
                st.info("No Gemini API key — using template-based titles. Add a free key in the sidebar for AI-powered results.")
                result = generate_templates(gen_keyword.strip(), num_titles)

            if result and not result.startswith("Error"):
                st.markdown("---")
                for line in result.strip().split('\n'):
                    line = line.strip()
                    if line:
                        st.success(line)
            else:
                st.error(result)
