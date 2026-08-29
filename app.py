import streamlit as st
from google import genai
from google.genai import types
from streamlit_mic_recorder import mic_recorder
import json
import random
import time

st.set_page_config(page_title="Charisma & Banter Lab", layout="centered")

# Initialize Gemini Client
api_key = st.secrets.get("GEMINI_API_KEY")
if not api_key:
    st.error("API Key missing. Please add GEMINI_API_KEY in Streamlit App Settings -> Secrets.")
    st.stop()

clean_key = str(api_key).strip().strip('"').strip("'")
client = genai.Client(api_key=clean_key)

# Failover models to eliminate 503 errors completely
MODEL_CASCADE = [
    "gemini-2.5-flash",
    "gemini-2.5-pro",
    "gemini-1.5-flash",
    "gemini-1.5-pro"
]

def fast_call(prompt, is_json=False):
    """Ultra-fast call with automatic multi-model failover."""
    last_err = None
    for model_name in MODEL_CASCADE:
        try:
            cfg = types.GenerateContentConfig(
                response_mime_type="application/json" if is_json else None,
                max_output_tokens=60 if not is_json else 800,
                temperature=0.7 if not is_json else 0.2
            )
            resp = client.models.generate_content(
                model=model_name,
                contents=prompt,
                config=cfg
            )
            if resp and resp.text:
                return resp.text.strip()
        except Exception as e:
            last_err = e
            continue
    raise last_err

# Scenarios Library
SCENARIO_POOLS = {
    "Level 1: The Casual Line Opener (Low Stakes)": {
        "instructions": "Keep replies strictly under 1-2 punchy sentences. React naturally to observations and situational humor. Do not interrogate. Stay strictly in character.",
        "settings": [
            "You are waiting in a slow morning line at an artisanal espresso bar where the barista is meticulously hand-pouring every order.",
            "You are browsing the new release non-fiction table at an independent neighborhood bookstore on a rainy afternoon.",
            "You are standing in a long line at a popular Sunday morning bagel bakery watching the chaotic kitchen staff.",
            "You are sitting on a park bench holding an iced coffee while watching an unruly pack of dogs play at the dog park.",
            "You are standing by the baggage carousel at an airport waiting for luggage to appear.",
            "You are looking at artisanal sourdough loaves at a Saturday morning farmers market stand.",
            "You are waiting for the elevator in the lobby of a modern co-working office building on a Friday afternoon.",
            "You are holding a shopping basket waiting in the express checkout lane at a crowded gourmet grocery store.",
            "You are waiting for your car at a busy suburban car wash viewing area.",
            "You are standing in line at a food truck festival trying to decide between two complicated fusion taco menus.",
            "You are browsing plants and succulents in the greenhouse section of a garden nursery.",
            "You are waiting in the pickup line at a busy downtown juice and smoothie bar.",
            "You are standing on a sunny train platform waiting for the morning commuter express train."
        ]
    },
    "Level 2: The Gallery Mixer (Neutral Ground)": {
        "instructions": "Keep replies under 2 sentences. Reward playful assumptions, challenge boring clichés, match the user's banter.",
        "settings": [
            "You are standing in front of an abstract, confusing modern sculpture at a gallery opening, holding a glass of sparkling water.",
            "You are browsing rare vintage vinyl records at a local weekend pop-up fair.",
            "You are browsing items at a silent charity auction while sipping champagne.",
            "You are tasting boutique extra-virgin olive oils at a specialty food festival booth.",
            "You are examining mid-century modern furniture pieces at a curated architectural flea market.",
            "You are standing in the courtyard at a historic botanical garden during an evening members-only event.",
            "You are attending an outdoor screening of an indie film sitting on a picnic blanket with wine.",
            "You are standing near the appetizer spread at an alumni evening gathering.",
            "You are browsing an artisan watch and craft leather market in an open-air pavilion.",
            "You are waiting for a photography exhibit lecture to begin in a museum auditorium lobby.",
            "You are sampling micro-batch cheeses at a gourmet food and wine expo.",
            "You are browsing rare vintage books at an antiquarian book fair.",
            "You are checking out handcrafted ceramics at a local studio open house."
        ]
    },
    "Level 3: The Dinner Party / Mutual Friends (Warm Social Dynamics)": {
        "instructions": "Respond well to funny observations about the food/host, playful assumptions about how people know each other, and lively storytelling. Max 2 short sentences.",
        "settings": [
            "You are a close friend of the host sitting across the table at an intimate eight-person suburban dinner party.",
            "You are hanging around the kitchen island at a friend's housewarming party helping open wine bottles.",
            "You are sitting around a backyard fire pit at an evening get-together with mutual acquaintances.",
            "You are sharing a long communal wooden table at a scenic hillside vineyard on a sunny afternoon.",
            "You are sitting at a chef's counter group tasting dinner where the courses are getting progressively theatrical.",
            "You are helping clean up dessert plates in the kitchen while laughing about the host's burnt entree.",
            "You are hanging out on the deck at a summer lake house barbecue with a casual group of friends.",
            "You are sitting on a patio sectional at a mutual friend's birthday tapas dinner.",
            "You are attending a family-style Italian Sunday supper at a bustling neighborhood trattoria.",
            "You are sitting around a fondue pot at a winter cabin ski weekend dinner.",
            "You are hanging out by the grill with a drink while the host attempts to smoke a brisket.",
            "You are tasting blindfolded wines at a casual friend group wine-tasting party.",
            "You are sitting at a rooftop communal dinner table watching the city skyline as dinner winds down."
        ]
    },
    "Level 4: The Music Festival / Concert (High Energy, Fast Calibration)": {
        "instructions": "Keep replies extremely brief (1 punchy sentence, max 15 words). Match high enthusiasm. React well to situational comments.",
        "settings": [
            "You are standing near the soundboard between sets at a crowded indoor indie rock venue.",
            "You are waiting in a slow beverage line on the lawn at an outdoor summer amphitheater festival.",
            "You are leaning against the balcony railing at an electronic dance music venue between artist sets.",
            "You are sitting at a small front-row table at an intimate late-night jazz club while the quartet takes a short break.",
            "You are cooling off on the outdoor smoking patio of an underground warehouse music show.",
            "You are standing near the stage rail waiting for the headline band to take the stage at a packed theater.",
            "You are grabbing a slice of late-night pizza at the concession stand inside a historic music hall.",
            "You are standing by the merch booth looking at vintage band tour t-shirts after a loud rock set.",
            "You are waiting for friends near the hydration station at a massive multi-stage music festival.",
            "You are hanging out in the mezzanine lounge of a concert venue holding two overpriced craft beers.",
            "You are sitting on the grass hill at an afternoon bluegrass festival listening to the opening act.",
            "You are standing in the lobby of an acoustic concert hall at intermission discussing the performance.",
            "You are watching the DJ set up gear from the edge of the dance floor at a rooftop sunset party."
        ]
    },
    "Level 5: The Fitness Class / Gym (Low Friction, Non-Intrusive)": {
        "instructions": "Keep replies concise and grounded (max 2 short sentences). Appreciate self-amused commiseration, dislike try-hard pickup lines.",
        "settings": [
            "You are wiping down a barbell station after completing a brutal conditioning circuit class, catching your breath.",
            "You are refilling a water bottle near the turf sprinting area between heavy sled pushes.",
            "You are rolling out your back on a foam roller in the gym mobility corner after a tough lifting session.",
            "You are putting away heavy dumbbells on the rack after finishing a set of shoulder presses.",
            "You are stretching near the door after a demanding hot yoga or power Pilates session.",
            "You are adjusting your indoor cycling bike pedals before a spin class begins.",
            "You are taking a short breather on a plyo box between rowing machine intervals.",
            "You are chalking your hands at the pull-up rig while resting between calisthenics sets.",
            "You are stepping out of the infrared sauna and sitting on the relaxation bench in a wellness studio.",
            "You are waiting for the cold plunge tub to open up after a heavy leg workout.",
            "You are tightening your lifting belt near the squat rack while switching weight plates.",
            "You are untying your running shoes on a locker room bench after an outdoor track workout.",
            "You are mixing a protein shaker bottle at the smoothie counter of a boutique climbing gym."
        ]
    },
    "Level 6: The Lounge (Flirtatious & High Polarity)": {
        "instructions": "Respond well to confident frame-flipping and light teasing. Never be rude; maintain high social warmth. Max 2 punchy sentences.",
        "settings": [
            "You are waiting for the bartender at a crowded, dimly lit speakeasy cocktail lounge on a Friday night.",
            "You are sitting on a plush leather sofa at an upscale hotel bar enjoying an Old Fashioned.",
            "You are leaning on the railing of a crowded rooftop bar enjoying a summer sunset drink.",
            "You are standing near the oyster bar at an energetic coastal seafood tavern during happy hour.",
            "You are sitting at a candlelit high-top table at a vibrant tapas and mezcal bar.",
            "You are browsing the cocktail menu at an intimate velvet-draped piano bar.",
            "You are waiting for a table at the bar of a buzzing Michelin-starred downtown bistro.",
            "You are standing near the fireplace lounge of an alpine ski resort bar after a day on the slopes.",
            "You are ordering a bespoke botanical gin and tonic at a garden terrace lounge.",
            "You are sharing bar space while waiting for a glass of natural wine at a lively neighborhood enoteca.",
            "You are leaning against a marble cocktail counter watching a mixologist carve clear ice blocks.",
            "You are sitting in the courtyard lounge of a boutique hotel with a late-night cocktail.",
            "You are standing by the DJ booth at an upscale after-work lounge listening to deep house music."
        ]
    },
    "Level 7: The Skeptical Stranger (Frame Control)": {
        "instructions": "Start with concise, slightly dry/skeptical replies. Only warm up if the user uses genuine warmth, self-amusement, and observational play. Max 2 sentences.",
        "settings": [
            "You are sitting at an airport departure gate on a three-hour flight delay reading a dense novel, looking tired.",
            "You are sitting alone with a laptop in a quiet hotel lobby bar catching up on work emails.",
            "You are waiting for a delayed commuter train on a freezing winter evening platform, looking unenthusiastic.",
            "You are waiting in a slow line at the post office holding three heavy cardboard boxes.",
            "You are sitting on an airplane in the window seat while boarding is stalled in the aisle.",
            "You are browsing an aisle at the pharmacy while waiting for a prescription order to be filled.",
            "You are waiting in a hotel check-in line where the computer system is currently frozen.",
            "You are sitting at an auto service center waiting room reading magazines while your car is inspected.",
            "You are standing in line at the passport renewal office clutching a stack of paperwork.",
            "You are sitting on a park bench working on a tablet, looking focused and slightly guarded.",
            "You are waiting for takeout food at a crowded restaurant counter where orders are running late.",
            "You are standing near the coat check line at a large conference hall at the end of a long seminar day.",
            "You are waiting for an elevator in a silent medical office building hallway."
        ]
    }
}

# State Management Initialization
if "level" not in st.session_state:
    st.session_state.level = list(SCENARIO_POOLS.keys())[0]
if "current_setting" not in st.session_state:
    st.session_state.current_setting = random.choice(SCENARIO_POOLS[st.session_state.level]["settings"])
if "transcript" not in st.session_state:
    st.session_state.transcript = []
if "reaction_times" not in st.session_state:
    st.session_state.reaction_times = []
if "active_timer_start" not in st.session_state:
    st.session_state.active_timer_start = None
if "evaluation" not in st.session_state:
    st.session_state.evaluation = None

pairs_count = len(st.session_state.transcript) // 2

# Header Layout
top_col1, top_col2 = st.columns([3, 1])
with top_col1:
    st.title("⚡ Charisma & Banter Lab")
    st.caption("Sub-second conversational sparring with precision latency tracking.")
with top_col2:
    st.write("")
    if st.button("🔄 Reset Scenario", use_container_width=True):
        st.session_state.transcript = []
        st.session_state.reaction_times = []
        st.session_state.evaluation = None
        st.session_state.current_setting = random.choice(SCENARIO_POOLS[st.session_state.level]["settings"])
        st.session_state.active_timer_start = None
        st.rerun()

# Level Selection
selected_level = st.selectbox("Select Training Scenario Tier:", list(SCENARIO_POOLS.keys()))
if selected_level != st.session_state.level:
    st.session_state.level = selected_level
    st.session_state.current_setting = random.choice(SCENARIO_POOLS[selected_level]["settings"])
    st.session_state.transcript = []
    st.session_state.reaction_times = []
    st.session_state.evaluation = None
    st.session_state.active_timer_start = None
    st.rerun()

st.info(f"📍 **Setting:** {st.session_state.current_setting}")

# Dialogue Stream Display
for turn in st.session_state.transcript:
    if turn["role"] == "user":
        latency_str = f" *(⚡ {turn['latency']:.1f}s)*" if turn.get("latency") is not None else " *(Opener)*"
        st.chat_message("user").write(f"{turn['text']}{latency_str}")
    else:
        st.chat_message("assistant").write(turn["text"])

# Interaction Zone (Max 4 full exchanges)
if pairs_count < 4:
    st.write("---")
    exchange_label = "Opener" if pairs_count == 0 else f"Exchange {pairs_count + 1} of 4"
    st.write(f"**Your Turn ({exchange_label}):**")
    
    col_mic, col_text = st.columns([1, 2])
    
    with col_mic:
        audio_record = mic_recorder(
            start_prompt="🔴 Record Mic",
            stop_prompt="⏹️ Send Audio",
            key=f"mic_rec_{pairs_count}",
            format="webm"
        )
        
    with col_text:
        with st.form(key=f"text_input_form_{pairs_count}", clear_on_submit=True):
            typed_message = st.text_input("Type your banter line here:", placeholder="Deliver your observation quickly...")
            send_btn = st.form_submit_button("Send Line ⚡", use_container_width=True)

    user_line = None
    calculated_latency = None

    # Precise Stopwatch Capture
    if send_btn and typed_message:
        now = time.time()
        if pairs_count > 0 and st.session_state.active_timer_start is not None:
            calculated_latency = max(0.5, round(now - st.session_state.active_timer_start, 1))
        user_line = typed_message.strip()
    elif audio_record and "bytes" in audio_record and audio_record["bytes"]:
        now = time.time()
        if pairs_count > 0 and st.session_state.active_timer_start is not None:
            calculated_latency = max(0.5, round(now - st.session_state.active_timer_start, 1))
        with st.spinner("⚡ Transcribing..."):
            try:
                user_line = fast_call([
                    types.Part.from_bytes(data=audio_record["bytes"], mime_type="audio/webm"),
                    "Transcribe spoken English accurately. Output ONLY transcription text."
                ])
            except Exception as e:
                st.error(f"Transcription Error: {str(e)}")

    # Fast Generation
    if user_line:
        if calculated_latency is not None:
            st.session_state.reaction_times.append(calculated_latency)
            
        temp_history = list(st.session_state.transcript)
        temp_history.append({"role": "user", "text": user_line, "latency": calculated_latency})
        
        dialogue_str = "\n".join([f"{t['role'].upper()}: {t['text']}" for t in temp_history])
        persona_prompt = f"""
        Scenario: {st.session_state.current_setting}
        Rules: {SCENARIO_POOLS[st.session_state.level]['instructions']}

        Dialogue History:
        {dialogue_str}

        Respond strictly in character as the other person. Keep it under 2 punchy, natural sentences.
        """
        
        try:
            partner_reply = fast_call(persona_prompt)
            
            # Append turns to state
            st.session_state.transcript.append({"role": "user", "text": user_line, "latency": calculated_latency})
            st.session_state.transcript.append({"role": "assistant", "text": partner_reply})
            
            # Start timer strictly when partner reply completes
            st.session_state.active_timer_start = time.time()
            st.rerun()
        except Exception as e:
            st.error(f"Partner Response Error: {str(e)}")

else:
    # Round Complete - Evaluation Section
    valid_times = [t for t in st.session_state.reaction_times if t is not None]
    avg_latency = round(sum(valid_times) / len(valid_times), 1) if valid_times else 3.0
    st.success(f"🎉 Drill Complete! (Average Reaction Latency: {avg_latency}s)")
    
    if st.session_state.evaluation is None:
        if st.button("📊 Generate Charisma & Speed Scorecard", use_container_width=True):
            with st.spinner("Analyzing banter dynamics and reaction pace..."):
                transcript_block = "\n".join([
                    f"{t['role'].upper()} ({t.get('latency', 'Opener')}s): {t['text']}" if t['role'] == 'user' else f"{t['role'].upper()}: {t['text']}"
                    for t in st.session_state.transcript
                ])
                critic_prompt = f"""
                You are a world-class conversational dynamics and charisma coach.
                Analyze this transcript for Scenario: {st.session_state.current_setting}
                Level Tier: {st.session_state.level}
                User Average Latency (Exchanges 2-4): {avg_latency} seconds

                [TRANSCRIPT]
                {transcript_block}

                Evaluate the User based on:
                1. Spontaneity & Speed Score (1-10): (<3.5s = 10, 3.5-6s = 8-9, 6-10s = 5-7, >10s = <5)
                2. Outcome Independence (Self-amusement vs. approval-seeking)
                3. Playfulness & Frame Control (Playful assumptions vs. boring interview questions)
                4. Brevity & Punchiness (Brevity vs rambling)
                5. Warmth & Calibration (Charming vs try-hard or cold)

                Return valid JSON matching this schema:
                {{
                  "scores": {{
                    "spontaneity_and_speed": 9,
                    "outcome_independence": 8,
                    "playfulness": 7,
                    "brevity": 9,
                    "warmth": 8,
                    "overall_score": 8.2
                  }},
                  "avg_latency_seconds": {avg_latency},
                  "verdict": "Passed / Needs More Reps",
                  "strengths": ["string"],
                  "weaknesses": ["string"],
                  "best_turn_upgrade": {{
                    "original": "string",
                    "upgraded": "string",
                    "reason": "string"
                  }},
                  "speed_critique": "string",
                  "key_takeaway": "string"
                }}
                """
                try:
                    eval_raw = fast_call(critic_prompt, is_json=True)
                    clean_json = eval_raw.strip().removeprefix("```json").removeprefix("```").removesuffix("```").strip()
                    st.session_state.evaluation = json.loads(clean_json)
                    st.rerun()
                except Exception as e:
                    st.error(f"Scoring Error: {str(e)}")

    if st.session_state.evaluation:
        ev = st.session_state.evaluation
        st.subheader(f"Overall Rating: {ev['scores']['overall_score']} / 10 ({ev['verdict']})")
        
        m1, m2, m3, m4, m5 = st.columns(5)
        m1.metric("Spontaneity", f"{ev['scores']['spontaneity_and_speed']}/10", f"{ev.get('avg_latency_seconds', avg_latency)}s avg")
        m2.metric("Independence", f"{ev['scores']['outcome_independence']}/10")
        m3.metric("Playfulness", f"{ev['scores']['playfulness']}/10")
        m4.metric("Brevity", f"{ev['scores']['brevity']}/10")
        m5.metric("Warmth", f"{ev['scores']['warmth']}/10")
        
        st.write("### ⚡ Spontaneity & Timing Breakdown")
        st.write(ev.get("speed_critique", f"Average reaction latency across exchanges: **{avg_latency} seconds**."))
        
        st.write("### 💡 Strengths & Weaknesses")
        for s in ev.get("strengths", []):
            st.write(f"✅ {s}")
        for w in ev.get("weaknesses", []):
            st.write(f"⚠️ {w}")
            
        if "best_turn_upgrade" in ev and ev["best_turn_upgrade"]:
            st.write("### 🚀 Upgraded Line Alternative")
            st.write(f"**Instead of:** *\"{ev['best_turn_upgrade'].get('original', '')}\"*")
            st.write(f"**Try saying:** **\"{ev['best_turn_upgrade'].get('upgraded', '')}\"**")
            st.caption(f"**Why:** {ev['best_turn_upgrade'].get('reason', '')}")
        
        st.info(f"**Anchor for next round:** {ev.get('key_takeaway', '')}")

        if st.button("🔄 Start New Drill", use_container_width=True):
            st.session_state.transcript = []
            st.session_state.reaction_times = []
            st.session_state.evaluation = None
            st.session_state.current_setting = random.choice(SCENARIO_POOLS[st.session_state.level]["settings"])
            st.session_state.active_timer_start = None
            st.rerun()
