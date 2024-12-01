from dataclasses import dataclass
from typing import List, Dict, Optional, Callable
from datetime import datetime
from .player import Player
from .team import Team
import pandas as pd

class AuctionSimulator:
    def __init__(self, teams: List[Team], players: List[Player]):
        self.teams = teams
        self.players = players
        self.sold_players: Dict[str, tuple] = {}
        self.auction_history: List[Dict] = []
        
        # Define the set order
        self.set_order = [
            'M1', 'M2',
            'AL1', 'AL2', 'AL3', 'AL4', 'AL5', 'AL6', 'AL7', 'AL8', 'AL9', 'AL10',
            'BA1', 'BA2', 'BA3', 'BA4', 'BA5',
            'FA1', 'FA2', 'FA3', 'FA4', 'FA5', 'FA6', 'FA7', 'FA8', 'FA9', 'FA10',
            'SP1', 'SP2', 'SP3',
            'WK1', 'WK2', 'WK3', 'WK4',
            'UAL1', 'UAL2', 'UAL3', 'UAL4', 'UAL5', 'UAL6', 'UAL7', 'UAL8', 'UAL9', 'UAL10',
            'UAL11', 'UAL12', 'UAL13', 'UAL14', 'UAL15',
            'UBA1', 'UBA2', 'UBA3', 'UBA4', 'UBA5', 'UBA6', 'UBA7', 'UBA8', 'UBA9',
            'UFA1', 'UFA2', 'UFA3', 'UFA4', 'UFA5', 'UFA6', 'UFA7', 'UFA8', 'UFA9', 'UFA10',
            'USP1', 'USP2', 'USP3', 'USP4', 'USP5',
            'UWK1', 'UWK2', 'UWK3', 'UWK4', 'UWK5', 'UWK6'
        ]
        
    def simulate_auction(self, progress_callback: Optional[Callable] = None):
        # Cache the sorted players to avoid repeated sorting
        sorted_players = self._get_sorted_players()
        
        # Pre-calculate player capabilities to avoid repeated calculations
        team_capabilities = [(team, team.calculate_capabilities()) for team in self.teams]
        
        current_set = None
        for idx, player in enumerate(sorted_players):
            player_set = getattr(player, '2025_Set', 'Unassigned')
            
            if player_set != current_set:
                current_set = player_set
                if progress_callback:
                    progress_callback(idx, len(sorted_players), f"Starting Set {current_set}")
            
            if progress_callback:
                progress_callback(idx, len(sorted_players), f"{player.name} ({current_set})")
            
            # Create auction record with only necessary fields
            auction_record = self._create_auction_record(player, player_set)
            
            # Optimize team filtering using the pre-calculated capabilities
            interested_teams = [
                team for team, capabilities in team_capabilities 
                if team.purse >= player.base_price and 
                capabilities.can_accommodate(player)
            ]
            
            if not interested_teams:
                self.auction_history.append(auction_record)
                continue
            
            self._process_bidding(player, interested_teams, auction_record)
            self.auction_history.append(auction_record)
    
    def _get_sorted_players(self):
        """Pre-sort players according to set order"""
        sorted_players = []
        
        # Process each set in order
        for set_name in self.set_order:
            # Get all players from current set
            set_players = [
                player for player in self.players 
                if player.set_2025 == set_name
            ]
            
            # Sort players within the set by base price and IPL experience
            set_players.sort(key=lambda x: (-x.base_price, -x.ipl_seasons))
            sorted_players.extend(set_players)
        
        # Add any remaining players (those without a set or unknown set)
        remaining = [
            p for p in self.players 
            if p.set_2025 not in self.set_order
        ]
        remaining.sort(key=lambda x: (-x.base_price, -x.ipl_seasons))
        sorted_players.extend(remaining)
        
        return sorted_players
    
    def _create_auction_record(self, player, player_set):
        """Create a basic auction record"""
        return {
            "player_name": player.name,
            "base_price": player.base_price,
            "category": player.category,
            "nationality": player.nationality,
            "test_caps": player.test_caps,
            "odi_caps": player.odi_caps,
            "t20_caps": player.t20_caps,
            "ipl_seasons": player.ipl_seasons,
            "set": player_set,
            "timestamp": datetime.now().strftime("%H:%M:%S"),
            "bidding_history": [],
            "final_price": None,
            "winning_team": None,
            "status": "Unsold"
        }
    
    def _get_bid_increment(self, current_price: float) -> float:
        """
        Returns the appropriate bid increment based on current price
        All amounts are in Crores
        """
        if current_price <= 1.0:  # Up to 1 crore
            return 0.05  # 5 lakh increment
        elif current_price <= 2.0:  # 1-2 crore
            return 0.10  # 10 lakh increment
        elif current_price <= 3.0:  # 2-3 crore
            return 0.10  # 10 lakh increment
        elif current_price <= 5.0:  # 3-5 crore
            return 0.20  # 20 lakh increment
        elif current_price <= 10.0:  # 5-10 crore
            return 0.20  # 20 lakh increment
        else:  # Above 10 crore
            return 0.50  # 50 lakh increment
    
    def _process_bidding(self, player, interested_teams, auction_record):
        """Handle the bidding process for a player"""
        current_price = player.base_price
        active_teams = interested_teams.copy()
        last_bidder = None
        
        while active_teams:
            for team in active_teams[:]:
                max_bid = team.calculate_bid_value(player)
                if max_bid <= current_price or current_price > team.purse:
                    auction_record["bidding_history"].append({
                        "team": team.name,
                        "bid_amount": current_price,
                        "status": "Withdrew"
                    })
                    active_teams.remove(team)
                else:
                    # Get the appropriate increment based on current price
                    increment = self._get_bid_increment(current_price)
                    new_price = round(current_price + increment, 2)
                    
                    auction_record["bidding_history"].append({
                        "team": team.name,
                        "bid_amount": new_price,
                        "status": "Active"
                    })
                    current_price = new_price
                    last_bidder = team
            
            if len(active_teams) == 1 and last_bidder == active_teams[0]:
                break
        
        if last_bidder and current_price <= last_bidder.purse:
            self._finalize_sale(player, last_bidder, current_price, auction_record)
    
    def _finalize_sale(self, player: Player, winning_team: Team, final_price: float, auction_record: Dict):
        """Finalize the sale of a player with validation"""
        # Validate one final time before completing the sale
        if not winning_team.can_bid(player):
            auction_record["status"] = "Unsold"
            auction_record["final_price"] = None
            auction_record["winning_team"] = None
            print(f"Sale validation failed for {player.name} to {winning_team.name}")
            return False
        
        winning_team.players.append(player)
        winning_team.purse -= final_price
        self.sold_players[player.name] = (winning_team.name, final_price)
        
        auction_record["final_price"] = final_price
        auction_record["winning_team"] = winning_team.name
        auction_record["status"] = "Sold"
        
        winning_team.auction_history = self.auction_history
        return True
    
    def get_auction_summary(self) -> pd.DataFrame:
        """Create a summary DataFrame of the auction results"""
        summary_data = []
        for record in self.auction_history:
            summary_data.append({
                'Player': record['player_name'],
                'Set': record['set'],  # Add set to the summary
                'Category': record['category'],
                'Nationality': record['nationality'],
                'Base Price (Cr)': record['base_price'],
                'Final Price (Cr)': float(record['final_price']) if record['final_price'] else 0,
                'Winning Team': record['winning_team'] if record['winning_team'] else 'Unsold',
                'Status': record['status'],
                'Number of Bids': len(record['bidding_history'])
            })
        return pd.DataFrame(summary_data) 