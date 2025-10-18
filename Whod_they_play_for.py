#%% Imports.
import urllib
import pandas as pd
import streamlit as st
import sqlalchemy as alc
import random
import time
import base64

#%% Connect to SQL server using SQL alchemy.

def connect_to_sql_alchemy_server():
    """
    :param   server:    Name of SQL server you want to connect to.
    :param   database:  Name of database you want to connect to.
    :param   username:  Azure account username.
    :return: engine:    SQL alchemy engine connected to desired SQL server.
    """
    # Input server, database, and username.
    server = st.secrets["server"]
    database = st.secrets["database"]
    username = st.secrets["username"]
    password = st.secrets["password"]

    # Connection to server/database.
    params = urllib.parse.quote_plus('DRIVER={ODBC Driver 17 for SQL Server};'
                                     f'SERVER=tcp:{server},1433;'
                                     f'DATABASE={database};'
                                     f'UID={username};'
                                     f'PWD={password}')
    conn_string = "mssql+pyodbc:///?odbc_connect={}".format(params)

    # Foreign SQL server can't handle all rows being inserted at once, so fast_executemany is set to False.
    engine = alc.create_engine(conn_string, echo=False, pool_pre_ping=True)
    print("Now connected to server")

    return engine

#%% Function to load latest game date.

@st.cache_data(ttl=1200)
def load_latest_game_date():
    """
    :return: Date of the latest game included in the dataframe.
    """
    # Connect to SQL server.
    sql_engine = connect_to_sql_alchemy_server()

    # Select latest game date.
    query = """
                SELECT
                    MAX(game_date) AS latest_game_date
                FROM streamlit.Fbref_Appearances
                WHERE competition_name = 'Champions League'
    """

    # Convert query to date.
    latest_game_date = pd.read_sql(query, sql_engine)["latest_game_date"].iloc[0]

    return latest_game_date

#%% Function to load list of all unique players.

@st.cache_data(ttl=1200)
def load_players(minimum_seasons):
    """
    :param minimum_seasons: Minimum number of seasons that a player must have played in selected competition(s).
    :return: List of unique players names based on competition names that were selected.
    """

    # Connect to SQL server.
    sql_engine = connect_to_sql_alchemy_server()

    # SQL query for unique players.
    query = f"""
        SELECT DISTINCT 
            player_name
        FROM streamlit.Fbref_Appearances
        WHERE competition_name = 'Champions League'
            AND number_of_seasons >= {minimum_seasons}
    """

    # Create dataframe using SQL query.
    df = pd.read_sql(query, sql_engine)

    # Sort dataframe and convert to list.
    players = sorted(df["player_name"].tolist())

    return players

#%% Function to load list of all unique players.

@st.cache_data(ttl=1200)
def load_players_data(player_name):
    """
    :param   player_name:       Name of player that has been randomly selected.
    :return: teams:             List of teams player has played for.
    :return: number_of_seasons: Number of seasons player has played in.
    """

    # Connect to SQL server.
    sql_engine = connect_to_sql_alchemy_server()

    # SQL query for teams that the generated player has played for and number of seasons they've played.
    query = alc.text("""
        SELECT DISTINCT 
            team_name,
            number_of_seasons
        FROM streamlit.Fbref_Appearances
        WHERE competition_name = 'Champions League'
            AND player_name = :player
    """)

    # Create dataframe using SQL query.
    df = pd.read_sql(query, sql_engine, params={'player': player_name})

    # Sort dataframe and convert to list.
    teams = sorted(df["team_name"].tolist())

    # Extract number of seasons player has played.
    number_of_seasons = df["number_of_seasons"].mode().iat[0]

    return teams, number_of_seasons


#%% Function to load list of all unique players.

@st.cache_data(ttl=1200)
def load_unique_teams():
    """
    :return: unique_teams: List of unique teams to have played in Europe.
    """

    # Connect to SQL server.
    sql_engine = connect_to_sql_alchemy_server()

    # SQL query for all teams to have played in Europe.
    query = f"""
        SELECT DISTINCT 
            team_name
        FROM streamlit.Fbref_Appearances
    """

    # Create dataframe using SQL query.
    df = pd.read_sql(query, sql_engine)

    # Sort dataframe and convert to list.
    unique_teams = sorted(df["team_name"].tolist())

    return unique_teams


#%% Function to load each level for the game/quiz.

def render_level(level, min_seasons, starting_min_seasons):
    """
    Render a level of the game/quiz.
    :param level: Integer between 1 and 10 to indicate the level
    :param min_seasons: Minimum seasons for the selected level.
    :param starting_min_seasons: Minimum seasons for level 1. Easy mode = 17, Normal = 14, Hard = 10.
    :return: True/False for if player passed level or not.
    """
    # Load all players who have played the minimum number of seasons specified.
    level_players = load_players(minimum_seasons=min_seasons)

    # Count number of players to choose from. Players from previous levels are excluded, so the level is subtracted.
    number_level_players = len(level_players) - level if level != 1 else len(level_players)

    # Exclude players used in previous levels.
    level_players = [p for p in level_players if p not in st.session_state.values()]

    # Level title and line under title.
    st.markdown(
        f"<h4 style='color:#FF800E;'>"
        f"Level {level}: Minimum {min_seasons} seasons played. {number_level_players} players to pick from.</h2>",
        unsafe_allow_html=True
    )
    st.markdown(
        "<hr style='border: none; height: 2px; background-color: #FF800E;'>",
        unsafe_allow_html=True
    )

    # Keys to distinguish between each level when they are run consecutively.
    player_key = f"level_{level}_player"
    selection_key = f"level_{level}_selection"

    # Make sure that the randomly selected player does not get refreshed when answers are inputted.
    if player_key not in st.session_state:
        # Randomly generate a player who has played at least min_seasons in the CL.
        st.session_state[player_key] = random.choice(level_players)

    # Initialise the selection as empty.
    if selection_key not in st.session_state:
        st.session_state[selection_key] = []

    # Define the randomly generated player and their teams and number of seasons.
    level_player = st.session_state[player_key]
    level_answers, number_of_seasons = load_players_data(player_name=level_player)

    # Display the randomly generated player to the user.
    st.markdown(
        f"<h1 style='color: #1C9CE0; font-size:14px;'>"
        f"Your player is {level_player}, who has played {number_of_seasons} season(s) in the Champions League."
        f"</h1>",
        unsafe_allow_html=True
    )

    # Display to the user, how many teams the player has played for in the CL.
    # If player has only played for one team, print team instead of teams.
    if len(level_answers) == 1:
        st.markdown(
            f"<h1 style='color: #1C9CE0; font-size:14px;'>"
            f"He has played for 1 team in the Champions League. Who is this team?"
            f"</h1>",
            unsafe_allow_html=True
        )
    else:
        st.markdown(
            f"<h1 style='color: #1C9CE0; font-size:14px;'>"
            f"He has played for {len(level_answers)} teams in the Champions League. Who are these teams?"
            f"</h1>",
            unsafe_allow_html=True
        )

    # Selection for user for the teams the player has played for.
    st.session_state[selection_key] = st.multiselect(
        f"Please select {len(level_answers)} teams:",
        options=load_unique_teams(),
        key=f"multiselect_level_{level}"  # Unique key for each level.
    )

    # Allow users to reveal 1 team if they're stuck.
    if st.session_state["remaining_reveals"] > 0:
        if st.button(f"Reveal 1 Team ({st.session_state['remaining_reveals']} left)", key=f"reveal_button_{level}"):
            # Randomly select one correct team.
            revealed_team = random.choice(level_answers)
            st.session_state[selection_key].append(revealed_team)

            # Subtract 1 reveal from the allowed number of reveals.
            st.session_state["remaining_reveals"] -= 1
            st.success(f"🎁 Revealed one team: {revealed_team}")
            st.rerun()
    else:
        st.markdown("<p style='color: #1C9CE0; font-size:14px;'>No reveals remaining.</p>", unsafe_allow_html=True)

    # When all teams are selected, see if the answers from the user are correct.
    if len(st.session_state[selection_key]) == len(level_answers):
        # If user's answers are correct:
        if set(st.session_state[selection_key]) == set(level_answers):
            st.markdown(
                f"<h1 style='color: #1C9CE0; font-size:14px;'>"
                f"That is correct!<br></h1>",
                unsafe_allow_html=True
            )

            # Print congratulatory message if user finishes the entire game.
            if level == 10:
                st.markdown(
                    f"<h1 style='color: #1C9CE0; font-size:14px;'>"
                    f"You have completed the game, congratulations! 🥳 🎉<br><br>"
                    f"Please feel free to try a new difficulty level 😊.</h1>",
                    unsafe_allow_html=True
                )

                # Reset button if user wants to restart game after completing it.
                if st.button("🔄 Play Again"):
                    # Reset all session states.
                    for key in list(st.session_state.keys()):
                        del st.session_state[key]

                    # Refresh UI.
                    st.rerun()

            return True

        # If user's answers are incorrect:
        else:
            # Extract which teams the user got wrong.
            wrong_answers = set(st.session_state[selection_key]) - set(level_answers)
            wrong_teams = ", ".join(team for team in wrong_answers)

            # Extract how many answers the user got correct.
            correct_answers = set(st.session_state[selection_key]) & set(level_answers)

            st.markdown(
                f"<h1 style='color: #1C9CE0; font-size:14px;'>"
                f"Unlucky, that is incorrect. You got {len(correct_answers)} out of {len(level_answers)} team(s) correct.<br><br>"
                f"Incorrect team(s): {wrong_teams}."
                f"</h1>",
                unsafe_allow_html=True
            )
            # Restart the game/quiz.
            st.write("🔄 Restarting game...")

            # Sleep for 3 seconds so users can read that their answers were wrong.
            time.sleep(3)

            # Reset all previous levels if answer wrong.
            for lvl in range(1, 11):
                # Reset the stored selections.
                if f"level_{lvl}_selection" in st.session_state:
                    del st.session_state[f"level_{lvl}_selection"]

                # Reset the widget state as well.
                if f"multiselect_level_{lvl}" in st.session_state:
                    del st.session_state[f"multiselect_level_{lvl}"]

                # New player loaded for level 1 as game restarts.
                if lvl == 1:
                    st.session_state[f"level_{lvl}_player"] = random.choice(load_players(minimum_seasons=starting_min_seasons))

                # Delete player from all other levels so they can be generated again if user makes it that far.
                else:
                    if f"level_{lvl}_player" in st.session_state:
                        del st.session_state[f"level_{lvl}_player"]

            # Force rerun so UI updates immediately.
            st.rerun()

    return False


#%% Build Streamlit app.

def create_streamlit_app():
    """
    :return:
    """
    # Set up page configuration.
    st.set_page_config(
        page_title="Who'd they play for?",
        page_icon="Logo_Youtube.png",
        layout="centered",
        initial_sidebar_state="expanded",
        menu_items={
            'Report a bug': "mailto:contact@onetouchinsights.com",
            'About': "All data comes from Fbref Champions League games 1992-Present (Latest game date in the top left). "
                     "A player is considered to have played a season if they made a minimum of 1 appearance during that season "
                     "(excluding qualifiers). "
                     "Players who have had another player with the same name (E.g. Marcelo- Left back for Real Madrid/Centre back "
                     "for Lyon & Besiktas) also play in a European Competition will have extra info given including their nationality, "
                     "seasons played and Fbref id. You can Google this id to see exactly who the player is."
        }
    )

    # Responsive meta viewport tag. Used to automatically resize the app depending on if the user is on mobile or desktop.
    st.markdown(
        """
        <meta name="viewport" content="width=device-width, initial-scale=1, maximum-scale=1">
        """,
        unsafe_allow_html=True
    )

    # OneTouch logo with link to website.
    st.markdown(
        f"""
        <a href="https://onetouchinsights.com/" target="_blank" rel="noopener noreferrer">
            <img src="data:image/png;base64,
            {base64.b64encode(open("Logo.png", "rb").read()).decode()}"
            alt="OneTouchInsights"
            style="width:200px; height:60px;"/>
        </a>
        """,
        unsafe_allow_html=True
    )

    # Define the positions for the page's headers
    header1, header2 = st.columns([3, 1])

    # Header 1: Displays the date that the last game comes from.
    with header1:
        st.markdown(
            f"<h1 style='color: #FF800E; font-size:14px;'>"
            f"Latest game date: {load_latest_game_date().strftime('%B %d, %Y')}"
            f"</h1>",
            unsafe_allow_html=True
        )

    # Header 2: Link to LinkedIn page.
    with header2:
        st.markdown(
            "<a href='https://www.linkedin.com/in/conor-mc/' target='_blank' style='color: #FF800E;float: right; text-decoration: none; font-size:14px;'>"
            "Conor McCarthy"
            "</a>",
            unsafe_allow_html=True
        )

    # Set title.
    st.markdown(
        "<h1 style='text-align: center; color: #FF800E;'>"
        "⚽ Who'd they play for? ⚽</h1>",
        unsafe_allow_html=True
    )

    # Button to allow user to check for updated data and clear the cache data.
    if st.button("🔄 Check for updates."):
        st.cache_data.clear()
        st.cache_resource.clear()
        st.rerun()

    # Title.
    st.markdown(
        f"<h1 style='color: #FF800E; font-size:14px;'>"
        f"Game description: "
        f"</h1>",
        unsafe_allow_html=True
    )

    # Wrap quiz description in a box.
    with st.container(border=True):

        # Quiz description.
        st.markdown(
            "<h1 style='color: #1C9CE0; font-size:14px;'>"
            "In this game, you will be given random players who have played in the Champions League.<br><br>"
            "You must name the teams that this player has played for in the Champions League.<br><br>"
            "Each difficulty level contains 10 levels.<br><br>"
            "For the 'Easy' difficulty, the first level will be a random player that played at least 17 seasons in the "
                "competition, then the next level will be minimum 16 seasons, and so on down to 8 seasons.<br><br>"
            "For the 'Normal' difficulty, the first level has minimum 14 seasons and the final level minimum 5 seasons.<br><br>"
            "For the 'Hard' difficulty, the first level has minimum 10 seasons and the final level minimum 1 season.<br><br>"
            "To complete the game, you will need to get 10 correct answers in a row.<br><br>"
            "If you get an answer wrong, you will be forced to start the game again.<br><br>"
            "Good luck!"
            "</h1>",
            unsafe_allow_html=True
        )

    # Dictionary for storing the starting minimum number of seasons for each difficulty.
    game_difficulty = {
        "Select a difficulty level" : 0,
        "Easy" : 17,
        "Normal" : 14,
        "Hard" : 10
    }

    # Game difficulty selector for user.
    difficulty_selection = st.selectbox(
        label="Please select a difficulty level:",
        options=list(game_difficulty.keys())
    )

    # Define allowed team reveals per difficulty.
    reveals_per_difficulty = {
        "Easy": 3,
        "Normal": 2,
        "Hard": 1
    }

    # Initialize remaining reveal count if not set or difficulty changed.
    if ("remaining_reveals" not in st.session_state
    or "previous_difficulty" not in st.session_state
    or st.session_state["previous_difficulty"] != difficulty_selection):
        st.session_state["remaining_reveals"] = reveals_per_difficulty.get(difficulty_selection, 0)
        st.session_state["previous_difficulty"] = difficulty_selection

    # Start game based on the game difficulty selected.
    if difficulty_selection != "Select a difficulty level":
        # Track previous difficulty to see if the user has selected a new difficulty.
        if "current_difficulty" not in st.session_state:
            st.session_state["current_difficulty"] = difficulty_selection

        # If the user changes the difficulty, reset all the levels.
        if st.session_state["current_difficulty"] != difficulty_selection:
            for lvl in range(1, 11):
                # Remove player selections and multiselect widgets.
                st.session_state.pop(f"level_{lvl}_selection", None)
                st.session_state.pop(f"multiselect_level_{lvl}", None)

                # Remove the stored player for each level.
                st.session_state.pop(f"level_{lvl}_player", None)

            # Update difficulty to newly selected.
            st.session_state["current_difficulty"] = difficulty_selection

            # Refresh UI.
            st.rerun()

        # Generate random player for each level 1-10.
        for level in range(1, 11):
            # Define minimum seasons played for each level.
            min_seasons = game_difficulty[difficulty_selection] + 1 - level

            # See if user passed each level.
            passed = render_level(level, min_seasons, game_difficulty[difficulty_selection])

            # Don't load next levels if user gets the answer wrong.
            if not passed:
                break

    else:
        st.error("Please select a difficulty level.")


create_streamlit_app()