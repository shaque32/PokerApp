import streamlit as st
import pandas as pd
from datetime import datetime
from parser import ZelleMessageParser
from db import DatabaseManager

def main():
    st.title("Poker Buy-ins Manager")
    db = DatabaseManager('poker.db')

    tabs = st.tabs(["Add Buy-in", "Sessions", "Payouts"])

    with tabs[0]:
        st.header("Add Buy-in")
        mode = st.radio("Mode", ["Auto-parse Zelle Message", "Manual Entry"])
        if mode == "Auto-parse Zelle Message":
            msg = st.text_area("Paste Zelle message text here")
            if st.button("Parse & Add"):
                record = ZelleMessageParser.parse(msg)
                if record:
                    db.add_buyin(record)
                    st.success(f"Recorded buy-in: {record['sender']} - $ {record['amount']}")
                else:
                    st.error("No valid poker buy-in found.")
        else:
            player = st.text_input("Player Name")
            amount = st.number_input("Amount", min_value=0.0, format="%.2f")
            dt = st.datetime_input("Date & Time", datetime.now())
            notes = st.text_input("Notes (optional)")
            if st.button("Add Manual Buy-in"):
                db.add_manual_buyin(player, amount, dt, notes)
                st.success(f"Manually added buy-in: {player} - $ {amount}")

    with tabs[1]:
        st.header("Sessions")
        sessions = db.list_sessions()
        df_sessions = pd.DataFrame(sessions)
        st.dataframe(df_sessions)
        if not df_sessions.empty:
            session = st.selectbox("Select Session", df_sessions['session_id'])
            buyins = db.get_buyins(session)
            df_buyins = pd.DataFrame(buyins)
            st.subheader(f"Buy-ins for {session}")
            st.dataframe(df_buyins)

            # Edit / Delete
            st.markdown("**Edit or Delete a Record**")
            col1, col2 = st.columns(2)
            with col1:
                edit_id = st.number_input("Record ID to edit/delete", min_value=1, step=1)
            with col2:
                action = st.selectbox("Action", ["Delete", "Edit"])

            if action == "Delete":
                if st.button("Delete Record"):
                    db.delete_buyin(edit_id)
                    st.success("Record deleted.")
            else:
                new_player = st.text_input("New Player Name")
                new_amount = st.number_input("New Amount", min_value=0.0, format="%.2f")
                if st.button("Update Record"):
                    db.update_buyin(edit_id, new_player or None, new_amount)
                    st.success("Record updated.")

            # Export CSV
            csv = df_buyins.to_csv(index=False).encode('utf-8')
            st.download_button(label="Download Buy-ins CSV", data=csv, file_name=f"buyins_{session}.csv", mime='text/csv')

    with tabs[2]:
        st.header("Payouts")
        sessions = db.list_sessions()
        if sessions:
            session = st.selectbox("Select Session for Payouts", [s['session_id'] for s in sessions])
            buyins = db.get_buyins(session)
            total_collected = sum(item['amount'] for item in buyins)
            payouts = db.get_payouts(session)
            total_payout = sum(p['amount'] for p in payouts)

            st.write(f"Total Collected: $ {total_collected:.2f}")
            st.write(f"Total Payout: $ {total_payout:.2f}")
            st.write(f"Remaining Balance: $ {(total_collected - total_payout):.2f}")

            st.subheader("Add Payout")
            winner = st.text_input("Winner Name")
            amount = st.number_input("Payout Amount", min_value=0.0, format="%.2f")
            if st.button("Record Payout"):
                db.add_payout(session, winner, amount)
                st.success(f"Payout of $ {amount} to {winner} recorded.")

            df_payouts = pd.DataFrame(payouts)
            st.subheader("Payout History")
            st.dataframe(df_payouts)

            # Export payout summary
            summary = {
                'type': ['collected', 'payout', 'remaining'],
                'amount': [total_collected, total_payout, total_collected - total_payout]
            }
            df_summary = pd.DataFrame(summary)
            summary_csv = df_summary.to_csv(index=False).encode('utf-8')
            st.download_button(label="Download Payout Summary CSV", data=summary_csv, file_name=f"payout_summary_{session}.csv", mime='text/csv')

if __name__ == "__main__":
    main()
