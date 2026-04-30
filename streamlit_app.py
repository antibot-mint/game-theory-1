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
    
    title_style = ParagraphStyle('CustomTitle', parent=styles['Title'], fontSize=24, textColor=colors.darkblue, spaceAfter=30)
    story.append(Paragraph("🎲 Dynamic Game Complete Results", title_style))
    story.append(Spacer(1, 20))
    
    all_games = db.reference("games").get() or {}
    expected_players = db.reference("expected_players").get() or 0
    all_matches = db.reference("matches").get() or {}
    
    story.append(Paragraph(f"<b>Game Summary</b>", styles['Heading2']))
    story.append(Paragraph(f"Expected Players: {expected_players}", styles['Normal']))
    story.append(Paragraph(f"Total Matches: {len(all_matches)}", styles['Normal']))
    story.append(Spacer(1, 20))
    
    story.append(Paragraph("<b>Individual Match Results</b>", styles['Heading2']))
    table_data = [["Match ID", "Player 1", "Player 2", "Period 1", "Period 1 Payoffs", "Period 2", "Period 2 Payoffs"]]
    payoff_matrix = {
        "A": {"X": (4, 3), "Y": (0, 0), "Z": (1, 4)},
        "B": {"X": (0, 0), "Y": (2, 1), "Z": (0, 0)}
    }
    for match_id, match_data in all_matches.items():
        players = match_data.get("players", [])
        if len(players) < 2: continue
        p1_name, p2_name = players[0], players[1]
        game_data = all_games.get(match_id, {})
        period1 = game_data.get("period1", {})
        period2 = game_data.get("period2", {})
        p1_a1 = period1.get("Player 1", {}).get("action", "N/A")
        p2_a1 = period1.get("Player 2", {}).get("action", "N/A")
        p1_a2 = period2.get("Player 1", {}).get("action", "N/A")
        p2_a2 = period2.get("Player 2", {}).get("action", "N/A")
        payoff1 = payoff_matrix.get(p1_a1, {}).get(p2_a1, ("N/A","N/A")) if p1_a1!="N/A" and p2_a1!="N/A" else ("N/A","N/A")
        payoff2 = payoff_matrix.get(p1_a2, {}).get(p2_a2, ("N/A","N/A")) if p1_a2!="N/A" and p2_a2!="N/A" else ("N/A","N/A")
        table_data.append([
            match_id, p1_name, p2_name,
            f"P1:{p1_a1}, P2:{p2_a1}", str(payoff1),
            f"P1:{p1_a2}, P2:{p2_a2}", str(payoff2)
        ])
    
    col_widths = [1.2*inch, 1*inch, 1*inch, 1.2*inch, 0.8*inch, 1.2*inch, 0.8*inch]
    table = Table(table_data, colWidths=col_widths)
    table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.grey),
        ('TEXTCOLOR', (0,0), (-1,0), colors.whitesmoke),
        ('ALIGN', (0,0), (-1,-1), 'CENTER'),
        ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
        ('FONTSIZE', (0,0), (-1,0), 9),
        ('BOTTOMPADDING', (0,0), (-1,0), 12),
        ('BACKGROUND', (0,1), (-1,-1), colors.beige),
        ('FONTSIZE', (0,1), (-1,-1), 8),
        ('GRID', (0,0), (-1,-1), 1, colors.black)
    ]))
    story.append(table)
    story.append(Spacer(1, 30))
    
    # Statistical summary (percentages as text)
    story.append(Paragraph("<b>Statistical Summary</b>", styles['Heading2']))
    all_choices = {
        "p1_r1": [], "p2_r1": [], "p1_r2": [], "p2_r2": []
    }
    for game in all_games.values():
        if "period1" in game:
            if "Player 1" in game["period1"]: all_choices["p1_r1"].append(game["period1"]["Player 1"]["action"])
            if "Player 2" in game["period1"]: all_choices["p2_r1"].append(game["period1"]["Player 2"]["action"])
        if "period2" in game:
            if "Player 1" in game["period2"]: all_choices["p1_r2"].append(game["period2"]["Player 1"]["action"])
            if "Player 2" in game["period2"]: all_choices["p2_r2"].append(game["period2"]["Player 2"]["action"])
    
    def add_pct(choices, labels, title):
        if choices:
            total = len(choices)
            pcts = {c: choices.count(c)/total*100 for c in labels}
            story.append(Paragraph(f"<b>{title}</b>", styles['Normal']))
            story.append(Paragraph(f"Sample size: {total}", styles['Normal']))
            for label in labels:
                pct = pcts.get(label, 0)
                story.append(Paragraph(f"{label}: {pct:.1f}%", styles['Normal']))
            story.append(Spacer(1, 10))
        else:
            story.append(Paragraph(f"<b>{title}</b> – No data yet", styles['Normal']))
    
    add_pct(all_choices["p1_r1"], ["A","B"], "Player 1 – Period 1")
    add_pct(all_choices["p2_r1"], ["X","Y","Z"], "Player 2 – Period 1")
    add_pct(all_choices["p1_r2"], ["A","B"], "Player 1 – Period 2")
    add_pct(all_choices["p2_r2"], ["X","Y","Z"], "Player 2 – Period 2")
    
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
                "Player 1 Name": game_data.get("period1", {}).get("Player 1", {}).get("player", "Unknown"),
                "Player 2 Name": game_data.get("period1", {}).get("Player 2", {}).get("player", "Unknown"),
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
    
    # Build player-partner mapping
    player_partner = {}
    player_match_ids = {}
    for match_id, match_data in all_matches.items():
        players = match_data.get("players", [])
        if len(players) == 2:
            player_partner[players[0]] = players[1]
            player_partner[players[1]] = players[0]
            player_match_ids[players[0]] = match_id
            player_match_ids[players[1]] = match_id
    
    # Determine completed matches (both players finished period2)
    completed_matches = set()
    completed_players = set()
    for match_id, game_data in all_games.items():
        if "period2" in game_data and "Player 1" in game_data["period2"] and "Player 2" in game_data["period2"]:
            completed_matches.add(match_id)
            if match_id in all_matches:
                for p in all_matches[match_id].get("players", []):
                    completed_players.add(p)
    
    col1, col2, col3, col4 = st.columns(4)
    with col1: st.metric("Expected Players", expected_players)
    with col2: st.metric("Registered Players", len(all_players))
    with col3: st.metric("Matched Players", len(player_partner))
    with col4: st.metric("Completed Matches", len(completed_matches))
    
    if expected_players > 0:
        progress = min(len(completed_players) / expected_players, 1.0) if expected_players > 0 else 0
        st.progress(progress)
        st.write(f"Progress: {len(completed_players)}/{expected_players} players completed ({progress*100:.1f}%)")
    
    st.subheader("👥 Player Activity Monitor")
    if all_players:
        status_data = []
        for p in all_players.keys():
            partner = player_partner.get(p, "Not yet matched")
            match_id = player_match_ids.get(p, "")
            status = "🔴 Registered"
            activity = "Waiting for match"
            if partner != "Not yet matched":
                status = "🟡 Matched"
                activity = f"Matched with {partner}"
            if p in completed_players:
                status = "🟢 Completed"
                activity = f"Game finished (match {match_id})"
            status_data.append({
                "Player Name": p,
                "Partner": partner,
                "Status": status,
                "Activity": activity
            })
        st.dataframe(pd.DataFrame(status_data), use_container_width=True)
    
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
    
    # Admin controlled matching
    st.subheader("🎲 Player Matching")
    if len(all_players) >= 2 and len(all_players) % 2 == 0:
        if st.button("👥 Assign Random Matches"):
            db.reference("matches").delete()
            players_list = list(all_players.keys())
            random.shuffle(players_list)
            pairs = [players_list[i:i+2] for i in range(0, len(players_list), 2)]
            for pair in pairs:
                match_id = f"{pair[0]}_vs_{pair[1]}"
                db.reference(f"matches/{match_id}").set({"players": pair})
            st.success(f"Created {len(pairs)} matches.")
            st.rerun()
    else:
        st.info(f"Need an even number of registered players (currently {len(all_players)}).")
    
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
    all_completed = expected_players > 0 and len(completed_players) >= expected_players
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
    
    # Wait for admin to assign matches
    matches_ref = db.reference("matches")
    all_matches = matches_ref.get() or {}
    player_match = None
    role = None
    for mid, mdata in all_matches.items():
        if name in mdata.get("players", []):
            player_match = mid
            role = "Player 1" if mdata["players"][0] == name else "Player 2"
            break
    
    if not player_match:
        st.info("⏳ Waiting for admin to assign matches... The game will start once all players are matched.")
        time.sleep(3)
        st.rerun()
    
    # Gameplay
    game_ref_period1 = db.reference(f"games/{player_match}/period1")
    period1_data = game_ref_period1.get()
    payoff_matrix = {
        "A": {"X": (4, 3), "Y": (0, 0), "Z": (1, 4)},
        "B": {"X": (0, 0), "Y": (2, 1), "Z": (0, 0)}
    }
    
    if period1_data and "Player 1" in period1_data and "Player 2" in period1_data:
        # Period 1 complete
        p1a = period1_data["Player 1"]["action"]
        p2a = period1_data["Player 2"]["action"]
        payoff1 = payoff_matrix[p1a][p2a]
        st.success(f"Period 1 result: You ({role}) chose {'A' if role=='Player 1' else p2a}, partner chose {'B' if role=='Player 1' else p1a} → Payoffs {payoff1}")
        st.subheader("🔁 Period 2")
        game_ref_period2 = db.reference(f"games/{player_match}/period2")
        period2_data = game_ref_period2.get()
        if period2_data and "Player 1" in period2_data and "Player 2" in period2_data:
            p1a2 = period2_data["Player 1"]["action"]
            p2a2 = period2_data["Player 2"]["action"]
            payoff2 = payoff_matrix[p1a2][p2a2]
            st.success(f"Period 2 result: You ({role}) chose {'A' if role=='Player 1' else p2a2}, partner chose {'B' if role=='Player 1' else p1a2} → Payoffs {payoff2}")
            st.balloons()
            partner_name = period1_data["Player 2"]["player"] if role == "Player 1" else period1_data["Player 1"]["player"]
            st.success(f"✅ Game complete! You were paired with **{partner_name}**. Thank you for playing!")
        else:
            existing = game_ref_period2.child(role).get()
            if existing:
                st.info("Waiting for the other player to submit Period 2...")
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
        # Period 1 not yet complete
        existing = game_ref_period1.child(role).get()
        if existing:
            st.info("Waiting for the other player to finish Period 1...")
            time.sleep(2)
            st.rerun()
        else:
            st.subheader("🎮 Period 1: Make Your Choice")
            if role == "Player 1":
                choice = st.radio("Your action:", ["A", "B"])
            else:
                choice = st.radio("Your action:", ["X", "Y", "Z"])
            if st.button("Submit Period 1"):
                game_ref_period1.child(role).set({"action": choice, "timestamp": time.time(), "player": name})
                st.success("Submitted! Waiting for partner.")
                st.rerun()
    
    # --- Global class results: show only after ALL players have completed ---
    all_games = db.reference("games").get() or {}
    all_matches_check = db.reference("matches").get() or {}
    completed_players = set()
    for match_id, game_data in all_games.items():
        if "period2" in game_data and "Player 1" in game_data["period2"] and "Player 2" in game_data["period2"]:
            if match_id in all_matches_check:
                for p in all_matches_check[match_id].get("players", []):
                    completed_players.add(p)
    expected_players = db.reference("expected_players").get() or 0
    all_completed = expected_players > 0 and len(completed_players) >= expected_players
    
    if all_completed:
        st.header("📊 Class Results")
        p1_r1, p2_r1, p1_r2, p2_r2 = [], [], [], []
        for g in all_games.values():
            if "period1" in g:
                if "Player 1" in g["period1"]: p1_r1.append(g["period1"]["Player 1"]["action"])
                if "Player 2" in g["period1"]: p2_r1.append(g["period1"]["Player 2"]["action"])
            if "period2" in g:
                if "Player 1" in g["period2"]: p1_r2.append(g["period2"]["Player 1"]["action"])
                if "Player 2" in g["period2"]: p2_r2.append(g["period2"]["Player 2"]["action"])
        
        def show_styled_choices(choices, labels, title, bg_color, text_color):
            if choices:
                total = len(choices)
                st.markdown(
                    f"""
                    <div style="background-color:{bg_color}; border-radius:15px; padding:15px; margin-bottom:20px;">
                        <h4 style="color:{text_color}; margin:0 0 10px 0;">{title}</h4>
                        <p style="margin:0 0 15px 0; color:#333;"><strong>Sample size:</strong> {total}</p>
                        <div style="display: flex; gap: 15px; justify-content: space-around;">
                    """,
                    unsafe_allow_html=True
                )
                cols = st.columns(len(labels))
                for i, label in enumerate(labels):
                    pct = choices.count(label) / total * 100
                    cols[i].markdown(
                        f"""
                        <div style="background-color:#ffffff; border-radius:10px; padding:15px; text-align:center; box-shadow: 0 2px 4px rgba(0,0,0,0.1);">
                            <span style="font-size:28px; font-weight:bold; color:{text_color};">{label}</span><br>
                            <span style="font-size:36px; font-weight:bold; color:#333333;">{pct:.1f}%</span>
                        </div>
                        """,
                        unsafe_allow_html=True
                    )
                st.markdown("</div></div>", unsafe_allow_html=True)
            else:
                st.info(f"No data for {title}")
        
        show_styled_choices(p1_r1, ["A","B"], "Period 1 – Player 1 Choices", "#FFF3E0", "#E67E22")
        show_styled_choices(p2_r1, ["X","Y","Z"], "Period 1 – Player 2 Choices", "#E3F2FD", "#1976D2")
        show_styled_choices(p1_r2, ["A","B"], "Period 2 – Player 1 Choices", "#FFF3E0", "#E67E22")
        show_styled_choices(p2_r2, ["X","Y","Z"], "Period 2 – Player 2 Choices", "#E3F2FD", "#1976D2")
        
        if st.button("🔄 Refresh Results"):
            st.rerun()
