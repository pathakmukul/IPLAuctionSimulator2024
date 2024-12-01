from dataclasses import dataclass
from typing import List, Optional
import pandas as pd

@dataclass
class Player:
    name: str
    base_price: float  # in crores
    category: str
    nationality: str
    age: int
    test_caps: int = 0
    odi_caps: int = 0
    t20_caps: int = 0
    ipl_seasons: int = 0
    previous_ipl_teams: Optional[str] = None
    current_ipl_team: Optional[str] = None
    current_ipl_status: Optional[str] = None
    specialization: str = ""
    set_2025: Optional[str] = None


def load_auction_players() -> List[Player]:
    """Load players from CSV file and convert to Player objects"""
    df = pd.read_csv('/Users/mukulpathak/Documents/VSCodeZone/chotu/IPL_Auction/IPL_Auction.csv')
    
    auction_players = []
    retained_players_by_team = {
        'MI': [], 'KKR': [], 'CSK': [], 'RR': [], 'RCB': [], 
        'DC': [], 'GT': [], 'LSG': [], 'PBKS': [], 'SRH': []
    }
    
    for _, row in df.iterrows():
        # Convert lakhs to crores for base_price
        base_price_cr = row['Price_rs_lakhs'] / 100
        
        # Handle missing values for caps
        test_caps = row['Test_caps'] if pd.notna(row['Test_caps']) else 0
        odi_caps = row['ODI_caps'] if pd.notna(row['ODI_caps']) else 0
        t20_caps = row['T20_caps'] if pd.notna(row['T20_caps']) else 0
        
        # Handle IPL related data
        ipl_seasons = row['IPL'] if pd.notna(row['IPL']) else 0
        prev_teams = row['Previous_IPL_Teams'] if pd.notna(row['Previous_IPL_Teams']) else None
        current_team = row['2024_Team'] if pd.notna(row['2024_Team']) else None
        current_status = row['2024_IPL'] if pd.notna(row['2024_IPL']) else None
        
        player = Player(
            name=f"{row['First_Name']} {row['Surname']}",
            base_price=base_price_cr,
            category=row['Specialism'],
            nationality=row['Country'],
            age=row['Age'],
            test_caps=int(test_caps),
            odi_caps=int(odi_caps),
            t20_caps=int(t20_caps),
            ipl_seasons=int(ipl_seasons),
            previous_ipl_teams=prev_teams,
            current_ipl_team=current_team,
            current_ipl_status=current_status,
            specialization=row['Specialism'],
            set_2025=row['2025_Set'] if pd.notna(row['2025_Set']) else None
        )
        
        # If player is retained, add to respective team's retained list
        if row['Sold_status'] == 'Retained' and row['2025_Team'] in retained_players_by_team:
            retained_players_by_team[row['2025_Team']].append(player)
        # If player is not retained, add to auction pool
        elif pd.isna(row['Sold_status']):
            auction_players.append(player)
    
    # Create global variables for retained players
    global MI_RETAINED, KKR_RETAINED, CSK_RETAINED, RR_RETAINED, RCB_RETAINED
    global DC_RETAINED, GT_RETAINED, LSG_RETAINED, PBKS_RETAINED, SRH_RETAINED
    
    MI_RETAINED = retained_players_by_team['MI']
    KKR_RETAINED = retained_players_by_team['KKR']
    CSK_RETAINED = retained_players_by_team['CSK']
    RR_RETAINED = retained_players_by_team['RR']
    RCB_RETAINED = retained_players_by_team['RCB']
    DC_RETAINED = retained_players_by_team['DC']
    GT_RETAINED = retained_players_by_team['GT']
    LSG_RETAINED = retained_players_by_team['LSG']
    PBKS_RETAINED = retained_players_by_team['PBKS']
    SRH_RETAINED = retained_players_by_team['SRH']
    
    return auction_players

# Initialize the retained lists and auction pool
AUCTION_POOL = load_auction_players()

# Remove the hardcoded retained player lists since they're now populated by the CSV

# Make sure to export all the names in __all__
__all__ = [
    'Player',
    'MI_RETAINED',
    'KKR_RETAINED', 
    'CSK_RETAINED',
    'RR_RETAINED',
    'RCB_RETAINED',
    'DC_RETAINED',
    'GT_RETAINED',
    'LSG_RETAINED',
    'PBKS_RETAINED',
    'SRH_RETAINED',
    'AUCTION_POOL',
    'load_auction_players'
] 