import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from dataclasses import dataclass
from typing import List, Dict, Optional
import random
from datetime import datetime
from models.player import (
    Player,
    MI_RETAINED,
    KKR_RETAINED,
    CSK_RETAINED,
    RR_RETAINED,
    RCB_RETAINED,
    DC_RETAINED,
    GT_RETAINED,
    LSG_RETAINED,
    PBKS_RETAINED,
    SRH_RETAINED,
    AUCTION_POOL
)
from models.team import Team  # Import the Team class
from models.auction import AuctionSimulator  # Add this import at the top

# Global constants
TOTAL_PURSE = 120.0  # Total purse in Crores for each team

# Initialize data
def initialize_ipl_teams() -> List[Team]:
    return Team.create_teams()  # Call the static method to create teams

def generate_auction_pool() -> List[Player]:
    return AUCTION_POOL

def display_team_analysis(teams: List[Team]):
    for team in teams:
        st.markdown(f"### {team.name}")
        player_analysis = team.get_player_analysis()
        st.table(player_analysis)

def get_teams_overview(teams: List[Team]) -> pd.DataFrame:
    """
    Create an overview DataFrame of all teams' statistics
    """
    overview_data = []
    for team in teams:
        team_data = {
            'Team': team.name,
            'Squad Size': len(team.players),
            'Overseas': team.get_overseas_count(),
            'Uncapped': team.get_uncapped_count(),
            'Batters': sum(1 for p in team.players if p.category == "BATTER"),
            'Bowlers': sum(1 for p in team.players if p.category == "BOWLER"),
            'All-rounders': sum(1 for p in team.players if p.category == "ALL-ROUNDER"),
            'Keepers': sum(1 for p in team.players if p.category == "WICKETKEEPER"),
            'Purse Remaining (Cr)': "{:.1f}".format(team.purse),
            'Spent (Cr)': "{:.1f}".format(TOTAL_PURSE - team.purse),  # Using 120 Cr total purse
        }
        overview_data.append(team_data)
    
    return pd.DataFrame(overview_data)

def highlight_max(s):
    """
    Highlight the maximum value in a Series in bold
    """
    is_max = s == s.max()
    return ['font-weight: bold' if v else '' for v in is_max]

# Streamlit UI
def main():
    st.set_page_config(page_title="IPL Auction Simulator", layout="wide")
    
    # Move reset button to very top of sidebar, before any tab-specific content
    with st.sidebar:
        if st.button("🔄 Reset Auction", key="reset_button"):
            reset_session_state()
    
    # Title and description
    st.title("IPL 2025 Auction Simulator")
    st.markdown("""
    This dashboard simulates the IPL 2025 auction process using AI-powered bidding strategies.
    Track live auctions, bidding wars, and team strategies in real-time.
    """)
    
    # Initialize session state variables if they don't exist
    if 'auction_completed' not in st.session_state:
        st.session_state.auction_completed = False
    if 'teams' not in st.session_state:
        st.session_state.teams = initialize_ipl_teams()
        st.session_state.auction_pool = generate_auction_pool()
    
    # Tabs for different views
    tab1, tab2, tab3, tab4 = st.tabs(["Live Auction", "Team Analysis", "Auction History", "Teams Overview"])
    
    with tab1:
        # Remove the reset button from here since it's now in the main sidebar
        st.sidebar.header("Auction Controls")  # Changed from "Simulation Controls"
        num_simulations = st.sidebar.slider("Number of Simulations", 1, 10, 1)
        
        # Run simulation button
        if st.sidebar.button("Start Auction"):
            progress_bar = st.progress(0)
            status_text = st.empty()  # Create a placeholder for status updates
            
            status_text.text("Initializing auction simulation...")
            teams = initialize_ipl_teams()
            auction_pool = generate_auction_pool()
            simulator = AuctionSimulator(teams, auction_pool)
            
            # Create containers for live updates
            latest_sale = st.empty()
            recent_transactions = st.empty()
            
            def update_progress(idx, total, player_name=None):
                progress = (idx + 1) / total
                progress_bar.progress(progress)
                if player_name:
                    status_text.text(f"Processing {player_name}... ({idx + 1}/{total})")
            
            # Run simulation with progress updates
            simulator.simulate_auction(
                progress_callback=update_progress
            )
            
            # Update each team's auction history
            for team in teams:
                team.auction_history = simulator.auction_history
            
            st.session_state.auction_history = simulator.auction_history
            st.session_state.final_summary = simulator.get_auction_summary()
            st.session_state.teams = teams
            st.session_state.auction_completed = True
            
            progress_bar.progress(1.0)
            status_text.text("Auction Complete!")
            
            # Show final results
            st.success("Auction simulation completed successfully!")
            
            # Display latest results
            if len(simulator.auction_history) > 0:
                st.markdown("### Latest Auction Results")
                recent_df = simulator.get_auction_summary().tail(5)[::-1]
                st.table(recent_df)
        
        # Always show auction results if available
        elif st.session_state.auction_completed:
            st.markdown("### Latest Auction Results")
            recent_df = st.session_state.final_summary.tail(5)[::-1]
            st.table(recent_df)
            
            # Show some bidding details
            st.markdown("### Recent Bidding Activity")
            for record in st.session_state.auction_history[-3:]:
                if record['bidding_history']:
                    st.markdown(f"**{record['player_name']}** - {record['status']}")
                    if record['status'] == 'Sold':
                        st.success(f"Sold to {record['winning_team']} for ₹{record['final_price']} Cr")
                    else:
                        st.warning("Unsold")
                    st.markdown("---")
    
        # Add a section for viewing player bids
        if st.session_state.auction_completed and st.session_state.auction_history:
            st.markdown("### 🔍 View Player Bids")
            
            # Create a dropdown with all players from auction history
            player_names = [record['player_name'] for record in st.session_state.auction_history]
            selected_player = st.selectbox(
                "Select Player",
                options=player_names,
                key="player_bid_viewer"
            )
            
            # Get the auction record for selected player
            player_record = next(
                record for record in st.session_state.auction_history 
                if record['player_name'] == selected_player
            )
            
            # Display player information
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Base Price", f"₹{player_record['base_price']:.1f} Cr")
            with col2:
                st.metric("Final Price", 
                         f"₹{player_record['final_price']:.1f} Cr" if player_record['final_price'] else "Unsold")
            with col3:
                st.metric("Status", player_record['status'])
            
            # Display bidding history in a table
            if player_record['bidding_history']:
                st.markdown("#### Bidding History")
                
                # Create DataFrame for bidding history
                bid_df = pd.DataFrame(player_record['bidding_history'])
                
                # Format the bid amounts
                bid_df['bid_amount'] = bid_df['bid_amount'].apply(lambda x: f"₹{x:.1f} Cr")
                
                # Rename columns for better display
                bid_df.columns = ['Team', 'Bid Amount', 'Status']
                
                # Apply color coding based on status
                def color_status(val):
                    if val == 'Active':
                        return 'background-color: #90EE90'  # Light green
                    elif val == 'Withdrew':
                        return 'background-color: #FFB6C6'  # Light red
                    return ''
                
                # Display styled table
                st.dataframe(
                    bid_df.style.applymap(color_status, subset=['Status']),
                    use_container_width=True
                )
                
                # Add a visual representation of the bidding war
                st.markdown("#### Bidding Progression")
                fig = px.line(
                    bid_df,
                    x=bid_df.index,
                    y=[float(amt.replace('₹', '').replace(' Cr', '')) for amt in bid_df['Bid Amount']],
                    title=f"Bidding Progression for {selected_player}",
                    labels={'x': 'Bid Number', 'y': 'Bid Amount (Cr)'}
                )
                fig.update_traces(mode='lines+markers')
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("No bidding history available for this player")
    
    with tab2:
        st.markdown("### Team Analysis")
        if 'teams' in st.session_state:  # Check if teams exist in session state
            selected_team = st.selectbox(
                "Select Team",
                options=[team.name for team in st.session_state.teams]
            )
            
            team = next(team for team in st.session_state.teams if team.name == selected_team)
            
            col1, col2 = st.columns(2)
            
            with col1:
                # Squad composition
                if team.players:  # Check if team has players
                    role_counts = {
                        role: sum(1 for p in team.players if p.category == role)
                        for role in team.required_roles.keys()
                    }
                    
                    fig_roles = px.pie(
                        values=list(role_counts.values()),
                        names=list(role_counts.keys()),
                        title="Role Distribution"
                    )
                    fig_roles.update_traces(textposition='inside', textinfo='value')
                    st.plotly_chart(fig_roles)
                    
                    # Nationality distribution
                    nationality_counts = {}
                    for p in team.players:
                        nationality_counts[p.nationality] = nationality_counts.get(p.nationality, 0) + 1
                    
                    if nationality_counts:  # Only create chart if there are players
                        fig_nationality = px.pie(
                            values=list(nationality_counts.values()),
                            names=list(nationality_counts.keys()),
                            title="Player Nationalities"
                        )
                        st.plotly_chart(fig_nationality)
                else:
                    st.info("No players in team yet.")
            
            with col2:
                # Financial summary
                st.markdown("#### Financial Overview")
                st.metric("Total Purse (Cr)", f"₹{TOTAL_PURSE:.1f}")
                st.metric("Spent (Cr)", f"₹{TOTAL_PURSE - team.purse:.1f}")
                st.metric("Remaining (Cr)", f"₹{team.purse:.1f}")

                # List of Players - Single consolidated table
                st.markdown("#### Team Squad")
                player_df = team.get_player_analysis()
                
                # Reorder columns to show prices after name
                columns_order = ['Name', 'Base Price (Cr)', 'Final Price (Cr)', 'Role']
                player_df = player_df[columns_order]
                
                st.table(player_df)
                
                # Player acquisition summary (optional - can keep or remove)
                if 'auction_history' in st.session_state:
                    team_purchases = [
                        record for record in st.session_state.auction_history
                        if record['winning_team'] == team.name
                    ]
                    
                    if team_purchases:
                        st.markdown("#### Recent Acquisitions")
                        for purchase in team_purchases:
                            st.markdown(f"""
                            * {purchase['player_name']} - ₹{purchase['final_price']} Cr
                              * Base Price: ₹{purchase['base_price']} Cr
                              * Number of bids: {len(purchase['bidding_history'])}
                            """)
    
    with tab3:
        # Auction History
        if 'auction_history' in st.session_state:
            st.markdown("### Complete Auction History")
            
            # Filters
            col1, col2, col3 = st.columns(3)
            with col1:
                status_filter = st.multiselect(
                    "Status",
                    options=['Sold', 'Unsold'],
                    default=['Sold', 'Unsold']
                )
            with col2:
                category_filter = st.multiselect(
                    "Category",
                    options=list(set(record['category'] for record in st.session_state.auction_history)),
                    default=list(set(record['category'] for record in st.session_state.auction_history))
                )
            with col3:
                team_filter = st.multiselect(
                    "Winning Team",
                    options=[team.name for team in st.session_state.teams] + ['Unsold'],
                    default=[team.name for team in st.session_state.teams] + ['Unsold']
                )
            
            # Filter data
            filtered_df = st.session_state.final_summary[
                (st.session_state.final_summary['Status'].isin(status_filter)) &
                (st.session_state.final_summary['Category'].isin(category_filter)) &
                (st.session_state.final_summary['Winning Team'].isin(team_filter))
            ]
            
            # Display filtered data
            st.dataframe(filtered_df)
            
            # Summary statistics
            st.markdown("### Auction Statistics")
            col1, col2, col3 = st.columns(3)
            
            with col1:
                st.metric("Total Players Sold", 
                         len(filtered_df[filtered_df['Status'] == 'Sold']))
            with col2:
                st.metric("Total Amount Spent (Cr)", 
                         f"₹{filtered_df[filtered_df['Status'] == 'Sold']['Final Price (Cr)'].sum():.1f}")
            with col3:
                st.metric("Average Player Price (Cr)", 
                         round(filtered_df[filtered_df['Status'] == 'Sold']['Final Price (Cr)'].mean(), 2))
            
            # Highest bids
            st.markdown("#### Top 5 Most Expensive Players")
            sold_players = filtered_df[filtered_df['Status'] == 'Sold'].copy()
            sold_players['Final Price (Cr)'] = pd.to_numeric(sold_players['Final Price (Cr)'])
            top_purchases = sold_players.nlargest(5, 'Final Price (Cr)')
            st.table(top_purchases[['Player', 'Category', 'Winning Team', 'Final Price (Cr)']])
        else:
            st.info("No auction history available. Please run an auction first.")
    
    with tab4:
        st.markdown("### Teams Overview")
        if 'teams' in st.session_state:
            overview_df = get_teams_overview(st.session_state.teams)
            
            # Convert numeric columns to appropriate type
            numeric_cols = ['Squad Size', 'Overseas', 'Uncapped', 'Batters', 'Bowlers', 'All-rounders', 'Keepers']
            for col in numeric_cols:
                overview_df[col] = pd.to_numeric(overview_df[col])
            
            # Apply styling
            styled_df = overview_df.style.apply(highlight_max)
            
            # Display the table
            st.table(styled_df)
            
            # Add summary statistics
            st.markdown("### Summary Statistics")
            
            # First row of metrics
            col1, col2, col3 = st.columns(3)
            
            with col1:
                st.metric("Total Purse (All Teams)", f"₹{TOTAL_PURSE * len(st.session_state.teams):.1f}")
            
            with col2:
                total_remaining = float(overview_df['Purse Remaining (Cr)'].str.replace(',', '').astype(float).sum())
                st.metric("Total Purse Remaining", f"₹{total_remaining:.1f}")
            
            with col3:
                total_spent = float(overview_df['Spent (Cr)'].str.replace(',', '').astype(float).sum())
                st.metric("Total Amount Spent", f"₹{total_spent:.1f}")
            
            # Second row of metrics
            col4, col5, col6 = st.columns(3)  # Create new columns for auction statistics
            
            with col4:
                if 'auction_history' in st.session_state:
                    total_auctioned = len(st.session_state.auction_history)
                    st.metric("Players Auctioned", total_auctioned)
            
            with col5:
                if 'auction_history' in st.session_state:
                    total_sold = len([r for r in st.session_state.auction_history if r['status'] == 'Sold'])
                    st.metric("Players Sold", total_sold)
            
            with col6:
                if 'auction_history' in st.session_state:
                    total_unsold = len([r for r in st.session_state.auction_history if r['status'] == 'Unsold'])
                    st.metric("Players Unsold", total_unsold)
        else:
            st.info("No team data available. Please run an auction first.")

def reset_session_state():
    """Reset all session state variables"""
    keys_to_remove = [
        'auction_completed',
        'teams',
        'auction_pool',
        'current_player',
        'current_bid',
        'current_team',
        'bidding_teams',
        'auction_history',
        'selected_team',
        'selected_player',
        'team_analysis',
        'overview_data',
        'filtered_players',
        # Add any other session state variables you're using
    ]
    
    for key in keys_to_remove:
        if key in st.session_state:
            del st.session_state[key]
    
    # Reinitialize core state
    st.session_state.teams = initialize_ipl_teams()
    st.session_state.auction_pool = generate_auction_pool()
    st.session_state.auction_completed = False
    
    # Force rerun
    st.rerun()

if __name__ == "__main__":
    main()