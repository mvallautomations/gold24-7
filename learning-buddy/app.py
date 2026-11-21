import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from learning import LESSONS, QUIZ
from progress import init_db, get_progress, save_lesson, save_quiz

st.set_page_config(page_title="Gold Trading Buddy", page_icon="🧭", layout="centered")
init_db()

st.title("🧭 Gold Trading Buddy")
st.caption("A small-step learning companion for understanding XAUUSD charts.")
st.info("Learning and historical simulation only. This app does not provide trading signals, financial advice, or broker execution.")

progress = get_progress()
completed = set(progress["completed"])
st.subheader("Your learning path")
col1, col2, col3 = st.columns(3)
col1.metric("Lessons completed", f"{len(completed)} / {len(LESSONS)}")
col2.metric("Quiz points", progress["points"])
col3.metric("Current level", "Starter" if len(completed) < 3 else "Explorer" if len(completed) < 7 else "Chart Student")
st.progress(len(completed) / len(LESSONS))

tab1, tab2, tab3 = st.tabs(["📚 Learn", "🧩 Quick quiz", "📈 Chart practice"])

with tab1:
    st.subheader("One idea at a time")
    lesson_names = [f'{i+1}. {x["title"]}' for i, x in enumerate(LESSONS)]
    choice = st.selectbox("Choose a short lesson", lesson_names)
    idx = lesson_names.index(choice)
    lesson = LESSONS[idx]
    st.markdown(f"### {lesson['title']}")
    st.write(lesson["eli10"])
    st.markdown("**What to look for**")
    for item in lesson["look_for"]:
        st.markdown(f"- {item}")
    st.warning(f"**Common mistake:** {lesson['mistake']}")
    if idx in completed:
        st.success("Lesson completed")
    elif st.button("Mark lesson complete", type="primary"):
        save_lesson(idx)
        st.success("Lesson saved. Small steps count.")
        st.rerun()

with tab2:
    st.subheader("Check what you learned")
    q = st.selectbox("Pick a question", list(QUIZ.keys()))
    item = QUIZ[q]
    answer = st.radio("Your answer", item["choices"], index=None, key=f"quiz_{q}")
    if st.button("Check answer", disabled=answer is None):
        correct = answer == item["answer"]
        save_quiz(10 if correct else 0)
        if correct:
            st.success("Correct! +10 learning points.")
        else:
            st.warning(f"Not quite. {item['why']}")
        st.caption(f"Explanation: {item['why']}")

with tab3:
    st.subheader("Practice reading a chart")
    st.write("Upload an OHLC CSV with columns: time, open, high, low, close. Volume is optional.")
    uploaded = st.file_uploader("Choose historical CSV", type=["csv"])
    if uploaded:
        try:
            df = pd.read_csv(uploaded)
            required = {"time", "open", "high", "low", "close"}
            if not required.issubset(set(df.columns.str.lower())):
                st.error("CSV needs time, open, high, low, close columns.")
            else:
                df.columns = [c.lower() for c in df.columns]
                df["time"] = pd.to_datetime(df["time"], errors="coerce")
                for col in ["open", "high", "low", "close"]:
                    df[col] = pd.to_numeric(df[col], errors="coerce")
                df = df.dropna(subset=["time","open","high","low","close"]).tail(500)
                if df.empty:
                    st.error("No valid OHLC rows found.")
                else:
                    fig = go.Figure(go.Candlestick(x=df.time, open=df.open, high=df.high, low=df.low, close=df.close, name="Historical price"))
                    fig.update_layout(height=480, xaxis_rangeslider_visible=False, title="Historical candlesticks")
                    st.plotly_chart(fig, use_container_width=True)
                    st.caption(f"Showing {len(df)} historical candles. Use this to practise describing structure; the chart does not generate buy/sell instructions.")
        except Exception as exc:
            st.error(f"Could not read this CSV: {exc}")
    else:
        st.caption("No file? Start with the lessons and quizzes. A sample dataset can be added later.")

st.divider()
st.caption("Built for focused 5–10 minute learning sessions. No streak pressure, no live execution.")
