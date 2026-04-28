import streamlit as st
import firebase_admin
from firebase_admin import credentials, db
import json
import time
import random
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from io import BytesIO
import base64
import matplotlib.pyplot as plt
import pandas as pd
from datetime import datetime

st.set_page_config(page_title="🎲 2-Period Dynamic Game")

st.title("🎲 Multiplayer 2-Period Dynamic Game")

# Game description (short)
st.markdown("""
You will be matched with another player and play a 2‑period dynamic game.  
Each period you simultaneously choose an action. After both submit, the outcome and payoffs are shown.

|     | X       | Y       | Z       |
|-----|---------|---------|---------|
| A   | (4, 3)  | (0, 0)  | (1, 4)  |
| B   | (0, 0)  | (2, 1)  | (0, 0)  |
""")

# Firebase config
service_account = {
    "type": st.secrets["type"],
    "project_id": st.secrets["project_id"],
    "private_key_id": st.secrets["private_key_id"],
    "private_key": st.secrets["private_key"],
    "client_email": st.secrets["client_email"],
    "client_id": st.secrets["client_id"],
    "auth_uri": st.secrets["auth_uri"],
    "token_uri": st.secrets["token_uri"],
    "auth_provider_x509_cert_url": st.secrets["auth_provider_x509_cert_url"],
    "client_x509_cert_url": st.secrets["client_x509_cert_url"],
    "universe_domain": st.secrets["universe_domain"],
}
database_url = st.secrets["database_url"]

if not firebase_admin._apps:
    cred = credentials.Certificate(service_account)
    firebase_admin.initialize_app(cred, {"databaseURL": database_url})

# -------------------- Helper Functions --------------------
def create_comprehensive_pdf():
    import matplotlib.pyplot as plt
    import tempfile
    import os
    from reportlab.lib.pagesizes import letter
    from reportlab.lib.units import inch
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image, Table, TableStyle
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib import colors
    
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter, topMargin=0.5*inch, bottomMargin=0.5*inch)
    styles = getSampleStyleSheet()
    story = []
    
    # Title
    title_style = ParagraphStyle('CustomTitle', parent=styles['Title'], fontSize=24, textColor=colors.darkblue, spaceAfter=30)
    story.append(Paragraph("🎲 Dynamic Game Complete Results", title_style))
    story.append(Spacer(1, 20))
    
    all_games = db.reference("games").get() or {}
    expected_players = db.reference("expected_players").get() or 0
    
    story.append(Paragraph(f"<b>Game Summary</b>", styles['Heading2']))
    story.append(Paragraph(f"Expected Players: {expected_players}", styles['Normal']))
    story.append(Paragraph(f"Total Matches: {len(all_games)}", styles['Normal']))
    story.append(Spacer(1, 20))
    
    story.append(Paragraph("<b>Individual Match Results</b>", styles['Heading2']))
    table_data = [["Match ID", "Period 1", "Period 1 Payoffs", "Period 2", "Period 2 Payoffs"]]
    payoff_matrix = {
        "A": {"X": (4, 3), "Y": (0, 0), "Z": (1, 4)},
        "B": {"X": (0, 0), "Y": (2, 1), "Z": (0, 0)}
    }
    for match_id, game_data in all_games.items():
        if "period1" in game_data and "period2" in game_data:
            p1_action1 = game_data["period1"].get("Player 1", {}).get("action", "N/A")
            p2_action1 = game_data["period1"].get("Player 2", {}).get("action", "N/A")
            if p1_action1 != "N/A" and p2_action1 != "N/A":
                payoff1 = payoff_matrix[p1_action1][p2_action1]
            else:
                payoff1 = "N/A"
            p1_action2 = game_data["period2"].get("Player 1", {}).get("action", "N/A")
            p2_action2 = game_data["period2"].get("Player 2", {}).get("action", "N/A")
            if p1_action2 != "N/A" and p2_action2 != "N/A":
                payoff2 = payoff_matrix[p1_action2][p2_action2]
            else:
                payoff2 = "N/A"
            table_data.append([match_id, f"P1:{p1_action1}, P2:{p2_action1}", str(payoff1), f"P1:{p1_action2}, P2:{p2_action2}", str(payoff2)])
    
    table = Table(table_data, colWidths=[1.5*inch, 1.5*inch, 1*inch, 1.5*inch, 1*inch])
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 10),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
        ('FONTSIZE', (0, 1), (-1, -1), 8),
        ('GRID', (0, 0), (-1, -1), 1, colors.black)
    ]))
    story.append(table)
    story.append(Spacer(1, 30))
    
    # Charts
    story.append(Paragraph("<b>Statistical Analysis</b>", styles['Heading2']))
    p1_choices_r1, p2_choices_r1 = [], []
    p1_choices_r2, p2_choices_r2 = [], []
    for match in all_games.values():
        if "period1" in match:
            if match["period1"].get("Player 1", {}).get("action"): p1_choices_r1.append(match["period1"]["Player 1"]["action"])
            if match["period1"].get("Player 2", {}).get("action"): p2_choices_r1.append(match["period1"]["Player 2"]["action"])
        if "period2" in match:
            if match["period2"].get("Player 1", {}).get("action"): p1_choices_r2.append(match["period2"]["Player 1"]["action"])
            if match["period2"].get("Player 2", {}).get("action"): p2_choices_r2.append(match["period2"]["Player 2"]["action"])
    
    temp_dir = tempfile.mkdtemp()
    def create_chart(choices, labels, title, filename, colors_list):
        if not choices: return None
        counts = pd.Series(choices).value_counts(normalize=True).reindex(labels, fill_value=0) * 100
        fig, ax = plt.subplots(figsize=(10, 6))
        fig.patch.set_facecolor('#f0f0f0')
        ax.set_facecolor('#e0e0e0')
        bars = counts.plot(kind='bar', ax=ax, color=colors_list, linewidth=2, width=0.7)
        ax.set_title(title, fontsize=16, fontweight='bold', pad=20)
        ax.set_ylabel("Percentage (%)", fontsize=14)
        ax.set_xlabel("Choice", fontsize=14)
        ax.tick_params(rotation=0, labelsize=12)
        ax.set_ylim(0, 100)
        ax.grid(True, alpha=0.3)
        for bar in bars.patches:
            height = bar.get_height()
            ax.text(bar.get_x()+bar.get_width()/2., height+1, f'{height:.1f}%', ha='center', va='bottom', fontweight='bold')
        ax.text(0.02, 0.98, f"Sample size: {len(choices)}", transform=ax.transAxes, fontsize=10, verticalalignment='top', bbox=dict(boxstyle='round', facecolor='white', alpha=0.8))
        plt.tight_layout()
        filepath = os.path.join(temp_dir, filename)
        plt.savefig(filepath, dpi=300)
        plt.close()
        return filepath
    
    charts = []
    if p1_choices_r1: charts.append(create_chart(p1_choices_r1, ["A","B"], "Player 1 Choices (Period 1)", "p1_r1.png", ['#1f77b4','#ff7f0e']))
    if p2_choices_r1: charts.append(create_chart(p2_choices_r1, ["X","Y","Z"], "Player 2 Choices (Period 1)", "p2_r1.png", ['#1f77b4','#ff7f0e','#2ca02c']))
    if p1_choices_r2: charts.append(create_chart(p1_choices_r2, ["A","B"], "Player 1 Choices (Period 2)", "p1_r2.png", ['#1f77b4','#ff7f0e']))
    if p2_choices_r2: charts.append(create_chart(p2_choices_r2, ["X","Y","Z"], "Player 2 Choices (Period 2)", "p2_r2.png", ['#1f77b4','#ff7f0e','#2ca02c']))
    
    for chart_file in charts:
        if chart_file:
            story.append(Image(chart_file, width=6*inch, height=4*inch))
            story.append(Spacer(1, 20))
    
    # Cleanup
    for f in charts:
        if f and os.path.exists(f): os.remove(f)
    os.rmdir(temp_dir)
    
    # Payoff matrix reference
    story.append(Paragraph("<b>Payoff Matrix Reference</b>", styles['Heading2']))
    payoff_table = Table([["", "X", "Y", "Z"], ["A", "(4,3)", "(0,0)", "(1,4)"], ["B", "(0,0)", "(2,1)", "(0,0)"]],
                         colWidths=[1*inch,1*inch,1*inch,1*inch])
    payoff_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.grey),
        ('BACKGROUND', (0,0), (0,-1), colors.grey),
        ('TEXTCOLOR', (0,0), (-1,0), colors.whitesmoke),
        ('ALIGN', (0,0), (-1,-1), 'CENTER'),
        ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
        ('FONTNAME', (0,0), (0,-1), 'Helvetica-Bold'),
        ('FONTSIZE', (0,0), (-1,-1), 12),
        ('GRID', (0,0), (-1,-1), 1, colors.black)
    ]))
    story.append(payoff_table)
    story.append(Spacer(1,20))
    story.append(Paragraph("Format: (Player 1 Payoff, Player 2 Payoff)", styles['Normal']))
    story.append(Spacer(1,20))
    story.append(Paragraph("✅ Report generated automatically", styles['Normal']))
    doc.build(story)
    buffer.seek(0)
    return buffer

def export_game_csv():
    """Export all match results to CSV string"""
    all_games = db.reference("games").get() or {}
    rows = []
    payoff_matrix = {
        "A": {"X": (4,3), "Y": (0,0), "Z": (1,4)},
        "B": {"X": (0,0), "Y": (2,1), "Z": (0,0)}
    }
    for match_id, game_data in all_games.items():
        if "period1" in game_data and "period2" in game_data:
            p1_1 = game_data["period1"].get("Player 1", {}).get("action", "N/A")
            p2_1 = game_data["period1"].get("Player 2", {}).get("action", "N/A")
            payoff1 = payoff_matrix.get(p1_1, {}).get(p2_1, ("N/A","N/A")) if p1_1!="N/A" and p2_1!="N/A" else ("N/A","N/A")
            p1_2 = game_data["period2"].get("Player 1", {}).get("action", "N/A")
            p2_2 = game_data["period2"].get("Player 2", {}).get("action", "N/A")
            payoff2 = payoff_matrix.get(p1_2, {}).get(p2_2, ("N/A","N/A")) if p1_2!="N/A" and p2_2!="N/A" else ("N/A","N/A")
            rows.append({
                "Match ID": match_id,
                "Player 1": game_data["period1"].get("Player 1", {}).get("player", "Unknown"),
                "Player 2": game_data["period1"].get("Player 2", {}).get("player", "Unknown"),
                "Period1_P1_Action": p1_1,
                "Period1_P2_Action": p2_1,
                "Period1_P1_Payoff": payoff1[0],
                "Period1_P2_Payoff": payoff1[1],
                "Period2_P1_Action": p1_2,
                "Period2_P2_Action": p2_2,
                "Period2_P1_Payoff": payoff2[0],
                "Period2_P2_Payoff": payoff2[1]
            })
    df = pd.DataFrame(rows)
    return df.to_csv(index=False)

# -------------------- Admin Panel --------------------
admin_password = st.text_input("Admin Password (for database management):", type="password")
if admin_password == "admin123":
    st.header("🔒 Admin Dashboard")
    all_players = db.reference("players").get() or {}
    all_matches = db.reference("matches").get() or {}
    all_games = db.reference("games").get() or {}
    expected_players = db.reference("expected_players").get() or 0
    
    matched_players = set()
    for match in all_matches.values():
        matched_players.update(match.get("players", []))
    completed_period2 = set()
    for game in all_games.values():
        if "period2" in game:
            for p in game["period2"].keys():
                completed_period2.add(p)
    
    col1, col2, col3, col4 = st.columns(4)
    with col1: st.metric("Expected Players", expected_players)
    with col2: st.metric("Registered Players", len(all_players))
    with col3: st.metric("Matched Players", len(matched_players))
    with col4: st.metric("Completed Period 2", len(completed_period2))
    
    if expected_players > 0:
        progress = min(len(completed_period2) / expected_players, 1.0)
        st.progress(progress)
        st.write(f"Progress: {len(completed_period2)}/{expected_players} players completed ({progress*100:.1f}%)")
    
    st.subheader("👥 Player Activity Monitor")
    if all_players:
        status_data = []
        for p in all_players.keys():
            status = "🔴 Registered"
            activity = "Waiting for match"
            if p in matched_players:
                status = "🟡 Matched"
                activity = "Matched with partner"
            if p in completed_period2:
                status = "🟢 Completed"
                activity = "Game finished"
            status_data.append({"Player Name": p, "Status": status, "Activity": activity})
        st.dataframe(pd.DataFrame(status_data), use_container_width=True)
    
    # Live Choice Analytics (same as before, but keep concise)
    st.subheader("📈 Live Choice Analytics")
    if all_games:
        p1_r1, p2_r1, p1_r2, p2_r2 = [], [], [], []
        for game in all_games.values():
            if "period1" in game:
                if game["period1"].get("Player 1", {}).get("action"): p1_r1.append(game["period1"]["Player 1"]["action"])
                if game["period1"].get("Player 2", {}).get("action"): p2_r1.append(game["period1"]["Player 2"]["action"])
            if "period2" in game:
                if game["period2"].get("Player 1", {}).get("action"): p1_r2.append(game["period2"]["Player 1"]["action"])
                if game["period2"].get("Player 2", {}).get("action"): p2_r2.append(game["period2"]["Player 2"]["action"])
        
        def quick_chart(choices, labels, title):
            if choices:
                counts = pd.Series(choices).value_counts(normalize=True).reindex(labels, fill_value=0)*100
                fig, ax = plt.subplots()
                counts.plot(kind='bar', ax=ax)
                ax.set_ylim(0,100)
                ax.set_title(title)
                st.pyplot(fig)
            else:
                st.info(f"No data for {title}")
        
        col1, col2 = st.columns(2)
        with col1: quick_chart(p1_r1, ["A","B"], "P1 Period 1")
        with col2: quick_chart(p2_r1, ["X","Y","Z"], "P2 Period 1")
        col3, col4 = st.columns(2)
        with col3: quick_chart(p1_r2, ["A","B"], "P1 Period 2")
        with col4: quick_chart(p2_r2, ["X","Y","Z"], "P2 Period 2")
    
    st.subheader("⚙️ Game Management")
    current_expected = db.reference("expected_players").get() or 0
    new_expected = st.number_input("Set expected number of players (even):", min_value=0, max_value=100, value=current_expected, step=2)
    if st.button("Update Expected Players"):
        if new_expected % 2 == 0:
            db.reference("expected_players").set(new_expected)
            st.success(f"Expected players set to {new_expected}")
            st.rerun()
        else:
            st.error("Must be even")
    
    # CSV export button
    if st.button("📊 Export All Results to CSV"):
        if all_games:
            csv_data = export_game_csv()
            st.download_button("Download CSV", data=csv_data, file_name="dynamic_game_results.csv", mime="text/csv")
        else:
            st.warning("No game data yet.")
    
    # PDF report
    if st.button("📄 Download Complete Game Report (PDF)"):
        with st.spinner("Generating PDF..."):
            try:
                pdf_buffer = create_comprehensive_pdf()
                b64 = base64.b64encode(pdf_buffer.read()).decode()
                href = f'<a href="data:application/pdf;base64,{b64}" download="complete_game_results.pdf">Click here to download PDF</a>'
                st.markdown(href, unsafe_allow_html=True)
                st.success("PDF generated!")
            except Exception as e:
                st.error(f"Error: {e}")
    
    # Restart game button – keeps matches but clears all period choices
    if st.button("🔄 Restart Game (keep same pairs, reset all progress)"):
        # Delete all game data (period1 and period2 for all matches)
        db.reference("games").delete()
        st.success("✅ Game data cleared. Players can now replay from Period 1.")
        st.rerun()
    
    # Full reset
    if st.button("🗑 Delete ALL Game Data (including players and matches)"):
        db.reference("games").delete()
        db.reference("matches").delete()
        db.reference("players").delete()
        db.reference("expected_players").set(0)
        st.success("All data cleared.")
        st.rerun()
    
    # Auto-refresh unless all completed
    all_completed = expected_players > 0 and len(completed_period2) >= expected_players
    if all_completed:
        st.success("🎉 All participants completed! Admin monitoring complete.")
        if st.button("Manual Refresh"):
            st.rerun()
    else:
        time.sleep(3)
        st.rerun()
    
    st.stop()

# -------------------- Player Game --------------------
if (db.reference("expected_players").get() or 0) <= 0:
    st.info("⚠️ Game not configured yet. Admin needs to set expected number of players.")
    st.stop()

name = st.text_input("Enter your name to join the game:")
if name:
    st.success(f"👋 Welcome, {name}!")
    player_ref = db.reference(f"players/{name}")
    if not player_ref.get():
        player_ref.set({"joined": True, "timestamp": time.time()})
    
    # Matching logic (unchanged, but ensure no duplicate matches)
    matches_ref = db.reference("matches")
    all_matches = matches_ref.get() or {}
    player_match = None
    for mid, mdata in all_matches.items():
        if name in mdata.get("players", []):
            player_match = mid
            role = "Player 1" if mdata["players"][0] == name else "Player 2"
            break
    
    if not player_match:
        # Check if all expected players already completed (no new matches)
        expected_players = db.reference("expected_players").get() or 0
        all_games = db.reference("games").get() or {}
        completed_count = 0
        for g in all_games.values():
            if "period1" in g and "period2" in g and "Player 1" in g["period1"] and "Player 2" in g["period1"] and "Player 1" in g["period2"] and "Player 2" in g["period2"]:
                completed_count += 2
        if expected_players > 0 and completed_count >= expected_players:
            st.info("🎯 All games have been completed! No more matches are available. Check the summary below.")
            # Still show results if any
        else:
            players_data = db.reference("players").get() or {}
            unmatched = [p for p in players_data.keys() if p != name and not any(p in m.get("players", []) for m in all_matches.values())]
            if unmatched:
                partner = unmatched[0]
                pair = sorted([name, partner])
                match_id = f"{pair[0]}_vs_{pair[1]}"
                if not matches_ref.child(match_id).get():
                    matches_ref.child(match_id).set({"players": pair})
                role = "Player 1" if pair[0] == name else "Player 2"
                player_match = match_id
                st.success(f"🎮 You are {role} in match {match_id}")
            else:
                st.info("⏳ Waiting for another player to join...")
                # Wait for match (simple polling)
                for _ in range(15):
                    time.sleep(2)
                    all_matches = matches_ref.get() or {}
                    for mid, mdata in all_matches.items():
                        if name in mdata.get("players", []):
                            player_match = mid
                            role = "Player 1" if mdata["players"][0] == name else "Player 2"
                            st.rerun()
                    break
    
    if player_match:
        # Gameplay period 1
        game_ref_period1 = db.reference(f"games/{player_match}/period1")
        period1_data = game_ref_period1.get()
        payoff_matrix = {
            "A": {"X": (4, 3), "Y": (0, 0), "Z": (1, 4)},
            "B": {"X": (0, 0), "Y": (2, 1), "Z": (0, 0)}
        }
        
        if period1_data and "Player 1" in period1_data and "Player 2" in period1_data:
            # Period 1 already complete
            p1a = period1_data["Player 1"]["action"]
            p2a = period1_data["Player 2"]["action"]
            payoff1 = payoff_matrix[p1a][p2a]
            st.success(f"Period 1 result: P1:{p1a}, P2:{p2a} → Payoffs {payoff1}")
            st.subheader("🔁 Period 2")
            game_ref_period2 = db.reference(f"games/{player_match}/period2")
            period2_data = game_ref_period2.get()
            if period2_data and "Player 1" in period2_data and "Player 2" in period2_data:
                p1a2 = period2_data["Player 1"]["action"]
                p2a2 = period2_data["Player 2"]["action"]
                payoff2 = payoff_matrix[p1a2][p2a2]
                st.success(f"Period 2 result: P1:{p1a2}, P2:{p2a2} → Payoffs {payoff2}")
                st.balloons()
                st.success("✅ Game complete! Thank you.")
                st.session_state["game_done"] = True
            else:
                # Submit period 2
                existing = game_ref_period2.child(role).get()
                if existing:
                    st.info("Waiting for the other player...")
                    time.sleep(2)
                    st.rerun()
                else:
                    if role == "Player 1":
                        choice = st.radio("Your Period 2 action:", ["A", "B"])
                    else:
                        choice = st.radio("Your Period 2 action:", ["X", "Y", "Z"])
                    if st.button("Submit Period 2"):
                        game_ref_period2.child(role).set({"action": choice, "timestamp": time.time(), "player": name})
                        st.success("Submitted! Waiting for partner.")
                        st.rerun()
        else:
            # Submit period 1
            existing = game_ref_period1.child(role).get()
            if existing:
                st.info("Waiting for the other player to finish Period 1...")
                time.sleep(2)
                st.rerun()
            else:
                if role == "Player 1":
                    choice = st.radio("Your Period 1 action:", ["A", "B"])
                else:
                    choice = st.radio("Your Period 1 action:", ["X", "Y", "Z"])
                if st.button("Submit Period 1"):
                    game_ref_period1.child(role).set({"action": choice, "timestamp": time.time(), "player": name})
                    st.success("Submitted! Waiting for partner.")
                    st.rerun()
    
    # After game complete, show summary if any matches exist
    if st.session_state.get("game_done", False):
        st.header("📊 Class Results")
        all_games = db.reference("games").get() or {}
        p1_r1, p2_r1, p1_r2, p2_r2 = [], [], [], []
        for g in all_games.values():
            if "period1" in g:
                if g["period1"].get("Player 1", {}).get("action"): p1_r1.append(g["period1"]["Player 1"]["action"])
                if g["period1"].get("Player 2", {}).get("action"): p2_r1.append(g["period1"]["Player 2"]["action"])
            if "period2" in g:
                if g["period2"].get("Player 1", {}).get("action"): p1_r2.append(g["period2"]["Player 1"]["action"])
                if g["period2"].get("Player 2", {}).get("action"): p2_r2.append(g["period2"]["Player 2"]["action"])
        
        def plot_pct(choices, labels, title):
            if choices:
                counts = pd.Series(choices).value_counts(normalize=True).reindex(labels, fill_value=0)*100
                fig, ax = plt.subplots()
                counts.plot(kind='bar', ax=ax, color=['#1f77b4','#ff7f0e','#2ca02c'][:len(labels)])
                ax.set_ylim(0,100)
                ax.set_title(title)
                st.pyplot(fig)
            else:
                st.info(f"No data for {title}")
        
        st.subheader("Period 1 Choices")
        col1, col2 = st.columns(2)
        with col1: plot_pct(p1_r1, ["A","B"], "Player 1")
        with col2: plot_pct(p2_r1, ["X","Y","Z"], "Player 2")
        st.subheader("Period 2 Choices")
        col3, col4 = st.columns(2)
        with col3: plot_pct(p1_r2, ["A","B"], "Player 1")
        with col4: plot_pct(p2_r2, ["X","Y","Z"], "Player 2")
        
        if st.button("🔄 Refresh Results"):
            st.rerun()
