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
    sql_engine = connect_to_sql_alchemy_server(server_type="prod")

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
    sql_engine = connect_to_sql_alchemy_server(server_type="prod")

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
    sql_engine = connect_to_sql_alchemy_server(server_type="prod")

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
    sql_engine = connect_to_sql_alchemy_server(server_type="prod")

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

def render_level(level, min_seasons):
    """
    Render a level of the game/quiz.
    :param level: Integer between 1 and 10 to indicate the level
    :param min_seasons: Minimum seasons for the selected level.
    :return: True/False for if player passed level or not.
    """
    # Load all players who have played the minimum number of seasons specified.
    level_players = load_players(minimum_seasons=min_seasons)
    number_level_players = len(level_players)

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
        # default=st.session_state[selection_key],
        key=f"multiselect_level_{level}"  # Unique key for each level.
    )

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
                    f"You have completed the game, congratulations! <br></h1>",
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

            st.markdown(
                f"<h1 style='color: #1C9CE0; font-size:14px;'>"
                f"That is incorrect!<br><br>"
                f"Incorrect teams: {wrong_teams}."
                f"</h1>",
                unsafe_allow_html=True
            )
            # Restart the game/quiz.
            st.write("🔄 Restarting game...")

            # Sleep for 2 seconds so users can read that their answers were wrong.
            time.sleep(2)

            # Reset all previous levels if answer wrong.
            for lvl in range(1, 11):
                # Reset the multiselects.
                st.session_state[f"level_{lvl}_selection"] = []

                # New player loaded for level 1 as game restarts.
                if lvl == 1:
                    st.session_state[f"level_{lvl}_player"] = random.choice(load_players(minimum_seasons=10))

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
        layout="wide",
        initial_sidebar_state="expanded",
        menu_items={
            'Report a bug': "mailto:contact@onetouchinsights.com",
            'About': "All data comes from Fbref European matches from 1990-2025. 2 seasons of European Cup (1990-1992), "
                     "35 seasons of Champions League (1992-Present), 20 seasons of UEFA Cup (1990-2009), 16 seasons of "
                     "Europa League (2010-Present), and 4 seasons of Europa Conference League (2021-Present)."
        }
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
            f"<h1 style='color: #1C9CE0; font-size:14px;'>"
            f"In this game, you will be given random players who have played in the Champions League.<br><br>You must name the "
            f"teams that this player has played for in the Champions League.<br><br>The game will initially select a random player "
            f"who has played at least 10 seasons in the competition. The next player will have played at least 9, then 8 "
            f"and so on down to 1.<br><br>To complete the game, you will need to get 10 correct answers in a row.<br><br>If you get an "
            f"answer wrong, you will be forced to start the game again.<br><br> Good luck!"
            f"</h1>",
            unsafe_allow_html=True
        )

    # Generate random player for each level 1-10.
    for level in range(1, 11):
        # Define minimum seasons played for each level (Level 1 = 10, Level 2 = 9, etc.)
        min_seasons = 11 - level

        # See if user passed each level.
        passed = render_level(level, min_seasons)

        # Don't load next levels if user gets the answer wrong.
        if not passed:
            break


create_streamlit_app()