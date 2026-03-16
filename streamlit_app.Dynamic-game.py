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

# Game description
st.markdown("""
Game Description  
You will be matched with another player and play a 2-period dynamic game. In each period, you simultaneously choose an action.  
After both players submit, the outcome and payoffs will be shown before moving to the next round.

Payoff Matrix (Player 1, Player 2):

|     | X       | Y       | Z       |
|-----|---------|---------|---------|
| A   | (4, 3)  | (0, 0)  | (1, 4)  |
| B   | (0, 0)  | (2, 1)  | (0, 0)  |
""")

# Firebase credentials and config
firebase_key = st.secrets["firebase_key"]
database_url = st.secrets["database_url"]

if not firebase_admin._apps:
    cred = credentials.Certificate(json.loads(firebase_key))
    firebase_admin.initialize_app(cred, {
        'databaseURL': database_url
    })

# BEGIN PDF
# Function to create comprehensive PDF with all game data and graphs
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
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Title'],
        fontSize=24,
        textColor=colors.darkblue,
        spaceAfter=30
    )
    story.append(Paragraph("🎲 Dynamic Game Complete Results", title_style))
    story.append(Spacer(1, 20))
    
    # Get all game data from Firebase
    all_games = db.reference("games").get() or {}
    expected_players = db.reference("expected_players").get() or 0
    
    # Summary section
    story.append(Paragraph(f"<b>Game Summary</b>", styles['Heading2']))
    story.append(Paragraph(f"Expected Players: {expected_players}", styles['Normal']))
    story.append(Paragraph(f"Total Matches: {len(all_games)}", styles['Normal']))
    story.append(Spacer(1, 20))
    
    # Individual match results
    story.append(Paragraph("<b>Individual Match Results</b>", styles['Heading2']))
    
    # Create table data for all matches
    table_data = [["Match ID", "Period 1", "Period 1 Payoffs", "Period 2", "Period 2 Payoffs"]]
    
    for match_id, game_data in all_games.items():
        if "period1" in game_data and "period2" in game_data:
            # Period 1
            p1_action1 = game_data["period1"].get("Player 1", {}).get("action", "N/A")
            p2_action1 = game_data["period1"].get("Player 2", {}).get("action", "N/A")
            payoff_matrix = {
                "A": {"X": (4, 3), "Y": (0, 0), "Z": (1, 4)},
                "B": {"X": (0, 0), "Y": (2, 1), "Z": (0, 0)}
            }
            if p1_action1 != "N/A" and p2_action1 != "N/A":
                payoff1 = payoff_matrix[p1_action1][p2_action1]
            else:
                payoff1 = "N/A"
            
            # Period 2
            p1_action2 = game_data["period2"].get("Player 1", {}).get("action", "N/A")
            p2_action2 = game_data["period2"].get("Player 2", {}).get("action", "N/A")
            if p1_action2 != "N/A" and p2_action2 != "N/A":
                payoff2 = payoff_matrix[p1_action2][p2_action2]
            else:
                payoff2 = "N/A"
            
            table_data.append([
                match_id,
                f"P1:{p1_action1}, P2:{p2_action1}",
                str(payoff1),
                f"P1:{p1_action2}, P2:{p2_action2}",
                str(payoff2)
            ])
    
    # Create and style the table
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
    
    # Generate charts and add to PDF
    story.append(Paragraph("<b>Statistical Analysis</b>", styles['Heading2']))
    
    # Collect choice data
    p1_choices_r1, p2_choices_r1 = [], []
    p1_choices_r2, p2_choices_r2 = [], []
    
    for match in all_games.values():
        if "period1" in match:
            p1 = match["period1"].get("Player 1", {}).get("action")
            p2 = match["period1"].get("Player 2", {}).get("action")
            if p1: p1_choices_r1.append(p1)
            if p2: p2_choices_r1.append(p2)
        if "period2" in match:
            p1 = match["period2"].get("Player 1", {}).get("action")
            p2 = match["period2"].get("Player 2", {}).get("action")
            if p1: p1_choices_r2.append(p1)
            if p2: p2_choices_r2.append(p2)
    
    # Create temporary directory for chart images
    temp_dir = tempfile.mkdtemp()
    
    def create_enhanced_chart(choices, labels, title, filename, player_type):
        if len(choices) > 0:
            import pandas as pd
            counts = pd.Series(choices).value_counts(normalize=True).reindex(labels, fill_value=0) * 100
            
            # Create figure with enhanced styling
            fig, ax = plt.subplots(figsize=(10, 6))
            fig.patch.set_facecolor('#f0f0f0')
            ax.set_facecolor('#e0e0e0')
            
            # Color scheme
            colors_p1 = ['#1f77b4', '#ff7f0e'] if player_type == "P1" else ['#1f77b4', '#ff7f0e', '#2ca02c']
            
            # Create bar plot
            bars = counts.plot(kind='bar', ax=ax, color=colors_p1, linewidth=2)
            
            # Enhanced styling
            ax.set_title(title, fontsize=16, fontweight='bold', pad=20)
            ax.set_ylabel("Percentage (%)", fontsize=14)
            ax.set_xlabel("Choice", fontsize=14)
            ax.tick_params(rotation=0)
            ax.set_ylim(0, max(100, counts.max() * 1.1))
            
            # Add grid
            ax.grid(True, alpha=0.3, linestyle='-', linewidth=0.5)
            
            # Add value labels on bars
            for i, bar in enumerate(ax.patches):
                height = bar.get_height()
                ax.text(bar.get_x() + bar.get_width()/2., height + 1,
                       f'{height:.1f}%', ha='center', va='bottom', fontsize=12, fontweight='bold')
            
            # Add date
            today = datetime.today().strftime('%B %d, %Y')
            ax.text(0.02, 0.98, f"Generated: {today}", transform=ax.transAxes, 
                   fontsize=10, verticalalignment='top', alpha=0.7)
            
            plt.tight_layout()
            filepath = os.path.join(temp_dir, filename)
            plt.savefig(filepath, dpi=300, bbox_inches='tight')
            plt.close()
            return filepath
        return None
    
    # Generate enhanced charts
    chart_files = []
    if p1_choices_r1:
        chart_files.append(create_enhanced_chart(p1_choices_r1, ["A", "B"], "Player 1 Choices (Period 1)", "p1_r1.png", "P1"))
    if p2_choices_r1:
        chart_files.append(create_enhanced_chart(p2_choices_r1, ["X", "Y", "Z"], "Player 2 Choices (Period 1)", "p2_r1.png", "P2"))
    if p1_choices_r2:
        chart_files.append(create_enhanced_chart(p1_choices_r2, ["A", "B"], "Player 1 Choices (Period 2)", "p1_r2.png", "P1"))
    if p2_choices_r2:
        chart_files.append(create_enhanced_chart(p2_choices_r2, ["X", "Y", "Z"], "Player 2 Choices (Period 2)", "p2_r2.png", "P2"))
    
    # Add charts to PDF
    for chart_file in chart_files:
        if chart_file and os.path.exists(chart_file):
            story.append(Image(chart_file, width=6*inch, height=4*inch))
            story.append(Spacer(1, 20))
    
    # Add payoff matrix reference
    story.append(Paragraph("<b>Payoff Matrix Reference</b>", styles['Heading2']))
    payoff_data = [
        ["", "X", "Y", "Z"],
        ["A", "(4, 3)", "(0, 0)", "(1, 4)"],
        ["B", "(0, 0)", "(2, 1)", "(0, 0)"]
    ]
    payoff_table = Table(payoff_data, colWidths=[1*inch, 1*inch, 1*inch, 1*inch])
    payoff_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
        ('BACKGROUND', (0, 0), (0, -1), colors.grey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('TEXTCOLOR', (0, 0), (0, -1), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 12),
        ('GRID', (0, 0), (-1, -1), 1, colors.black)
    ]))
    story.append(payoff_table)
    story.append(Spacer(1, 20))
    
    story.append(Paragraph("Format: (Player 1 Payoff, Player 2 Payoff)", styles['Normal']))
    story.append(Spacer(1, 20))
    story.append(Paragraph("✅ Report generated automatically", styles['Normal']))
    
    # Build PDF
    doc.build(story)
    
    # Cleanup temporary files
    for chart_file in chart_files:
        if chart_file and os.path.exists(chart_file):
            os.remove(chart_file)
    os.rmdir(temp_dir)
    
    buffer.seek(0)
    return buffer
   
# END PDF

# Password protection for admin functions only
admin_password = st.text_input("Admin Password (for database management):", type="password")

if admin_password == "admin123":
    st.header("🔒 Admin Dashboard")
    
    # Get real-time data
    all_players = db.reference("players").get() or {}
    all_matches = db.reference("matches").get() or {}
    all_games = db.reference("games").get() or {}
    expected_players = db.reference("expected_players").get() or 0
    
    # Calculate participation statistics
    total_registered = len(all_players)
    matched_players = set()
    for match in all_matches.values():
        matched_players.update(match.get("players", []))
    
    completed_period1_players = set()
    completed_period2_players = set()
    
    for game in all_games.values():
        if "period1" in game:
            for player in game["period1"].keys():
                completed_period1_players.add(player)
        if "period2" in game:
            for player in game["period2"].keys():
                completed_period2_players.add(player)
    
    # Live Statistics Dashboard
    st.subheader("📊 Live Game Statistics")
    
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Expected Players", expected_players)
    with col2:
        st.metric("Registered Players", total_registered)
    with col3:
        st.metric("Matched Players", len(matched_players))
    with col4:
        st.metric("Completed Period 2", len(completed_period2_players))
    
    # Participation Progress Bar
    if expected_players > 0:
        progress_percentage = min(len(completed_period2_players) / expected_players, 1.0)
        st.progress(progress_percentage)
        st.write(f"Progress: {len(completed_period2_players)}/{expected_players} players completed ({progress_percentage*100:.1f}%)")
    
    # Live Player Activity Monitoring
    st.subheader("👥 Player Activity Monitor")
    
    if all_players:
        player_status = []
        for player_name in all_players.keys():
            status = "🔴 Registered"
            current_activity = "Waiting to be matched"
            
            if player_name in matched_players:
                status = "🟡 Matched"
                current_activity = "Matched with partner"
                
            if player_name in completed_period1_players:
                status = "🔵 Period 1 Done"
                current_activity = "Completed Period 1"
                
            if player_name in completed_period2_players:
                status = "🟢 Completed"
                current_activity = "Game finished"
            
            player_status.append({
                "Player Name": player_name,
                "Status": status,
                "Activity": current_activity
            })
        
        # Display as a table
        if player_status:
            status_df = pd.DataFrame(player_status)
            st.dataframe(status_df, use_container_width=True)
    else:
        st.info("No players registered yet.")
    
    # Live Choice Analytics
    st.subheader("📈 Live Choice Analytics")
    
    if all_games:
        # Collect choice data for Period 1
        p1_choices_r1, p2_choices_r1 = [], []
        p1_choices_r2, p2_choices_r2 = [], []
        
        for match in all_games.values():
            if "period1" in match:
                p1_action = match["period1"].get("Player 1", {}).get("action")
                p2_action = match["period1"].get("Player 2", {}).get("action")
                if p1_action: p1_choices_r1.append(p1_action)
                if p2_action: p2_choices_r1.append(p2_action)
            if "period2" in match:
                p1_action = match["period2"].get("Player 1", {}).get("action")
                p2_action = match["period2"].get("Player 2", {}).get("action")
                if p1_action: p1_choices_r2.append(p1_action)
                if p2_action: p2_choices_r2.append(p2_action)
        
        # Enhanced admin charts function
        def plot_admin_chart(choices, labels, title, player_type):
            if len(choices) > 0:
                counts = pd.Series(choices).value_counts(normalize=True).reindex(labels, fill_value=0) * 100
                
                fig, ax = plt.subplots(figsize=(8, 5))
                fig.patch.set_facecolor('#f8f9fa')
                ax.set_facecolor('#ffffff')
                
                colors_scheme = ['#e74c3c', '#3498db'] if player_type == "P1" else ['#e74c3c', '#3498db', '#2ecc71']
                
                bars = counts.plot(kind='bar', ax=ax, color=colors_scheme, linewidth=2, width=0.6)
                
                ax.set_title(title, fontsize=14, fontweight='bold', pad=15)
                ax.set_ylabel("Percentage (%)", fontsize=12)
                ax.set_xlabel("Choice", fontsize=12)
                ax.tick_params(rotation=0, labelsize=10)
                ax.set_ylim(0, max(100, counts.max() * 1.1))
                
                ax.grid(True, alpha=0.2, linestyle='-', linewidth=0.5)
                
                # Add value labels
                for i, bar in enumerate(ax.patches):
                    height = bar.get_height()
                    ax.text(bar.get_x() + bar.get_width()/2., height + 2,
                           f'{height:.1f}%', ha='center', va='bottom', fontsize=10, fontweight='bold')
                
                # Add sample info
                ax.text(0.02, 0.95, f"n={len(choices)}", transform=ax.transAxes, 
                       fontsize=9, bbox=dict(boxstyle='round,pad=0.3', facecolor='lightgray', alpha=0.7))
                
                plt.tight_layout()
                return fig
            else:
                # Create empty chart
                fig, ax = plt.subplots(figsize=(8, 5))
                ax.text(0.5, 0.5, f'No data yet for {title}', ha='center', va='center', 
                       fontsize=12, transform=ax.transAxes)
                ax.set_title(title, fontsize=14, fontweight='bold')
                return fig
        
        # Period 1 Charts
        st.markdown("**Period 1 Choices**")
        col1, col2 = st.columns(2)
        
        with col1:
            fig1 = plot_admin_chart(p1_choices_r1, ["A", "B"], "Player 1 Choices (Period 1)", "P1")
            st.pyplot(fig1)
            
        with col2:
            fig2 = plot_admin_chart(p2_choices_r1, ["X", "Y", "Z"], "Player 2 Choices (Period 1)", "P2")
            st.pyplot(fig2)
        
        # Period 2 Charts
        if p1_choices_r2 or p2_choices_r2:
            st.markdown("**Period 2 Choices**")
            col3, col4 = st.columns(2)
            
            with col3:
                fig3 = plot_admin_chart(p1_choices_r2, ["A", "B"], "Player 1 Choices (Period 2)", "P1")
                st.pyplot(fig3)
                
            with col4:
                fig4 = plot_admin_chart(p2_choices_r2, ["X", "Y", "Z"], "Player 2 Choices (Period 2)", "P2")
                st.pyplot(fig4)
    
    # Game Configuration
    st.subheader("⚙️ Game Configuration")
    current_expected = db.reference("expected_players").get() or 0
    st.write(f"Current expected players: {current_expected}")
    
    new_expected_players = st.number_input(
        "Set expected number of players:", 
        min_value=0, 
        max_value=100, 
        value=current_expected,
        step=2,
        help="Must be an even number (players are paired)"
    )
    
    if st.button("⚙ Update Expected Players"):
        if new_expected_players % 2 == 0:  # Must be even for pairing
            db.reference("expected_players").set(new_expected_players)
            st.success(f"✅ Expected players set to {new_expected_players}")
            st.rerun()
        else:
            st.error("⚠ Number of players must be even (for pairing)")
    
    # Game Management
    st.subheader("📄 Game Management")
    
    # PDF Download
    if st.button("📄 Download Complete Game Report (PDF)"):
        with st.spinner("Generating comprehensive PDF report..."):
            try:
                pdf_buffer = create_comprehensive_pdf()
                b64 = base64.b64encode(pdf_buffer.read()).decode()
                href = f'<a href="data:application/pdf;base64,{b64}" download="complete_game_results.pdf">Click here to download Complete Game Report</a>'
                st.markdown(href, unsafe_allow_html=True)
                st.success("✅ Complete game report generated successfully!")
            except Exception as e:
                st.error(f"Error generating PDF: {str(e)}")
    
    # Database cleanup
    if st.button("🗑 Delete ALL Game Data"):
        db.reference("games").delete()
        db.reference("matches").delete()
        db.reference("players").delete()
        db.reference("expected_players").set(0)
        st.success("🧹 ALL game data deleted from Firebase.")
        st.warning("⚠ All players, matches, and game history have been permanently removed.")
        st.rerun()
    
    # Auto-refresh admin dashboard - STOP when all players complete
    all_completed = expected_players > 0 and len(completed_period2_players) >= expected_players
    
    if all_completed:
        # All completed - stop auto refresh permanently
        st.success("🎉 All participants completed! Admin monitoring complete.")
        if st.button("🔄 Manual Refresh Dashboard"):
            st.rerun()
    else:
        # Only auto-refresh if not all completed
        time.sleep(3)
        st.rerun()
    
    # Stop here - admin doesn't participate in the game
    st.stop()

# Check if expected players is set
if (db.reference("expected_players").get() or 0) <= 0:
    st.info("⚠️ Game not configured yet. Admin needs to set expected number of players.")
    st.stop()

# Initialize variables to avoid undefined errors
already_matched = False
match_id = None
role = None
pair = None

name = st.text_input("Enter your name to join the game:")

if name:
    st.success(f"👋 Welcome, {name}!")

    player_ref = db.reference(f"players/{name}")
    player_data = player_ref.get()

    if not player_data:
        player_ref.set({
            "joined": True,
            "timestamp": time.time()
        })
        st.write("✅ Firebase is connected and you are registered.")

    match_ref = db.reference("matches")
    match_data = match_ref.get() or {}

    # Check if player already matched
    already_matched = False
    for match_id, info in match_data.items():
        if name in info.get("players", []):
            role = "Player 1" if info["players"][0] == name else "Player 2"
            st.success(f"🎮 Hello, {name}! You are {role} in match {match_id}")
            already_matched = True
            break

    if not already_matched:
        # Check if all expected players have finished playing
        expected_players_ref = db.reference("expected_players")
        expected_players = expected_players_ref.get() or 0
        all_games = db.reference("games").get() or {}
        
        # Count completed players
        completed_players = 0
        for match_id, game_data in all_games.items():
            if "period1" in game_data and "period2" in game_data:
                if "Player 1" in game_data["period1"] and "Player 2" in game_data["period1"] \
                and "Player 1" in game_data["period2"] and "Player 2" in game_data["period2"]:
                    completed_players += 2
        
        # If all expected players have completed, no more matches allowed
        if expected_players >= 0 and completed_players >= expected_players:
            st.info("🎯 All games have been completed! No more matches are available.")
            st.info("📊 Check the Game Summary section below to see the results.")
        else:
            # Get fresh data to avoid race conditions
            players_data = db.reference("players").get() or {}
            match_data = db.reference("matches").get() or {}
            
            unmatched = [p for p in players_data.keys()
                         if not any(p in m.get("players", []) for m in match_data.values())
                         and p != name]

            if unmatched:
                partner = unmatched[0]
                pair = sorted([name, partner])
                match_id = f"{pair[0]}_vs_{pair[1]}"
                
                # Double-check that the match doesn't already exist (race condition protection)
                existing_match = match_ref.child(match_id).get()
                if not existing_match:
                    match_ref.child(match_id).set({"players": pair})
                    role = "Player 1" if pair[0] == name else "Player 2"
                    st.success(f"🎮 Hello, {name}! You are {role} in match {match_id}")
                else:
                    # Match was created by another player, check our role
                    role = "Player 1" if existing_match["players"][0] == name else "Player 2"
                    st.success(f"🎮 Hello, {name}! You are {role} in match {match_id}")
                    already_matched = True
            else:
                st.info("⏳ Waiting for another player to join...")
                with st.spinner("Checking for match..."):
                    timeout = 30
                    for i in range(timeout):
                        match_data = match_ref.get() or {}
                        for match_id, info in match_data.items():
                            if name in info.get("players", []):
                                role = "Player 1" if info["players"][0] == name else "Player 2"
                                st.success(f"🎮 Hello, {name}! You are {role} in match {match_id}")
                                already_matched = True
                                st.rerun()
                        time.sleep(2)

    # ✅ Once matched, proceed to Period 1 gameplay
    if already_matched or role is not None:
        match_id = match_id if already_matched else f"{pair[0]}_vs_{pair[1]}"
        role = role if already_matched else ("Player 1" if pair[0] == name else "Player 2")
        game_ref = db.reference(f"games/{match_id}/period1")

        # Check if both players already completed Period 1
        period1_data = game_ref.get()
        if period1_data and "Player 1" in period1_data and "Player 2" in period1_data:
            # Both players have submitted - show results and automatically go to Period 2
            action1 = period1_data["Player 1"]["action"]
            action2 = period1_data["Player 2"]["action"]
            payoff_matrix = {
                "A": {"X": (4, 3), "Y": (0, 0), "Z": (1, 4)},
                "B": {"X": (0, 0), "Y": (2, 1), "Z": (0, 0)}
            }
            payoff = payoff_matrix[action1][action2]
            st.success(f"🎯 Period 1 Outcome: P1 = {action1}, P2 = {action2} → Payoffs = {payoff}")
            
            # Automatically set flag to go to Period 2
            st.session_state["go_to_period2"] = True
        else:
            # Display available choices for Period 1
            st.subheader("🎮 Period 1: Make Your Choice")
            
            existing_action = game_ref.child(role).get()
            if existing_action:
                st.info(f"✅ You already submitted: {existing_action['action']}")
                st.info("⏳ Waiting for the other player to submit...")
                
                # Auto-refresh to check for other player's submission
                time.sleep(2)
                st.rerun()
            else:
                if role == "Player 1":
                    choice = st.radio("Choose your action:", ["A", "B"])
                else:
                    choice = st.radio("Choose your action:", ["X", "Y", "Z"])

                if st.button("Submit Choice"):
                    game_ref.child(role).set({
                        "action": choice,
                        "timestamp": time.time()
                    })
                    st.success("✅ Your choice has been submitted!")
                    time.sleep(1)
                    st.rerun()

        # ✅ Period 2 logic (automatically triggered after Period 1 completes)
        if st.session_state.get("go_to_period2", False):
            st.subheader("🔁 Period 2: Make Your Choice (Knowing Period 1 Outcome)")

            # Ensure match_id is properly set
            if not match_id and pair:
                match_id = f"{pair[0]}_vs_{pair[1]}"
            period1_data = db.reference(f"games/{match_id}/period1").get()
            if period1_data and "Player 1" in period1_data and "Player 2" in period1_data:
                action1 = period1_data["Player 1"]["action"]
                action2 = period1_data["Player 2"]["action"]
                payoff_matrix = {
                    "A": {"X": (4, 3), "Y": (0, 0), "Z": (1, 4)},
                    "B": {"X": (0, 0), "Y": (2, 1), "Z": (0, 0)}
                }
                period1_payoff = payoff_matrix[action1][action2]
                st.info(f"📢 In Period 1: P1 = {action1}, P2 = {action2} → Payoffs = {period1_payoff}")

            # Let players choose again for Period 2
            game_ref2 = db.reference(f"games/{match_id}/period2")

            # Check if both players already completed Period 2
            period2_data = game_ref2.get()
            if period2_data and "Player 1" in period2_data and "Player 2" in period2_data:
                # Both players completed - show final results first
                action1_2 = period2_data["Player 1"]["action"]
                action2_2 = period2_data["Player 2"]["action"]
                payoff_matrix = {
                    "A": {"X": (4, 3), "Y": (0, 0), "Z": (1, 4)},
                    "B": {"X": (0, 0), "Y": (2, 1), "Z": (0, 0)}
                }
                payoff2 = payoff_matrix[action1_2][action2_2]
                
                # Show results first
                st.success(f"🎯 Period 2 Outcome: P1 = {action1_2}, P2 = {action2_2} → Payoffs = {payoff2}")
                st.markdown("✅ Game Complete! Thanks for playing.")
                
                # Initialize variables for PDF functionality
                st.session_state["game_complete"] = True
                st.session_state["match_id"] = match_id
                st.session_state["action1"] = action1
                st.session_state["action2"] = action2
                st.session_state["period1_payoff"] = period1_payoff
                st.session_state["action1_2"] = action1_2
                st.session_state["action2_2"] = action2_2
                st.session_state["payoff2"] = payoff2
                st.session_state["pair"] = pair
                
                # Check if all players finished
                expected_players = db.reference("expected_players").get() or 0
                all_games_check = db.reference("games").get() or {}
                completed_check = 0
                for mid, gdata in all_games_check.items():
                    if "period1" in gdata and "period2" in gdata:
                        if "Player 1" in gdata["period1"] and "Player 2" in gdata["period1"] \
                        and "Player 1" in gdata["period2"] and "Player 2" in gdata["period2"]:
                            completed_check += 2
                
                if expected_players > 0 and completed_check >= expected_players:
                    st.success("🎉 All players have finished! Results are now available below.")
                    st.info("📊 Scroll down to see the complete game results and charts.")
                    st.session_state["all_games_complete"] = True
                
                # 🎈 BALLOONS CELEBRATION after showing results! 🎈
                if not st.session_state.get("balloons_shown", False):
                    st.balloons()
                    st.session_state["balloons_shown"] = True
                
                # Show immediate game summary for this player
                st.session_state["show_immediate_results"] = True
            else:
                # Period 2 gameplay
                existing_action2 = game_ref2.child(role).get()
                if existing_action2:
                    st.info(f"✅ You already submitted: {existing_action2['action']}")
                    st.info("⏳ Waiting for the other player to submit their Period 2 action...")
                    
                    # Auto-refresh to check for other player's submission
                    time.sleep(2)
                    st.rerun()
                else:
                    if role == "Player 1":
                        choice2 = st.radio("Choose your Period 2 action:", ["A", "B"], key="p1_period2")
                    else:
                        choice2 = st.radio("Choose your Period 2 action:", ["X", "Y", "Z"], key="p2_period2")

                    if st.button("Submit Period 2 Choice"):
                        game_ref2.child(role).set({
                            "action": choice2,
                            "timestamp": time.time()
                        })
                        st.success("✅ Your Period 2 choice has been submitted!")
                        time.sleep(1)
                        st.rerun()


# SHOW GAME SUMMARY ONLY AFTER PERIOD 2 COMPLETION
if st.session_state.get("show_immediate_results", False):
    
    # Enhanced chart function with improved styling
    def plot_enhanced_percentage_bar(choices, labels, title, player_type):
        if len(choices) > 0:
            counts = pd.Series(choices).value_counts(normalize=True).reindex(labels, fill_value=0) * 100
            
            # Create figure with enhanced styling
            fig, ax = plt.subplots(figsize=(10, 6))
            fig.patch.set_facecolor('#f0f0f0')
            ax.set_facecolor('#e0e0e0')
            
            # Color scheme based on player type
            colors_p1 = ['#1f77b4', '#ff7f0e'] if player_type == "P1" else ['#1f77b4', '#ff7f0e', '#2ca02c']
            
            # Create bar plot with enhanced styling
            bars = counts.plot(kind='bar', ax=ax, color=colors_p1, linewidth=2, width=0.7)
            
            # Enhanced styling
            ax.set_title(title, fontsize=16, fontweight='bold', pad=20)
            ax.set_ylabel("Percentage (%)", fontsize=14)
            ax.set_xlabel("Choice", fontsize=14)
            ax.tick_params(rotation=0, labelsize=12)
            ax.set_ylim(0, max(100, counts.max() * 1.1))
            
            # Add grid for better readability
            ax.grid(True, alpha=0.3, linestyle='-', linewidth=0.5)
            
            # Add value labels on bars
            for i, bar in enumerate(ax.patches):
                height = bar.get_height()
                ax.text(bar.get_x() + bar.get_width()/2., height + 1,
                       f'{height:.1f}%', ha='center', va='bottom', fontsize=12, fontweight='bold')
            
            # Add sample size info
            ax.text(0.02, 0.98, f"Sample size: {len(choices)} participants", 
                   transform=ax.transAxes, fontsize=10, verticalalignment='top', alpha=0.7,
                   bbox=dict(boxstyle='round,pad=0.3', facecolor='white', alpha=0.8))
            
            # Add current date
            today = datetime.today().strftime('%B %d, %Y')
            ax.text(0.98, 0.98, f"Generated: {today}", transform=ax.transAxes, 
                   fontsize=10, verticalalignment='top', horizontalalignment='right', alpha=0.7)
            
            plt.tight_layout()
            st.pyplot(fig)
        else:
            st.warning(f"⚠ No data available for {title}")

    st.header("📊 Game Summary - Your Results!")

    # Get current game data
    all_games = db.reference("games").get() or {}
    expected_players = db.reference("expected_players").get() or 0
    
    # Count completed players for status
    completed_players = 0
    for match_id, game_data in all_games.items():
        if "period1" in game_data and "period2" in game_data:
            if "Player 1" in game_data["period1"] and "Player 2" in game_data["period1"] \
            and "Player 1" in game_data["period2"] and "Player 2" in game_data["period2"]:
                completed_players += 2

    if expected_players > 0 and completed_players >= expected_players:
        st.success(f"✅ All {expected_players} players completed both rounds. Final results:")
    else:
        st.success("✅ Your game is complete! Here are the current results:")

    p1_choices_r1, p2_choices_r1 = [], []
    p1_choices_r2, p2_choices_r2 = [], []

    for match in all_games.values():
        # Round 1
        if "period1" in match:
            p1 = match["period1"].get("Player 1", {}).get("action")
            p2 = match["period1"].get("Player 2", {}).get("action")
            if p1: p1_choices_r1.append(p1)
            if p2: p2_choices_r1.append(p2)
        # Round 2
        if "period2" in match:
            p1 = match["period2"].get("Player 1", {}).get("action")
            p2 = match["period2"].get("Player 2", {}).get("action")
            if p1: p1_choices_r2.append(p1)
            if p2: p2_choices_r2.append(p2)

    st.subheader("🎯 Period 1 Results")
    col1, col2 = st.columns(2)
    
    with col1:
        plot_enhanced_percentage_bar(p1_choices_r1, ["A", "B"], "Player 1 Choices (Period 1)", "P1")
    with col2:
        plot_enhanced_percentage_bar(p2_choices_r1, ["X", "Y", "Z"], "Player 2 Choices (Period 1)", "P2")

    st.subheader("🔄 Period 2 Results")
    col3, col4 = st.columns(2)
    
    with col3:
        plot_enhanced_percentage_bar(p1_choices_r2, ["A", "B"], "Player 1 Choices (Period 2)", "P1")
    with col4:
        plot_enhanced_percentage_bar(p2_choices_r2, ["X", "Y", "Z"], "Player 2 Choices (Period 2)", "P2")

    st.markdown("---")
    st.markdown("🎮 **Thank you for participating in the 2-Period Dynamic Game!**")
