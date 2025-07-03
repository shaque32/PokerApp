import streamlit as st
import pandas as pd
from datetime import datetime
from parser import ZelleMessageParser
from db import DatabaseManager

# Page configuration
st.set_page_config(
    page_title="Poker Buy-ins Manager", 
    layout="wide"
)

# Custom sleek/gambling-themed CSS
st.markdown(
    """
    <style>
    /* Dark gradient background */
    .stApp {
        background: linear-gradient(135deg, #1b2631 0%, #0d1b2a 100%);
        color: #f0f0f0;
    }
    /* Header styling */
    .poker-header {
        font-family: 'Helvetica Neue', sans-serif;
        color: #e63946;
        font-size: 2.5rem;
        font-weight: 300;
        text-align: center;
        margin: 1rem 0;
        letter-spacing: 2px;
    }
    /* Card containers */
    .card {
        background-color: rgba(255, 255, 255, 0.05);
        border: 1px solid rgba(255, 255, 255, 0.1);
        border-radius: 8px;
        padding: 1.5rem;
        margin-bottom: 2rem;
    }
    /* Button styling */
    .stButton>button {
        background-color: #e63946;
        color: #f0f0f0;
        font-weight: 500;
        border: none;
        border-radius: 4px;
        padding: 0.6rem 1.2rem;
        transition: background 0.3s;
    }
    .stButton>button:hover {
        background-color: #d62828;
    }
    /* Dataframe styling */
    .stDataFrame table {
        background-color: rgba(255, 255, 255, 0.1);
        color: #f0f0f0;
    }
    </style>
    """, unsafe_allow_html=True
)

# Main app
def main():
    st.markdown("<div class='poker-header'>♠️ Poker Buy-ins Manager ♥️</div>", unsafe_allow_html=True)
    db = DatabaseManager('poker.db')

    tabs = st.tabs(["Manage Sessions", "Add Buy-in", "Sessions", "Payouts", "Settlement"])

    # Manage Sessions
    with tabs[0]:
        st.markdown("<div class='card'>", unsafe_allow_html=True)
        st.subheader("🎴 Manage Sessions")
        sessions = db.list_sessions()
        if sessions:
            st.dataframe(pd.DataFrame(sessions))
        else:
            st.info("No sessions yet. Create one below.")
        # Create session
        name = st.text_input("New Session Name", key="new_session_name")
        if st.button("Create Session", key="btn_create_session") and name:
            db.create_session(name)
            st.success(f"Session '{name}' created.")
        # Clear all sessions
        if st.button("Clear All Sessions", key="btn_clear_sessions"):
            # Delete sessions, buyins, and payouts
            if hasattr(db, 'conn'):
                db.conn.execute("DELETE FROM payouts")
                db.conn.execute("DELETE FROM buyins")
                db.conn.execute("DELETE FROM sessions")
                db.conn.commit()
            else:
                # Fallback using DatabaseManager methods if available
                try:
                    db.clear_sessions()
                except Exception:
                    pass
            st.success("All sessions, buy-ins, and payouts cleared.")
        st.markdown("</div>", unsafe_allow_html=True)

    # Add Buy-in
    with tabs[1]:
        st.markdown("<div class='card'>", unsafe_allow_html=True)
        st.subheader("💰 Add Buy-in")
        sess_ids = [s['session_id'] for s in db.list_sessions()]
        if not sess_ids:
            st.warning("Please create a session first.")
        else:
            sel = st.selectbox("Session", sess_ids, key="sel_buyin_sess")
            mode = st.radio("Mode", ["Auto", "Manual"], key="buyin_mode")
            if mode == "Auto":
                msg = st.text_area("Zelle message", key="auto_msg")
                if st.button("Parse & Add", key="auto_add"):
                    rec = ZelleMessageParser.parse(msg)
                    if rec:
                        rec['session_id'] = sel
                        db.add_buyin(rec)
                        st.success(f"{rec['sender']} - $ {rec['amount']} added")
                    else:
                        st.error("Invalid message.")
            else:
                player = st.text_input("Player", key="man_player")
                amt = st.number_input("Amount", min_value=0.0, format="%.2f", key="man_amt")
                note = st.text_input("Notes", key="man_notes")
                if st.button("Add Buy-in", key="man_add"):
                    db.add_manual_buyin(sel, player, amt, datetime.now(), note)
                    st.success(f"{player} - $ {amt} added")
        st.markdown("</div>", unsafe_allow_html=True)

    # Sessions
    with tabs[2]:
        st.markdown("<div class='card'>", unsafe_allow_html=True)
        st.subheader("📋 Sessions")
        df_sess = pd.DataFrame(db.list_sessions())
        st.dataframe(df_sess)
        if not df_sess.empty:
            vs = st.selectbox("Select Session", df_sess['session_id'], key="vs_sess")
            df_b = pd.DataFrame(db.get_buyins(vs))
            st.dataframe(df_b)
        st.markdown("</div>", unsafe_allow_html=True)

    # Payouts
    with tabs[3]:
        st.markdown("<div class='card'>", unsafe_allow_html=True)
        st.subheader("📈 Profit/Loss")
        sess = st.selectbox("Session", [s['session_id'] for s in db.list_sessions()], key="pl_sess")
        df_bi = pd.DataFrame(db.get_buyins(sess))
        if df_bi.empty:
            st.info("No buy-ins.")
        else:
            sum_df = df_bi.groupby('player')['amount'].sum().reset_index().rename(columns={'amount':'buyin'})
            ends = {r['player']: st.number_input(f"{r['player']} End", min_value=0.0, format="%.2f", key=f"end_{sess}_{r['player']}") for _,r in sum_df.iterrows()}
            if st.button("Compute", key="compute_pl"):
                res = [{'player':p,'buyin':b,'end': ends[p],'pl': ends[p]-b} for p,b in zip(sum_df['player'], sum_df['buyin'])]
                st.session_state['pl'] = res
                st.dataframe(pd.DataFrame(res))
        st.markdown("</div>", unsafe_allow_html=True)

    # Settlement
    with tabs[4]:
        st.markdown("<div class='card'>", unsafe_allow_html=True)
        st.subheader("🔄 Settlement")
        if 'pl' in st.session_state:
            for r in st.session_state['pl']:
                msg = f"{r['player']} {'receives' if r['pl']>0 else 'owes'} $ {abs(r['pl']):.2f}"
                if r['pl']>0: st.success(msg)
                elif r['pl']<0: st.error(msg)
                else: st.info(msg)
        else:
            st.info("Run Profit/Loss first.")
        st.markdown("</div>", unsafe_allow_html=True)

if __name__ == "__main__":
    main()
