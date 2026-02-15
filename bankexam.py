import streamlit as st
import pandas as pd
import numpy as np
import time
import os
import base64

# --- STEP 0: CONFIG & LOGO ---
st.set_page_config(page_title="Bank Exam DPP", layout="wide")

def get_base64_of_bin_file(bin_file):
    with open(bin_file, 'rb') as f:
        data = f.read()
    return base64.b64encode(data).decode()

def inject_logo(img_path):
    if os.path.exists(img_path):
        bin_str = get_base64_of_bin_file(img_path)
        st.markdown(
            f"""
            <style>
            .logo-container {{
                position: fixed;
                top: 100px;
                right: 50px;
                z-index: 1000;
            }}
            </style>
            <div class="logo-container">
                <img src="data:image/jpeg;base64,{bin_str}" width="180">
            </div>
            """,
            unsafe_allow_html=True
        )
    else:
        st.sidebar.warning(f"Logo file '{img_path}' not found in directory.")

excel_name = "Banking Data - DPP 1 Banking.csv"
logo_path = "Civils Notebook Logo.jpeg"

@st.cache_data
def load_data():
    if not os.path.exists(excel_name):
        st.error(f"File {excel_name} not found! Please ensure it is in the same folder.")
        return pd.DataFrame()
    return pd.read_csv(excel_name)

df = load_data()

# --- STEP 1: INITIALIZE STATE ---
if 'started' not in st.session_state:
    st.session_state.update({
        'started': False,
        'answered': [],
        'results_history': [],
        'ability': -3.0,
        'ability_max': 0.0,
        'q_count': 1,
        'total_q': 10,
        'current_q_data': None,
        'test_complete': False,
        'start_time': 0
    })

# --- STEP 2: LOGIC ---
def handle_submit(choice, final_time):
    q = st.session_state.current_q_data
    is_correct = (choice == q['correct_option'])
    
    # Adaptive Step Logic (From original code)
    step = 0.8 * (1 - (st.session_state.q_count / (st.session_state.total_q + 2)))
    st.session_state.ability += step if is_correct else -step
    st.session_state.ability_max += step
    
    # Data Mapping
    col_map = {'A': 'option_a', 'B': 'option_b', 'C': 'option_c', 'D': 'option_d' , 'E': 'option_e'}
    
    # Error Tagging Logic
    is_overtime = final_time > q.get('expected_time', 60)
    is_guess = final_time < q.get('minimum_time', 5)
    
    if is_guess: error_tag = "Rapid Guess"
    elif is_correct: error_tag = "N/A (Correct)"
    else:
        if q['difficulty_level'] < (st.session_state.ability - 0.5): error_tag = "Silly Mistake"
        elif q['difficulty_level'] > (st.session_state.ability + 0.5): error_tag = "Reach Question"
        else: error_tag = "Fundamental Gap"

    # Save to history
    st.session_state.results_history.append({
        'num': st.session_state.q_count,
        'full_question': q['question'],
        'diff': q['difficulty_level'],
        'user_ans': choice,
        'user_val': q[col_map[choice]],
        'correct_ans': q['correct_option'],
        'correct_val': q[col_map[q['correct_option']]],
        'is_correct': is_correct,
        'time': final_time,
        'expected_time': q.get('expected_time', 60),
        'min_time': q.get('minimum_time', 5),
        'is_overtime': is_overtime,
        'is_guess': is_guess,
        'error_tag': error_tag,
        'chapter' : q['Chapter']
    })

    st.session_state.answered.append(q['question_id'])
    st.session_state.q_count += 1
    st.session_state.current_q_data = None 
    
    if st.session_state.q_count > st.session_state.total_q:
        st.session_state.test_complete = True
    st.rerun()

# --- STEP 3: UI RENDERING ---
inject_logo(logo_path)

# LANDING PAGE
if not st.session_state.started:
    st.title("Bank Exam DPP")
    st.subheader("Adaptive Diagnostic - Full Analytics Suite")
    
    st.markdown("""
    ---
    **Instructions:**
    * Daily Practice Problems
    * **Total Questions:** 10
    * **Behavior analytics** (speed/guessing) is active.
    ---
    """)
    
    if st.button("START TEST", type="primary", use_container_width=True):
        st.session_state.started = True
        st.rerun()

# TEST INTERFACE
elif not st.session_state.test_complete:
    col_info, col_timer = st.columns([3, 1])
    
    if st.session_state.current_q_data is None:
        available = df[~df['question_id'].isin(st.session_state.answered)].copy()
        if available.empty:
            st.session_state.test_complete = True
            st.rerun()
        distances = (available['difficulty_level'] - st.session_state.ability).abs()
        st.session_state.current_q_data = available.loc[distances.idxmin()]
        st.session_state.start_time = time.time()

    q = st.session_state.current_q_data
    col_info.write(f"**QUESTION {st.session_state.q_count} OF {st.session_state.total_q}**")
    col_info.info(f"ESTIMATED ABILITY: **{st.session_state.ability:.2f}**")
    
    # Live Timer
    timer_placeholder = col_timer.empty()
    elapsed = int(time.time() - st.session_state.start_time)
    t_color = "red" if elapsed > q.get('expected_time', 60) else "green"
    timer_placeholder.markdown(f"### :{t_color}[Time: {elapsed}s]")

    st.divider()
    st.write(f"#### {q['question']}")

    for char in ['A', 'B', 'C', 'D','E']:
        if st.button(f"{char}: {q[f'option_{char.lower()}']}", use_container_width=True):
            final_duration = round(time.time() - st.session_state.start_time, 1)
            handle_submit(char, final_duration)

    time.sleep(1)
    st.rerun()

# REVIEW SCREEN
else:
    st.title("DIAGNOSTIC PERFORMANCE REVIEW")
    
    # ACCURACY TO DIFFICULTY CALCULATION
    total_correct = sum(1 for res in st.session_state.results_history if res['is_correct'])
    accuracy_pct = (total_correct / st.session_state.total_q) * 100
    # Formula: 0% accuracy = +3 score, 100% accuracy = -3 score
    difficulty_scaling_score = 3 - (accuracy_pct * 0.06)
    
    # 1. Scorecard
    c1, c2, c3 = st.columns(3)
    c1.metric("Final Adaptive Ability", f"{st.session_state.ability:.2f}")
    c2.metric("Accuracy Rate", f"{accuracy_pct:.0f}%")
    c3.metric("Difficulty Score", f"{difficulty_scaling_score:.2f}")

    # 2. Strategic Interpretation
    advice = "Elite level logic. Maintain speed." if st.session_state.ability > 1.5 else "Review foundational gaps."
    st.info(f"**Strategic Interpretation:** {advice}")

    # 3. Summary Table
    stats = {
        "Foundational (<-1)": {"correct": 0, "wrong": 0, "time_c": 0.0, "time_w": 0.0, "ovr": 0, "guesses": 0},
        "Intermediate (±1)":  {"correct": 0, "wrong": 0, "time_c": 0.0, "time_w": 0.0, "ovr": 0, "guesses": 0},
        "Advanced (>1)":      {"correct": 0, "wrong": 0, "time_c": 0.0, "time_w": 0.0, "ovr": 0, "guesses": 0}
    }
    for res in st.session_state.results_history:
        cat = "Foundational (<-1)" if res['diff'] < 0.0 else "Advanced (>1)" if res['diff'] > 1.0 else "Intermediate (±1)"
        if res['is_correct']:
            stats[cat]["correct"] += 1
            stats[cat]["time_c"] += res['time']
        else:
            stats[cat]["wrong"] += 1
            stats[cat]["time_w"] += res['time']
        if res['is_overtime']: stats[cat]["ovr"] += 1
        if res['is_guess']: stats[cat]["guesses"] += 1

    summary_list = []
    for cat, d in stats.items():
        total = d['correct'] + d['wrong']
        summary_list.append({
            "DIFFICULTY": cat, "CORRECT": d['correct'], "WRONG": d['wrong'],
            "AVG TIME(C)": f"{d['time_c']/(d['correct'] or 1):.1f}s",
            "AVG TIME(W)": f"{d['time_w']/(d['wrong'] or 1):.1f}s",
            "GUESSES": d['guesses'], "OVERTIME %": f"{(d['ovr']/(total or 1))*100:.1f}%"
        })
    st.table(pd.DataFrame(summary_list))

    # 4. Filter Controls
    st.divider()
    st.subheader("Detailed Audit Log")
    f1, f2, f3, f4 = st.columns(4)
    f_correct = f1.checkbox("Show Correct", value=True)
    f_wrong = f2.checkbox("Show Incorrect", value=True)
    f_overtime = f3.checkbox("Overtime Only", value=False)
    f_guess = f4.checkbox("Guesses Only", value=False)

    # 5. Render Audit Logs
    for res in st.session_state.results_history:
        show_acc = (res['is_correct'] and f_correct) or (not res['is_correct'] and f_wrong)
        show_time = (not f_overtime) or res['is_overtime']
        show_gs = (not f_guess) or res['is_guess']
        show_diff = "Foundational (<-1)" if res['diff'] < -1.0 else "Advanced (>1)" if res['diff'] > 1.0 else "Intermediate (±1)"
        
        if show_acc and show_time and show_gs :
            color = "green" if res['is_correct'] else "red"
            status = "✅" if res['is_correct'] else "❌"
            with st.expander(f"{status} Q#{res['num']} | Time: {res['time']}s | {res['error_tag']} | Difficulty level: {show_diff} | Chapter: {res['chapter']}"):
                st.write(f"**Question:** {res['full_question']}")
                st.markdown(f"**User Ans:** :{color}[{res['user_val']}] | **Correct:** {res['correct_val']}")
                if res['is_overtime']: st.warning("Note: Overtime response.")
                if res['is_guess']: st.error("Note: Tagged as Rapid Guess.")

    if st.button("Exit and Restart"):
        st.session_state.clear()
        st.rerun()