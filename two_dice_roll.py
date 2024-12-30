from typing import Dict, List, Optional, TypedDict, Literal
import streamlit as st
import random
import time
import pandas as pd
import altair as alt

# =============================================================================
# 1) Configuration and Types
# =============================================================================


class GameStateDict(TypedDict):
    """Type definition for the dictionary representation of GameState."""

    players: List[str]
    distribution: str
    rolls_by_player: Dict[str, List[int]]
    sum_counts: Dict[str, int]
    current_player_index: int


class GameState:
    """
    Represents the current state of the dice rolling game.

    Attributes:
        players (List[str]): List of player names
        distribution (Literal["Real", "Uniform"]): Type of dice roll distribution
        rolls_by_player (Dict[str, List[int]]): Dictionary mapping player names to their roll history
        sum_counts (Dict[int, int]): Dictionary tracking frequency of each possible roll sum
        current_player_index (int): Index of the current player in the players list
    """

    def __init__(
        self, players: List[str], distribution: Literal["Real", "Uniform"]
    ) -> None:
        self.players = players
        self.distribution = distribution
        self.rolls_by_player: Dict[str, List[int]] = {n: [] for n in players}
        self.sum_counts: Dict[int, int] = {s: 0 for s in range(2, 13)}
        self.current_player_index: int = 0

    @classmethod
    def from_dict(cls, data: GameStateDict) -> "GameState":
        """
        Create a GameState instance from a dictionary representation.

        Args:
            data (GameStateDict): Dictionary containing game state data

        Returns:
            GameState: New GameState instance initialized with the provided data
        """
        game = cls(data["players"], data["distribution"])
        game.rolls_by_player = data["rolls_by_player"]
        game.sum_counts = {int(k): v for k, v in data["sum_counts"].items()}
        game.current_player_index = data["current_player_index"]
        return game

    def to_dict(self) -> GameStateDict:
        """
        Convert the GameState instance to a dictionary representation.

        Returns:
            GameStateDict: Dictionary containing all game state data
        """
        return {
            "players": self.players,
            "distribution": self.distribution,
            "rolls_by_player": self.rolls_by_player,
            "sum_counts": self.sum_counts,
            "current_player_index": self.current_player_index,
        }


# =============================================================================
# 2) Setup and Configuration
# =============================================================================


def init_streamlit() -> None:
    """
    Initialize Streamlit application settings and session state variables.
    Sets up the page configuration and initializes required session state variables
    if they don't exist.
    """
    st.set_page_config(
        page_title="Two Dice Roll",
        page_icon="🎲",
        layout="centered",
    )

    if "game_state" not in st.session_state:
        st.session_state.game_state: Optional[GameState] = None
    if "page" not in st.session_state:
        st.session_state.page: Literal["setup", "game"] = "setup"


def apply_custom_styles() -> None:
    """
    Apply custom CSS styles to the Streamlit application.
    Injects custom CSS to modify the appearance of various UI components.
    """
    st.markdown(
        """
        <style>
        body {
            background: linear-gradient(to top right, #fcf3d1, #FFFFFF);
        }
        .stMarkdown h1, .stMarkdown h2, .stMarkdown h3 {
            color: #4531cc !important;
            font-weight: 600 !important;
        }
        div.stButton > button:first-child {
            background-color: #4531cc !important;
            color: white !important;
            border-radius: 8px;
            padding: 0.6em 1em;
            border: none;
            font-size: 1rem;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
            transition: all 0.3s ease;
        }
        div.stButton > button:hover {
            background-color: #F05240 !important;
            transform: translateY(-2px);
        }
        .stAlert {
            background-color: #fcf3d1 !important;
            border-left: 4px solid #4531cc !important;
        }
        .dataframe th {
            background-color: #fcf3d1 !important;
            color: #4531cc !important;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


# =============================================================================
# 3) Game Logic
# =============================================================================


def roll_dice(distribution: Literal["Real", "Uniform"]) -> int:
    """
    Generate a dice roll based on the selected distribution.

    Args:
        distribution (Literal["Real", "Uniform"]): Type of probability distribution to use
            - "Real": Simulates rolling two six-sided dice (2d6)
            - "Uniform": Equal probability for all possible sums (2-12)

    Returns:
        int: Sum of the dice roll
    """
    if distribution == "Uniform":
        return random.randint(2, 12)
    return random.randint(1, 6) + random.randint(1, 6)


def build_rolls_df(game_state: GameState) -> pd.DataFrame:
    """
    Create a DataFrame containing all players' rolls in chronological order.

    Args:
        game_state (GameState): Current game state containing roll history

    Returns:
        pd.DataFrame: DataFrame with players as columns and rolls as rows,
                     where empty slots are filled with None
    """
    if not any(game_state.rolls_by_player.values()):
        return pd.DataFrame()

    chronological_data: Dict[str, List[Optional[int]]] = {
        player: [] for player in game_state.players
    }
    total_rounds = max(len(rolls) for rolls in game_state.rolls_by_player.values())

    for player in game_state.players:
        player_rolls = game_state.rolls_by_player[player]
        chronological_data[player] = player_rolls + [None] * (
            total_rounds - len(player_rolls)
        )

    df = pd.DataFrame(chronological_data)
    df.index = [f"Roll {i+1}" for i in range(total_rounds)]

    return df


def create_histogram(game_state: GameState) -> alt.Chart:
    """
    Create an Altair histogram visualization of dice roll frequencies.

    Args:
        game_state (GameState): Current game state containing roll counts

    Returns:
        alt.Chart: Altair chart object representing the histogram
    """
    df_counts = pd.DataFrame(
        {
            "Sum": list(game_state.sum_counts.keys()),
            "Count": list(game_state.sum_counts.values()),
        }
    )
    return (
        alt.Chart(df_counts)
        .mark_bar(color="#4531cc")
        .encode(
            x=alt.X("Sum:O", title="Dice Sum"),
            y=alt.Y("Count:Q", title="Frequency"),
            tooltip=["Sum", "Count"],
        )
        .properties(width=600, height=300)
        .configure_axis(labelFontSize=12, titleFontSize=14)
    )


# =============================================================================
# 4) UI Screens
# =============================================================================


def setup_screen() -> None:
    """
    Render the game setup screen.
    Allows users to configure number of players, player names, and dice distribution.
    Updates session state and transitions to game screen when setup is complete.
    """
    st.title("🎲 Two Dice Roll Setup")

    col1, col2 = st.columns([2, 1])

    with col1:
        num_players: int = st.number_input(
            "Number of players:",
            min_value=1,
            max_value=6,
            value=2,
            step=1,
        )

        names: List[str] = []
        for i in range(num_players):
            default_name = f"Player {i+1}"
            name = st.text_input(
                f"Player {i+1} name:", value=default_name, key=f"player_{i}"
            ).strip()
            names.append(name if name else default_name)

    with col2:
        distribution: Literal["Real", "Uniform"] = st.radio(
            "Select dice distribution:",
            ["Real", "Uniform"],
            help="Real = Two dice (2d6), Uniform = Equal chance for all numbers",
        )

        if st.button("Start Game", use_container_width=True):
            if len(set(names)) != len(names):
                st.error("Each player must have a unique name!")
                return

            st.session_state.game_state = GameState(names, distribution)
            st.session_state.page = "game"
            st.rerun()


def game_screen() -> None:
    """
    Render the main game screen.
    Displays current player, roll button, roll history, and distribution visualization.
    Handles dice rolling and updates game state accordingly.
    """
    game_state: Optional[GameState] = st.session_state.game_state
    if not game_state:
        st.error("Game state not found!")
        if st.button("Return to Setup"):
            st.session_state.page = "setup"
            st.rerun()
        return

    st.title("🎲 Two Dice Roll")
    st.info(f"Distribution: {game_state.distribution}")

    current_player = game_state.players[game_state.current_player_index]
    st.markdown(f"### Current Turn: {current_player}")

    if st.button("Roll Dice!", use_container_width=True):
        with st.spinner("Rolling..."):
            time.sleep(0.5)
            roll_sum = roll_dice(game_state.distribution)
            game_state.rolls_by_player[current_player].append(roll_sum)
            game_state.sum_counts[roll_sum] += 1
            game_state.current_player_index = (
                game_state.current_player_index + 1
            ) % len(game_state.players)
            st.markdown(f"### 🎲 {current_player} rolled a {roll_sum}")

    total_rolls: int = sum(len(rolls) for rolls in game_state.rolls_by_player.values())

    st.subheader("Distribution of Rolls")
    if total_rolls > 0:
        st.altair_chart(create_histogram(game_state), use_container_width=True)
    else:
        st.info("Roll some dice to see the distribution!")

    col1, col2 = st.columns([2, 1])

    with col1:
        st.subheader("Roll History")
        rolls_df = build_rolls_df(game_state)
        if not rolls_df.empty:
            st.dataframe(rolls_df, use_container_width=True)
        else:
            st.info("No rolls yet. Click 'Roll Dice!' to begin!")

    with col2:
        st.metric("Total Rolls", total_rolls)

    st.write("---")
    if st.button("Reset Game"):
        st.session_state.game_state = None
        st.session_state.page = "setup"
        st.rerun()


# =============================================================================
# 5) Main Application
# =============================================================================


def main() -> None:
    """
    Main application entry point.
    Initializes the application and handles routing between screens.
    """
    init_streamlit()
    apply_custom_styles()

    if st.session_state.page == "setup":
        setup_screen()
    else:
        game_screen()


if __name__ == "__main__":
    main()
