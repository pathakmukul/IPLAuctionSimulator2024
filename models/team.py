from dataclasses import dataclass, field
from typing import List, Dict
from models.player import Player
import random
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
import pandas as pd
from datetime import datetime

@dataclass
class TeamCapabilities:
    """Helper class to store team capabilities"""
    can_add_overseas: bool = True
    can_add_uncapped: bool = True
    has_keeper: bool = False
    role_counts: Dict[str, int] = field(default_factory=dict)

    def can_accommodate(self, player: Player) -> bool:
        """Check if team can accommodate a player based on various rules"""
        # Check overseas player limit
        if player.nationality != "Indian" and not self.can_add_overseas:
            return False
            
        # Check if we need a keeper and this is not one
        if not self.has_keeper and len(self.role_counts) >= 15:
            if player.category != "WICKETKEEPER":
                return False
                
        return True

@dataclass
class Team:
    name: str
    purse: float
    players: List[Player]
    max_squad_size: int = 25
    min_squad_size: int = 18
    max_overseas: int = 8
    min_overseas: int = 6
    max_uncapped: int = 5
    min_uncapped: int = 2
    required_roles: Dict[str, tuple] = field(default_factory=lambda: {
        "BATTER": (6, 8),
        "BOWLER": (6, 8),
        "ALL-ROUNDER": (3, 6),
        "WICKETKEEPER": (1, 3)
    })
    retained_players: List[Player] = None
    auction_history: List[Dict] = None

    def __post_init__(self):
        self.retained_players = self.players.copy()
        # Standardize the required_roles categories based on Excel categories
        self.standardized_roles = {
            "BATTER": ("Batsman", (6, 8)),
            "BOWLER": ("Bowler", (6, 8)), 
            "ALL-ROUNDER": ("All-rounder", (3, 6)),
            "WICKETKEEPER": ("Wicket-keeper", (1, 3)),
        }

    def get_standardized_category(self, category: str) -> str:
        """Convert any category variation to standard format"""
        if category in self.standardized_roles:
            return self.standardized_roles[category][0]
        # If category not found, try to match with closest category
        for std_cat, (full_cat, _) in self.standardized_roles.items():
            if category.lower().replace(" ", "") in std_cat.lower().replace(" ", ""):
                return full_cat
        # Default to All-rounder if unknown category
        print(f"Warning: Unknown category '{category}' defaulting to All-rounder")
        return "All-rounder"

    def get_role_requirements(self, category: str) -> tuple:
        """Get min/max requirements for a category"""
        std_category = self.get_standardized_category(category)
        for _, (cat, requirements) in self.standardized_roles.items():
            if cat == std_category:
                return requirements
        return (3, 6)  # Default requirements if category not found

    def get_uncapped_count(self) -> int:
        """Count number of uncapped players in the team"""
        return sum(1 for p in self.players if p.test_caps + p.odi_caps + p.t20_caps == 0)

    def can_bid(self, player: Player) -> bool:
        """Check if team can bid on a player"""
        # Basic checks
        if player.base_price > self.purse:
            return False

        current_squad_size = len(self.players)
        if current_squad_size >= self.max_squad_size:
            return False

        # Get current composition
        role_counts = {
            "BATTER": sum(1 for p in self.players if p.category == "BATTER"),
            "BOWLER": sum(1 for p in self.players if p.category == "BOWLER"),
            "ALL-ROUNDER": sum(1 for p in self.players if p.category == "ALL-ROUNDER"),
            "WICKETKEEPER": sum(1 for p in self.players if p.category == "WICKETKEEPER")
        }
        overseas_count = self.get_overseas_count()

        # Check overseas limit
        if player.nationality != "India" and overseas_count >= self.max_overseas:
            return False

        # Check role limits
        min_req, max_req = self.required_roles[player.category]
        if role_counts[player.category] >= max_req:
            return False

        # Check if we can still meet minimum requirements for other roles
        remaining_slots = self.max_squad_size - current_squad_size - 1
        for role, (min_req, _) in self.required_roles.items():
            if role != player.category:
                current = role_counts[role]
                if current < min_req:
                    remaining_slots -= (min_req - current)

        if remaining_slots < 0:
            return False

        # Check if we can afford minimum squad size
        remaining_min_slots = max(0, self.min_squad_size - current_squad_size - 1)
        if remaining_min_slots > 0:
            min_cost_per_player = 0.2  # 20L per player minimum
            if (self.purse - player.base_price) < (remaining_min_slots * min_cost_per_player):
                return False

        return True

    def calculate_bid_value(self, player: Player) -> float:
        """Calculate maximum bid value for a player based on available attributes"""
        # Base value is the player's base price
        base_value = player.base_price
        
        # Experience multiplier based on IPL experience and current status
        experience_multiplier = 1.0
        if player.current_ipl_status == "Y":  # If player was in IPL 2024
            experience_multiplier *= 1.5
        if player.ipl_seasons > 100:  # Veteran IPL player
            experience_multiplier *= 1.5
        elif player.ipl_seasons > 50:  # Experienced IPL player
            experience_multiplier *= 1.3

        # International experience multiplier
        caps_multiplier = 1.0
        total_intl_caps = player.test_caps + player.odi_caps + player.t20_caps
        if total_intl_caps > 100:
            caps_multiplier = 1.8
        elif total_intl_caps > 50:
            caps_multiplier = 1.5
        elif total_intl_caps > 20:
            caps_multiplier = 1.3

        # Role-based urgency multiplier
        role_counts = {
            "BATTER": sum(1 for p in self.players if p.category == "BATTER"),
            "BOWLER": sum(1 for p in self.players if p.category == "BOWLER"),
            "ALL-ROUNDER": sum(1 for p in self.players if p.category == "ALL-ROUNDER"),
            "WICKETKEEPER": sum(1 for p in self.players if p.category == "WICKETKEEPER")
        }
        
        min_required, max_allowed = self.required_roles[player.category]
        current_count = role_counts[player.category]
        
        urgency_multiplier = 1.0
        if current_count < min_required:
            urgency_multiplier = 2.0
        elif current_count < (min_required + 1):
            urgency_multiplier = 1.5

        # Special multipliers
        special_multiplier = 1.0
        if player.nationality != "India":  # International players
            special_multiplier *= 1.3
        if player.current_ipl_team:  # Player was in a team in 2024
            special_multiplier *= 1.2
        if player.age <= 25:  # Young player
            special_multiplier *= 1.2

        # Market competition factor - bid higher if we have more purse
        purse_factor = 1.0
        if self.purse > 30:
            purse_factor = 1.4
        elif self.purse > 20:
            purse_factor = 1.2

        # Calculate final value
        final_value = (base_value * 
                      experience_multiplier * 
                      caps_multiplier * 
                      urgency_multiplier * 
                      special_multiplier * 
                      purse_factor)

        # Add some randomization (±15%)
        randomization = random.uniform(0.85, 1.15)
        final_value *= randomization

        # Set minimum thresholds based on international caps
        if total_intl_caps > 50:  # Experienced international player
            final_value = max(final_value, 4.0)  # Minimum 4 Cr
        if player.category == "WICKETKEEPER":
            final_value = max(final_value, 2.0)  # Minimum 2 Cr for keepers

        # Cap based on remaining purse (leave some buffer for other players)
        max_bid = min(final_value, self.purse * 0.4)  # Won't spend more than 40% of purse on one player

        # Round to 2 decimal places
        return round(max_bid, 2)

    def get_retained_value(self) -> float:
        return sum(player.base_price for player in self.players)

    def get_overseas_count(self) -> int:
        return sum(1 for player in self.players if player.nationality != "India")

    @staticmethod
    def create_teams() -> List['Team']:
        DEFAULT_SQUAD_SIZE = 25
        DEFAULT_MAX_OVERSEAS = 8
        DEFAULT_MAX_UNCAPPED = 4
        DEFAULT_ROLES = {
            "BATTER": (6, 8),
            "BOWLER": (6, 8),
            "ALL-ROUNDER": (3, 6),
            "WICKETKEEPER": (1, 3)
        }

        teams = [
            Team(
                name="Mumbai Indians",
                purse=120 - sum(p.base_price for p in MI_RETAINED),
                players=MI_RETAINED,
                max_squad_size=DEFAULT_SQUAD_SIZE,
                max_overseas=DEFAULT_MAX_OVERSEAS,
                max_uncapped=DEFAULT_MAX_UNCAPPED,
                required_roles=DEFAULT_ROLES
            ),
            Team(
                name="Sunrisers Hyderabad",
                purse=120 - sum(p.base_price for p in SRH_RETAINED),
                players=SRH_RETAINED,
                max_squad_size=DEFAULT_SQUAD_SIZE,
                max_overseas=DEFAULT_MAX_OVERSEAS,
                max_uncapped=DEFAULT_MAX_UNCAPPED,
                required_roles=DEFAULT_ROLES
            ),
            Team(
                name="Royal Challengers Bangalore",
                purse=120 - sum(p.base_price for p in RCB_RETAINED),
                players=RCB_RETAINED,
                max_squad_size=DEFAULT_SQUAD_SIZE,
                max_overseas=DEFAULT_MAX_OVERSEAS,
                max_uncapped=DEFAULT_MAX_UNCAPPED,
                required_roles=DEFAULT_ROLES
            ),
            Team(
                name="Chennai Super Kings",
                purse=120 - sum(p.base_price for p in CSK_RETAINED),
                players=CSK_RETAINED,
                max_squad_size=DEFAULT_SQUAD_SIZE,
                max_overseas=DEFAULT_MAX_OVERSEAS,
                max_uncapped=DEFAULT_MAX_UNCAPPED,
                required_roles=DEFAULT_ROLES
            ),
            Team(
                name="Delhi Capitals",
                purse=120 - sum(p.base_price for p in DC_RETAINED),
                players=DC_RETAINED,
                max_squad_size=DEFAULT_SQUAD_SIZE,
                max_overseas=DEFAULT_MAX_OVERSEAS,
                max_uncapped=DEFAULT_MAX_UNCAPPED,
                required_roles=DEFAULT_ROLES
            ),
            Team(
                name="Gujarat Titans",
                purse=120 - sum(p.base_price for p in GT_RETAINED),
                players=GT_RETAINED,
                max_squad_size=DEFAULT_SQUAD_SIZE,
                max_overseas=DEFAULT_MAX_OVERSEAS,
                max_uncapped=DEFAULT_MAX_UNCAPPED,
                required_roles=DEFAULT_ROLES
            ),
            Team(
                name="Kolkata Knight Riders",
                purse=120 - sum(p.base_price for p in KKR_RETAINED),
                players=KKR_RETAINED,
                max_squad_size=DEFAULT_SQUAD_SIZE,
                max_overseas=DEFAULT_MAX_OVERSEAS,
                max_uncapped=DEFAULT_MAX_UNCAPPED,
                required_roles=DEFAULT_ROLES
            ),
            Team(
                name="Lucknow Super Giants",
                purse=120 - sum(p.base_price for p in LSG_RETAINED),
                players=LSG_RETAINED,
                max_squad_size=DEFAULT_SQUAD_SIZE,
                max_overseas=DEFAULT_MAX_OVERSEAS,
                max_uncapped=DEFAULT_MAX_UNCAPPED,
                required_roles=DEFAULT_ROLES
            ),
            Team(
                name="Punjab Kings",
                purse=120 - sum(p.base_price for p in PBKS_RETAINED),
                players=PBKS_RETAINED,
                max_squad_size=DEFAULT_SQUAD_SIZE,
                max_overseas=DEFAULT_MAX_OVERSEAS,
                max_uncapped=DEFAULT_MAX_UNCAPPED,
                required_roles=DEFAULT_ROLES
            ),
            Team(
                name="Rajasthan Royals",
                purse=120 - sum(p.base_price for p in RR_RETAINED),
                players=RR_RETAINED,
                max_squad_size=DEFAULT_SQUAD_SIZE,
                max_overseas=DEFAULT_MAX_OVERSEAS,
                max_uncapped=DEFAULT_MAX_UNCAPPED,
                required_roles=DEFAULT_ROLES
            )
        ]
        return teams 

    def get_player_analysis(self) -> pd.DataFrame:
        """Return a DataFrame with player analysis"""
        data = []
        for player in self.players:
            # Check if player was in retained list
            was_retained = player in self.retained_players
            
            # Get auction price if player was acquired in auction
            auction_price = None
            if not was_retained:
                for record in self.auction_history:
                    if record['player_name'] == player.name and record['status'] == 'Sold':
                        auction_price = record['final_price']
                        break
            
            data.append({
                'Name': player.name,
                'Base Price (Cr)': "Retained" if was_retained else f"₹{player.base_price:.2f}",
                'Final Price (Cr)': f"₹{player.base_price:.2f}" if was_retained else (f"₹{auction_price:.2f}" if auction_price else "Unsold"),
                'Role': player.category,
                'Nationality': player.nationality,
                'Age': player.age,
                'IPL Seasons': player.ipl_seasons,
                'Int\'l Caps': player.test_caps + player.odi_caps + player.t20_caps,
            })
        return pd.DataFrame(data)

    def calculate_capabilities(self) -> TeamCapabilities:
        """Calculate current team capabilities and restrictions"""
        capabilities = TeamCapabilities()
        
        # Calculate overseas count
        overseas_count = sum(1 for p in self.players if p.nationality != "Indian")
        capabilities.can_add_overseas = overseas_count < 8
        
        # Calculate uncapped count
        uncapped_count = sum(1 for p in self.players 
                           if p.test_caps == 0 and p.odi_caps == 0 and p.t20_caps == 0)
        capabilities.can_add_uncapped = True  # No specific limit on uncapped players
        
        # Check for wicketkeeper
        capabilities.has_keeper = any(p.category == "WICKETKEEPER" for p in self.players)
        
        # Count roles
        capabilities.role_counts = {
            role: sum(1 for p in self.players if p.category == role)
            for role in ["BATTER", "BOWLER", "ALL-ROUNDER", "WICKETKEEPER"]
        }
        
        return capabilities

@dataclass
class TeamStrategy:
    focus_domestic: float  # 0-1 preference for domestic players
    focus_youth: float    # 0-1 preference for young players
    risk_taking: float    # 0-1 willingness to spend big
    
    def adjust_bid_value(self, bid: float, player: Player) -> float:
        # Adjust bid based on team strategy
        if player.nationality == "India":
            bid *= (1 + self.focus_domestic * 0.2)
        if player.age < 25:
            bid *= (1 + self.focus_youth * 0.2)
        if self.risk_taking > 0.7:
            bid *= random.uniform(1.0, 1.3)
        return bid

class AuctionSimulator:
    def __init__(self, teams: List[Team], players: List[Player]):
        self.teams = teams
        self.players = players
        self.sold_players: Dict[str, tuple] = {}
        self.auction_history: List[Dict] = []
        
    def simulate_auction(self, progress_callback=None):
        sorted_players = sorted(
            self.players, 
            key=lambda x: (-x.base_price, -x.ipl_seasons)
        )
        
        total_players = len(sorted_players)
        
        for idx, player in enumerate(sorted_players):
            if progress_callback:
                progress_callback(idx, total_players, player.name)
                
            auction_record = {
                "player_name": player.name,
                "base_price": player.base_price,
                "category": player.category,
                "nationality": player.nationality,
                "test_caps": player.test_caps,
                "odi_caps": player.odi_caps,
                "t20_caps": player.t20_caps,
                "ipl_seasons": player.ipl_seasons,
                "timestamp": datetime.now().strftime("%H:%M:%S"),
                "bidding_history": [],
                "final_price": None,
                "winning_team": None,
                "status": "Unsold"
            }
            
            # ... rest of auction logic ...
            
            if last_bidder and current_price <= last_bidder.purse:
                if self.validate_team_composition(last_bidder):
                    last_bidder.players.append(player)
                    last_bidder.purse -= current_price
                    self.sold_players[player.name] = (last_bidder.name, current_price)
                    
                    auction_record["final_price"] = current_price
                    auction_record["winning_team"] = last_bidder.name
                    auction_record["status"] = "Sold"
                    
                    # Update the winning team's auction history
                    last_bidder.auction_history = self.auction_history
                else:
                    print(f"Skipping bid due to team composition violation")
                    continue
            
            self.auction_history.append(auction_record)

    def validate_team_composition(self, team: Team) -> bool:
        """Validate team composition meets all requirements"""
        # Print current team composition for debugging
        print(f"\nValidating {team.name} composition:")
        print(f"Total players: {len(team.players)}/{team.max_squad_size}")
        print(f"Overseas players: {team.get_overseas_count()}/{team.max_overseas}")
        
        role_counts = {
            "BATTER": sum(1 for p in team.players if p.category == "BATTER"),
            "BOWLER": sum(1 for p in team.players if p.category == "BOWLER"),
            "ALL-ROUNDER": sum(1 for p in team.players if p.category == "ALL-ROUNDER"),
            "WICKETKEEPER": sum(1 for p in team.players if p.category == "WICKETKEEPER")
        }
        
        for role, count in role_counts.items():
            min_req, max_req = team.required_roles[role]
            print(f"{role}: {count} (min: {min_req}, max: {max_req})")

        # Actual validation
        if len(team.players) > team.max_squad_size:
            print(f"❌ Squad size exceeded")
            return False
        
        if team.get_overseas_count() > team.max_overseas:
            print(f"❌ Too many overseas players")
            return False
        
        for role, (min_req, max_req) in team.required_roles.items():
            count = sum(1 for p in team.players if p.category == role)
            if count > max_req:
                print(f"❌ Too many {role}s")
                return False
            
        print("✅ Team composition valid")
        return True