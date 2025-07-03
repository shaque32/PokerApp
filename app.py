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

# Initialize storage for P/L and ending stacks
if 'pl_results' not in st.session_state:
    st.session_state['pl_results'] = None
if 'ending_stacks' not in st.session_state:
    st.session_state['ending_stacks'] = {}

# Main app
def main():
    st.markdown("<div class='poker-header'>♠️ Poker Buy-ins Manager ♥️</div>", unsafe_allow_html=True)
    db = DatabaseManager('poker.db')

        # Global session selector
    sessions = db.list_sessions()
    session_ids = [s['session_id'] for s in sessions]
    if session_ids:
        # Persist current session selection via session_state
        if 'current_session' not in st.session_state or st.session_state['current_session'] not in session_ids:
            st.session_state['current_session'] = session_ids[0]
        selected_session = st.selectbox(
            "Select Session",
            session_ids,
            index=session_ids.index(st.session_state['current_session']),
            key="current_session",
        )
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
            st.session_state['current_session'] = new_name
            
        if st.button("Clear All Sessions", key="btn_clear_sessions"):
            db.conn.execute("DELETE FROM payouts")
            db.conn.execute("DELETE FROM buyins")
            db.conn.execute("DELETE FROM sessions")
            db.conn.commit()
            st.session_state['pl_results'] = None
            st.session_state['ending_stacks'] = {}
            st.session_state['current_session'] = None
            st.experimental_rerun()
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
                if st.session_state['pl_results'] is None:
                    st.subheader("Enter Ending Stacks")
                    for _, row in summary.iterrows():
                        # preload existing stack if available
                        default = st.session_state['ending_stacks'].get(row['player'], 0.0)
                        val = st.number_input(
                            f"{row['player']}'s Ending Stack", min_value=0.0, format="%.2f",
                            value=default,
                            key=f"end_{row['player']}"
                        )
                        st.session_state['ending_stacks'][row['player']] = val
                    if st.button("Compute Profit/Loss", key="compute_pl_btn"):
                        pl = []
                        for _, row in summary.iterrows():
                            amt = st.session_state['ending_stacks'][row['player']]
                            diff = amt - row['total_buyin']
                            pl.append({'player':row['player'],'total_buyin':row['total_buyin'],'ending_stack':amt,'profit_loss':diff})
                        st.session_state['pl_results'] = pl
                        st.experimental_rerun()
                else:
                    # show stored results directly
                    df_pl = pd.DataFrame(st.session_state['pl_results'])
                    st.subheader("Profit/Loss Summary")
                    st.dataframe(df_pl, use_container_width=True)
                    st.download_button(
                        "Download P/L", data=df_pl.to_csv(index=False).encode('utf-8'),
                        file_name=f"pl_{selected_session}.csv", mime='text/csv', key="dl_pl"
                    )
                    st.subheader("Buy-ins Details")
                    st.dataframe(df_buyins[['player','amount','timestamp','notes']], use_container_width=True)
            st.markdown("</div>", unsafe_allow_html=True)

    # Tab 4: Settlement
    with tabs[4]:
        st.markdown("<div class='card'>", unsafe_allow_html=True)
        st.subheader("Settlement")
        if st.session_state['pl_results'] is not None:
            df_settle = pd.DataFrame(st.session_state['pl_results'])
            total_receive = df_settle[df_settle['profit_loss']>0]['profit_loss'].sum()
            total_send = -df_settle[df_settle['profit_loss']<0]['profit_loss'].sum()
            cols = st.columns(2)
            cols[0].metric("Total to Receive", f"$ {total_receive:.2f}")
            cols[1].metric("Total to Send", f"$ {total_send:.2f}")
            st.markdown("---")
            for r in st.session_state['pl_results']:
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
