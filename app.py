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

# Responsive sleek/gambling-themed CSS
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
        max-width: 100%;
    }
    /* Button styling */
    .stButton > button {
        background-color: #e63946;
        color: #f0f0f0;
        font-weight: 500;
        border: none;
        border-radius: 4px;
        padding: 0.6rem 1.2rem;
        width: auto;
        transition: background 0.3s;
    }
    .stButton > button:hover {
        background-color: #d62828;
    }
    /* Dataframe styling */
    .stDataFrame table {
        background-color: rgba(255, 255, 255, 0.1);
        color: #f0f0f0;
    }
    /* Responsive adjustments */
    @media only screen and (max-width: 768px) {
        .poker-header { font-size: 1.8rem; letter-spacing: 1px; }
        .card { padding: 1rem; margin: 1rem 0; }
        .stButton > button { width: 100% !important; margin-bottom: 0.5rem; }
        .stDataFrame table { font-size: 0.8rem; }
    }
    </style>
    """,
    unsafe_allow_html=True
)

# Initialize buy-in queue
if 'buyin_queue' not in st.session_state:
    st.session_state['buyin_queue'] = []

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
            st.dataframe(pd.DataFrame(sessions), use_container_width=True)
        else:
            st.info("No sessions yet. Create one below.")
        name = st.text_input("New Session Name", key="new_session_name")
        if st.button("Create Session", key="btn_create_session") and name:
            db.create_session(name)
            st.success(f"Session '{name}' created.")
        if st.button("Clear All Sessions", key="btn_clear_sessions"):
            db.conn.execute("DELETE FROM payouts")
            db.conn.execute("DELETE FROM buyins")
            db.conn.execute("DELETE FROM sessions")
            db.conn.commit()
            st.success("All sessions, buy-ins, and payouts cleared.")
        st.markdown("</div>", unsafe_allow_html=True)

    # Add Buy-in with batching
    with tabs[1]:
        st.markdown("<div class='card'>", unsafe_allow_html=True)
        st.subheader("💰 Add Buy-in (Queue & Batch)")
        session_ids = [s['session_id'] for s in db.list_sessions()]
        if not session_ids:
            st.warning("Please create a session first.")
        else:
            sess = st.selectbox("Select Session", session_ids, key="add_buyin_session")
            mode = st.radio("Mode", ["Auto-parse Zelle Message", "Manual Entry"], key="add_buyin_mode")
            if mode == "Auto-parse Zelle Message":
                msg = st.text_area("Paste Zelle message", key="queue_auto_msg")
                if st.button("Queue Parsed Buy-in", key="queue_parse_btn"):
                    rec = ZelleMessageParser.parse(msg)
                    if rec:
                        rec['session_id'] = sess
                        st.session_state['buyin_queue'].append(rec)
                        st.success(f"Queued: {rec['sender']} - $ {rec['amount']}")
                    else:
                        st.error("Invalid message.")
            else:
                player = st.text_input("Player Name", key="queue_player")
                amt = st.number_input("Amount", min_value=0.0, format="%.2f", key="queue_amt")
                notes = st.text_input("Notes (optional)", key="queue_notes")
                if st.button("Queue Manual Buy-in", key="queue_manual_btn"):
                    record = {
                        'session_id': sess,
                        'sender': player,
                        'amount': amt,
                        'timestamp': datetime.now().isoformat(),
                        'notes': notes
                    }
                    st.session_state['buyin_queue'].append(record)
                    st.success(f"Queued: {player} - $ {amt}")
            # Show pending queue
            if st.session_state['buyin_queue']:
                st.subheader("Pending Buy-ins")
                st.dataframe(pd.DataFrame(st.session_state['buyin_queue']), use_container_width=True)
                if st.button("Submit All Buy-ins", key="submit_queue_btn"):
                    for rec in st.session_state['buyin_queue']:
                        db.add_buyin(rec)
                    st.session_state['buyin_queue'].clear()
                    st.success("All queued buy-ins submitted.")
        st.markdown("</div>", unsafe_allow_html=True)

    # Sessions Overview
    with tabs[2]:
        st.markdown("<div class='card'>", unsafe_allow_html=True)
        st.subheader("📋 Sessions")
        df_sess = pd.DataFrame(db.list_sessions())
        st.dataframe(df_sess, use_container_width=True)
        if not df_sess.empty:
            vs = st.selectbox("Select Session", df_sess['session_id'], key="vs_sess")
            df_b = pd.DataFrame(db.get_buyins(vs))
            st.dataframe(df_b, use_container_width=True)
        st.markdown("</div>", unsafe_allow_html=True)

    # Payouts & Profit/Loss
    with tabs[3]:
        st.markdown("<div class='card'>", unsafe_allow_html=True)
        st.subheader("📈 Profit/Loss & Details")
        sess_ids = [s['session_id'] for s in db.list_sessions()]
        if sess_ids:
            session = st.selectbox("Select Session", sess_ids, key="pl_sess")
            buyins = db.get_buyins(session)
            df_buyins = pd.DataFrame(buyins)
            if df_buyins.empty:
                st.info("No buy-ins recorded for this session.")
            else:
                summary = df_buyins.groupby('player')['amount'].sum().reset_index().rename(columns={'amount':'total_buyin'})
                st.subheader("Enter Ending Stacks")
                ending = {}
                for _, row in summary.iterrows():
                    ending[row['player']] = st.number_input(
                        f"{row['player']}'s Ending Stack", min_value=0.0, format="%.2f", key=f"end_{session}_{row['player']}"
                    )
                if st.button("Compute Profit/Loss", key="compute_pl_btn"):
                    pl_results = []
                    for _, row in summary.iterrows():
                        pl = ending[row['player']] - row['total_buyin']
                        pl_results.append({
                            'player': row['player'],
                            'total_buyin': row['total_buyin'],
                            'ending_stack': ending[row['player']],
                            'profit_loss': pl
                        })
                    # Persist results for Settlement tab
                    st.session_state['pl'] = pl_results
                    df_pl = pd.DataFrame(pl_results)
                    st.subheader("Profit/Loss Summary")
                    st.dataframe(df_pl, use_container_width=True)
                    st.download_button(
                        "Download Profit/Loss Report",
                        data=df_pl.to_csv(index=False).encode('utf-8'),
                        file_name=f"profit_loss_{session}.csv",
                        mime='text/csv',
                        key="download_pl_csv"
                    )
                    st.subheader("Buy-ins Details (including Zelle notes)")
                    st.dataframe(df_buyins[['player','amount','timestamp','notes']], use_container_width=True)
        st.markdown("</div>", unsafe_allow_html=True)

    # Settlement
    with tabs[4]:
        st.markdown("<div class='card'>", unsafe_allow_html=True)
        st.subheader("🔄 Settlement")
        if 'pl' in st.session_state:
            for r in st.session_state['pl']:
                msg = f"{r['player']} {'receives' if r['profit_loss']>0 else 'owes'} $ {abs(r['profit_loss']):.2f}"
                if r['profit_loss']>0:
                    st.success(msg)
                elif r['profit_loss']<0:
                    st.error(msg)
                else:
                    st.info(msg)
        else:
            st.info("Run Profit/Loss first.")
        st.markdown("</div>", unsafe_allow_html=True)

if __name__ == "__main__":
    main()
