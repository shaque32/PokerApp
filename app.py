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

# Main app
def main():
    st.markdown("<div class='poker-header'>♠️ Poker Buy-ins Manager ♥️</div>", unsafe_allow_html=True)
    db = DatabaseManager('poker.db')

    # Global session selector
    sessions = db.list_sessions()
    session_ids = [s['session_id'] for s in sessions]
    if session_ids:
        selected_session = st.selectbox("Select Session", session_ids, key="current_session")
    else:
        st.warning("No sessions available. Please create one in Manage Sessions.")
        selected_session = None

    tabs = st.tabs(["Manage Sessions", "Add Buy-in", "Sessions", "Payouts", "Settlement"])

    # Tab 0: Manage Sessions
    with tabs[0]:
        st.markdown("<div class='card'>", unsafe_allow_html=True)
        st.subheader("Manage Sessions")
        if sessions:
            st.dataframe(pd.DataFrame(sessions), use_container_width=True)
        else:
            st.info("No sessions yet.")
        new_name = st.text_input("New Session Name", key="new_session_name")
        if st.button("Create Session", key="btn_create_session") and new_name:
            db.create_session(new_name)
            st.success(f"Session '{new_name}' created.")
        if st.button("Clear All Sessions", key="btn_clear_sessions"):
            db.conn.execute("DELETE FROM payouts")
            db.conn.execute("DELETE FROM buyins")
            db.conn.execute("DELETE FROM sessions")
            db.conn.commit()
            st.success("All sessions, buy-ins, and payouts cleared.")
        st.markdown("</div>", unsafe_allow_html=True)

    # Tab 1: Add Buy-in
    if selected_session:
        with tabs[1]:
            st.markdown("<div class='card'>", unsafe_allow_html=True)
            st.subheader(f"Add Buy-in to Session: {selected_session}")
            mode = st.radio("Mode", ["Auto-parse Zelle Message", "Manual Entry"], key="add_buyin_mode")
            if mode == "Auto-parse Zelle Message":
                msg = st.text_area("Paste Zelle message", key="auto_msg")
                if st.button("Parse & Add Buy-in", key="auto_add_btn"):
                    record = ZelleMessageParser.parse(msg)
                    if record:
                        record['session_id'] = selected_session
                        db.add_buyin(record)
                        st.success(f"Added: {record['sender']} - $ {record['amount']}")
                    else:
                        st.error("Invalid message.")
            else:
                player = st.text_input("Player Name", key="man_player")
                amt = st.number_input("Amount", min_value=0.0, format="%.2f", key="man_amt")
                notes = st.text_input("Notes (optional)", key="man_notes")
                if st.button("Add Manual Buy-in", key="man_add_btn"):
                    db.add_manual_buyin(selected_session, player, amt, datetime.now(), notes)
                    st.success(f"Added: {player} - $ {amt}")
            st.markdown("</div>", unsafe_allow_html=True)

    # Tab 2: Sessions Overview
    with tabs[2]:
        st.markdown("<div class='card'>", unsafe_allow_html=True)
        st.subheader("Sessions Overview")
        df_all = pd.DataFrame(sessions)
        st.dataframe(df_all, use_container_width=True)
        st.markdown("</div>", unsafe_allow_html=True)

    # Tab 3: Payouts
    if selected_session:
        with tabs[3]:
            st.markdown("<div class='card'>", unsafe_allow_html=True)
            st.subheader(f"Profit/Loss for Session: {selected_session}")
            buyins = db.get_buyins(selected_session)
            df_buyins = pd.DataFrame(buyins)
            if df_buyins.empty:
                st.info("No buy-ins recorded.")
            else:
                summary = df_buyins.groupby('player')['amount'].sum().reset_index().rename(columns={'amount':'total_buyin'})
                st.subheader("Enter Ending Stacks")
                ending = {}
                for _, row in summary.iterrows():
                    ending[row['player']] = st.number_input(
                        f"{row['player']}'s Ending Stack", min_value=0.0, format="%.2f", key=f"end_{row['player']}"
                    )
                if st.button("Compute Profit/Loss", key="compute_pl_btn"):
                    pl_results = []
                    for _, row in summary.iterrows():
                        pl = ending[row['player']] - row['total_buyin']
                        pl_results.append({'player':row['player'],'total_buyin':row['total_buyin'],'ending_stack':ending[row['player']],'profit_loss':pl})
                    st.session_state['pl'] = pl_results
                    df_pl = pd.DataFrame(pl_results)
                    st.subheader("Profit/Loss Summary")
                    st.dataframe(df_pl, use_container_width=True)
                    st.download_button("Download P/L", data=df_pl.to_csv(index=False).encode('utf-8'), file_name=f"pl_{selected_session}.csv", mime='text/csv', key="dl_pl")
                    st.subheader("Buy-ins Details")
                    st.dataframe(df_buyins[['player','amount','timestamp','notes']], use_container_width=True)
            st.markdown("</div>", unsafe_allow_html=True)

    # Tab 4: Settlement
    with tabs[4]:
        st.markdown("<div class='card'>", unsafe_allow_html=True)
        st.subheader("Settlement")
        if 'pl' in st.session_state:
            df_settle = pd.DataFrame(st.session_state['pl'])
            total_receive = df_settle[df_settle['profit_loss']>0]['profit_loss'].sum()
            total_send = -df_settle[df_settle['profit_loss']<0]['profit_loss'].sum()
            cols = st.columns(2)
            cols[0].metric("Total to Receive", f"$ {total_receive:.2f}")
            cols[1].metric("Total to Send", f"$ {total_send:.2f}")
            st.markdown("---")
            for r in st.session_state['pl']:
                status = f"{r['player']} {'receives' if r['profit_loss']>0 else 'owes'} $ {abs(r['profit_loss']):.2f}"
                if r['profit_loss']>0:
                    st.success(status)
                elif r['profit_loss']<0:
                    st.error(status)
                else:
                    st.info(status)
        else:
            st.info("Run Profit/Loss first.")
        st.markdown("</div>", unsafe_allow_html=True)

if __name__ == "__main__":
    main()
