import streamlit as st
from google import genai
from google.genai import types
from streamlit_mic_recorder import mic_recorder
import json
import io

st.set_page_config(page_title="Charisma & Banter Lab", layout="centered")

# Initialize Gemini Client
api_key = st.secrets.get("GEMINI_API_KEY")
if not api_key:
    st.error("API Key missing. Please add GEMINI_API_KEY in Streamlit App Settings -> Secrets.")
    st.stop()

client = genai.Client(api_key=api_key)

# All Scenarios Dictionary
SCENARIOS = {
    "Level 1: The Casual Line Opener (Low Stakes)": {
        "context": "You are a warm, slightly witty stranger standing in line at a busy boutique coffee shop.",
        "instructions": "Keep replies under 2 sentences. React naturally to observations and humor. Do not interrogate. Stay strictly in character."
    },
    "Level 2: The Gallery Mixer (Neutral Ground)": {
        "context": "You are an attendee at an art gallery opening with a dry, understated sense of humor.",
        "instructions": "Keep replies under 2 sentences. Reward playful assumptions, challenge boring clichés, match the user's banter."
    },
    "Level 3: The Dinner Party / Mutual Friends (Warm Social Dynamics)": {
        "context": "You are a friend of the host sitting across the table at an intimate dinner party. You are socially savvy, expressive, and enjoy light group storytelling.",
        "instructions": "Respond well to funny observations about the food/host, playful assumptions about how people know each other, and lively storytelling. Keep spoken replies under 2-3 sentences."
    },
    "Level 4: The Music Festival / Concert (High Energy, Fast Calibration)": {
        "context": "You are standing near the stage/drink line between sets at a live music concert. The vibe is loud, spontaneous, and high-energy.",
        "instructions": "Keep replies extremely brief (1-2 punchy sentences). Match the high enthusiasm. React well to situational comments about the crowd, the band, or terrible drink prices."
    },
    "Level 5: The Fitness Class / Gym (Low Friction, Non-Intrusive)": {
        "context": "You are wiping down equipment after a challenging group fitness workout, slightly out of breath.",
        "instructions": "Initially give brief, focused replies. You appreciate self-amused commiseration about the brutal workout, but dislike overly eager or try-hard pickup attempts. Only warm up if the banter is low-pressure, grounded, and concise."
    },
    "Level 6: The Lounge (Flirtatious & High Polarity)": {
        "context": "You are a quick-witted, attractive patron enjoying a cocktail at a vibrant lounge.",
        "instructions": "Respond well to confident frame-flipping and light teasing. Never be rude; maintain high social warmth. Max 2 punchy sentences."
    },
    "Level 7: The Skeptical Stranger (Frame Control)": {
        "context": "You are sitting at an airport lounge reading, slightly tired and guarded.",
        "instructions": "Start with concise, slightly dry/skeptical replies. Only warm up if the user uses genuine warmth, self-amusement, and observational play."
    }
}

# State Management
if "level" not in st.session_state:
    st.session_state.level = list(SCENARIOS.keys())[0]
if "transcript" not in st.session_state:
    st.session_state.transcript = []
if "turn_count" not in st.session_state:
    st.session_state.turn_count = 0
if "evaluation" not in st.session_state:
    st.session_state.evaluation = None

st.title("🎙️ Charisma & Banter Lab")
st.caption("Audio-first dynamic conversational sparring with instant charisma scoring.")

selected_level = st.selectbox("Select Training Scenario:", list(SCENARIOS.keys()))
if selected_level != st.session_state.level:
    st.session_state.level = selected_level
    st.session_state.transcript = []
    st.session_state.turn_count = 0
    st.session_state.evaluation = None
    st.rerun()

st.info(f"**Setting:** {SCENARIOS[st.session_state.level]['context']}")

# Render Chat History
for turn in st.session_state.transcript:
    if turn["role"] == "user":
        st.chat_message("user").write(turn["text"])
    else:
        with st.chat_message("assistant"):
            st.write(turn["text"])
            if "audio" in turn and turn["audio"]:
                st.audio(turn["audio"], format="audio/mp3")

# Turn Handling (Max 4 turns per drill)
if st.session_state.turn_count < 4:
    st.write("---")
    st.write(f"**Your Turn (Exchange {st.session_state.turn_count + 1} of 4):**")
    
    col1, col2 = st.columns([1, 2])
    with col1:
        audio_record = mic_recorder(
            start_prompt="🔴 Record Line",
            stop_prompt="⏹️ Send Line",
            key="mic_recorder",
            format="webm"
        )
    with col2:
        text_input = st.text_input("Or type line if mic is unavailable:", key="text_fallback")

    user_text = ""
    if audio_record and "bytes" in audio_record:
        with st.spinner("Listening..."):
            transcribe_resp = client.models.generate_content(
                model="gemini-2.5-flash",
                contents=[
                    types.Part.from_bytes(data=audio_record["bytes"], mime_type="audio/webm"),
                    "Transcribe the spoken English accurately. Output ONLY the transcription text without commentary."
                ]
            )
            user_text = transcribe_resp.text.strip()
    elif text_input and st.button("Send Typed Line"):
        user_text = text_input.strip()

    if user_text:
        st.session_state.transcript.append({"role": "user", "text": user_text})
        st.session_state.turn_count += 1

        # Generate In-Character Response
        with st.spinner("Responding..."):
            dialogue_history = "\n".join([f"{t['role'].upper()}: {t['text']}" for t in st.session_state.transcript])
            persona_prompt = f"""
            Scenario: {SCENARIOS[st.session_state.level]['context']}
            Rules: {SCENARIOS[st.session_state.level]['instructions']}

            Dialogue History:
            {dialogue_history}

            Respond in character as the other person.
            """
            response = client.models.generate_content(
                model="gemini-2.5-flash",
                contents=persona_prompt
            )
            partner_reply = response.text.strip()

            # Text to Speech using Gemini Audio output
            audio_bytes = None
            try:
                tts_resp = client.models.generate_content(
                    model="gemini-2.5-flash",
                    contents=f"Read this line aloud naturally with subtle vocal expression: {partner_reply}",
                    config=types.GenerateContentConfig(
                        response_mime_type="audio/mp3"
                    )
                )
                if tts_resp.candidates and tts_resp.candidates[0].content.parts:
                    for part in tts_resp.candidates[0].content.parts:
                        if hasattr(part, 'inline_data') and part.inline_data:
                            audio_bytes = part.inline_data.data
            except Exception:
                audio_bytes = None

            turn_data = {"role": "assistant", "text": partner_reply}
            if audio_bytes:
                turn_data["audio"] = audio_bytes
            
            st.session_state.transcript.append(turn_data)
            st.rerun()

else:
    # Round Complete - Evaluation Section
    st.success("🎉 Drill Complete (4 Exchanges Finished)!")
    
    if st.session_state.evaluation is None:
        if st.button("📊 Generate Charisma Scorecard"):
            with st.spinner("Analyzing banter dynamics..."):
                transcript_block = "\n".join([f"{t['role'].upper()}: {t['text']}" for t in st.session_state.transcript])
                critic_prompt = f"""
                You are a world-class conversational dynamics and charisma coach.
                Analyze this transcript for Level: {st.session_state.level}

                [TRANSCRIPT]
                {transcript_block}

                Evaluate the User based on:
                1. Outcome Independence (Self-amusement vs. approval-seeking)
                2. Playfulness & Frame Control (Playful assumptions vs. boring interview questions)
                3. Brevity & Punchiness (Brevity vs rambling)
                4. Warmth & Calibration (Charming vs try-hard or cold)

                Return valid JSON matching this schema:
                {{
                  "scores": {{
                    "outcome_independence": 8,
                    "playfulness": 7,
                    "brevity": 9,
                    "warmth": 8,
                    "overall_score": 8.0
                  }},
                  "verdict": "Passed / Needs More Reps",
                  "strengths": ["string"],
                  "weaknesses": ["string"],
                  "best_turn_upgrade": {{
                    "original": "string",
                    "upgraded": "string",
                    "reason": "string"
                  }},
                  "key_takeaway": "string"
                }}
                """
                eval_resp = client.models.generate_content(
                    model="gemini-2.5-flash",
                    contents=critic_prompt,
                    config=types.GenerateContentConfig(response_mime_type="application/json")
                )
                st.session_state.evaluation = json.loads(eval_resp.text)
                st.rerun()

    if st.session_state.evaluation:
        ev = st.session_state.evaluation
        st.subheader(f"Overall Rating: {ev['scores']['overall_score']} / 10 ({ev['verdict']})")
        
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Independence", f"{ev['scores']['outcome_independence']}/10")
        m2.metric("Playfulness", f"{ev['scores']['playfulness']}/10")
        m3.metric("Brevity", f"{ev['scores']['brevity']}/10")
        m4.metric("Warmth", f"{ev['scores']['warmth']}/10")
        
        st.write("### 💡 Strengths & Weaknesses")
        for s in ev["strengths"]:
            st.write(f"✅ {s}")
        for w in ev["weaknesses"]:
            st.write(f"⚠️ {w}")
            
        st.write("### 🚀 Upgraded Line Alternative")
        st.write(f"**Instead of:** *\"{ev['best_turn_upgrade']['original']}\"*")
        st.write(f"**Try saying:** **\"{ev['best_turn_upgrade']['upgraded']}\"**")
        st.caption(f"**Why:** {ev['best_turn_upgrade']['reason']}")
        
        st.info(f"**Anchor for next round:** {ev['key_takeaway']}")

        if st.button("🔄 Start New Drill"):
            st.session_state.transcript = []
            st.session_state.turn_count = 0
            st.session_state.evaluation = None
            st.rerun()
