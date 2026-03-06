import streamlit as st
import pandas as pd
import os

# ── Configuración ──────────────────────────────────────────────
st.set_page_config(page_title="Athletic Club · CSV Explorer", layout="wide", page_icon="⚽")

DATA_DIR = os.path.join(os.path.dirname(__file__), "csv_export")

# ── Carga de datos ─────────────────────────────────────────────
@st.cache_data
def load_csv(name):
    path = os.path.join(DATA_DIR, name)
    return pd.read_csv(path)

@st.cache_data
def load_all():
    teams = load_csv("Team.csv")
    players = load_csv("Player.csv")
    matches = load_csv("Match.csv")
    goals = load_csv("Goal.csv")
    cards = load_csv("Card.csv")
    lineups = load_csv("Lineup.csv")
    subs = load_csv("Substitution.csv")
    stadiums = load_csv("Stadium.csv")
    referees = load_csv("Referee.csv")
    coaching = load_csv("CoachingStaff.csv")
    competition = load_csv("Competition_Season.csv")
    return teams, players, matches, goals, cards, lineups, subs, stadiums, referees, coaching, competition

teams, players, matches, goals, cards, lineups, subs, stadiums, referees, coaching, competition = load_all()

# Diccionarios auxiliares
team_map = dict(zip(teams["team_id"], teams["team_name"]))
player_map = dict(zip(players["player_id"], players["player_name"]))
stadium_map = dict(zip(stadiums["stadium_id"], stadiums["name"]))
referee_map = dict(zip(referees["referee_id"], referees["name"]))

def team_name(tid):
    return team_map.get(tid, str(tid))

def player_name(pid):
    return player_map.get(pid, str(pid))

# ── Sidebar ────────────────────────────────────────────────────
st.sidebar.title("⚽ Athletic Club")
st.sidebar.caption("CSV Explorer")

page = st.sidebar.radio(
    "Sección",
    ["🏠 Inicio", "📅 Partidos", "⚽ Goles", "🟨 Tarjetas", "👥 Plantillas", "🔄 Sustituciones", "📊 Explorador CSV"],
)

# ── Página: Inicio ─────────────────────────────────────────────
if page == "🏠 Inicio":
    st.title("Athletic Club · Datos de Competición")

    if not competition.empty:
        comp = competition.iloc[0]
        st.markdown(f"**Competición:** {comp.get('competition_name', '–')}  ·  **Temporada:** {comp.get('season_name', '–')}")

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Equipos", len(teams))
    col2.metric("Partidos", len(matches))
    col3.metric("Jugadores", len(players))
    col4.metric("Goles", len(goals))

    st.subheader("Clasificación (puntos estimados)")
    # Calcular clasificación básica
    rows = []
    for _, m in matches.iterrows():
        hs, aws = m["home_score"], m["away_score"]
        ht, at = m["home_team_id"], m["away_team_id"]
        if hs > aws:
            rows.append({"team_id": ht, "pts": 3, "gf": hs, "gc": aws, "w": 1, "d": 0, "l": 0})
            rows.append({"team_id": at, "pts": 0, "gf": aws, "gc": hs, "w": 0, "d": 0, "l": 1})
        elif hs < aws:
            rows.append({"team_id": ht, "pts": 0, "gf": hs, "gc": aws, "w": 0, "d": 0, "l": 1})
            rows.append({"team_id": at, "pts": 3, "gf": aws, "gc": hs, "w": 1, "d": 0, "l": 0})
        else:
            rows.append({"team_id": ht, "pts": 1, "gf": hs, "gc": aws, "w": 0, "d": 1, "l": 0})
            rows.append({"team_id": at, "pts": 1, "gf": aws, "gc": hs, "w": 0, "d": 1, "l": 0})

    if rows:
        tabla = pd.DataFrame(rows)
        tabla = tabla.groupby("team_id").agg(
            PTS=("pts", "sum"), PJ=("pts", "count"),
            PG=("w", "sum"), PE=("d", "sum"), PP=("l", "sum"),
            GF=("gf", "sum"), GC=("gc", "sum"),
        ).reset_index()
        tabla["DG"] = tabla["GF"] - tabla["GC"]
        tabla["Equipo"] = tabla["team_id"].map(team_name)
        tabla = tabla.sort_values(["PTS", "DG", "GF"], ascending=False).reset_index(drop=True)
        tabla.index = tabla.index + 1
        st.dataframe(
            tabla[["Equipo", "PJ", "PG", "PE", "PP", "GF", "GC", "DG", "PTS"]],
            use_container_width=True,
            hide_index=False,
        )

# ── Página: Partidos ───────────────────────────────────────────
elif page == "📅 Partidos":
    st.title("📅 Partidos")

    # Filtros
    col_f1, col_f2 = st.columns(2)
    jornadas = sorted(matches["match_week"].dropna().unique())
    sel_jornada = col_f1.selectbox("Jornada", ["Todas"] + [int(j) for j in jornadas])
    sel_equipo = col_f2.selectbox("Equipo", ["Todos"] + sorted(team_map.values()))

    df = matches.copy()
    if sel_jornada != "Todas":
        df = df[df["match_week"] == sel_jornada]
    if sel_equipo != "Todos":
        tid = [k for k, v in team_map.items() if v == sel_equipo]
        if tid:
            df = df[(df["home_team_id"].isin(tid)) | (df["away_team_id"].isin(tid))]

    df["Local"] = df["home_team_id"].map(team_name)
    df["Visitante"] = df["away_team_id"].map(team_name)
    df["Resultado"] = df["home_score"].astype(str) + " - " + df["away_score"].astype(str)
    df["Estadio"] = df["stadium_id"].map(lambda x: stadium_map.get(x, "–"))
    df["Árbitro"] = df["referee_id"].map(lambda x: referee_map.get(x, "–"))
    df["Fecha"] = df["match_date"]
    df["Jornada"] = df["match_week"]

    st.dataframe(
        df[["Jornada", "Fecha", "Local", "Resultado", "Visitante", "Estadio", "Árbitro"]].sort_values(["Jornada", "Fecha"]),
        use_container_width=True,
        hide_index=True,
    )

    # Detalle de un partido
    st.subheader("Detalle de partido")
    match_options = {
        f"J{int(r.match_week)} · {team_name(r.home_team_id)} {int(r.home_score)}-{int(r.away_score)} {team_name(r.away_team_id)} ({r.match_date})": r.match_id
        for _, r in matches.iterrows()
    }
    sel_match = st.selectbox("Selecciona un partido", list(match_options.keys()))
    mid = match_options[sel_match]

    m_goals = goals[goals["match_id"] == mid].copy()
    m_cards = cards[cards["match_id"] == mid].copy()
    m_lineup = lineups[lineups["match_id"] == mid].copy()
    m_subs = subs[subs["match_id"] == mid].copy()

    c1, c2 = st.columns(2)
    with c1:
        st.markdown("**⚽ Goles**")
        if m_goals.empty:
            st.info("Sin goles registrados")
        else:
            m_goals["Jugador"] = m_goals["scorer_player_id"].map(player_name)
            m_goals["Equipo"] = m_goals["scoring_team_id"].map(team_name)
            st.dataframe(m_goals[["minute", "Jugador", "Equipo", "goal_type", "score_home_after", "score_away_after"]], hide_index=True)

    with c2:
        st.markdown("**🟨 Tarjetas**")
        if m_cards.empty:
            st.info("Sin tarjetas")
        else:
            m_cards["Jugador"] = m_cards["player_id"].map(player_name)
            m_cards["Equipo"] = m_cards["team_id"].map(team_name)
            st.dataframe(m_cards[["minute", "Jugador", "Equipo", "card_type"]], hide_index=True)

    # Alineaciones
    m_info = matches[matches["match_id"] == mid].iloc[0]
    home_id, away_id = m_info["home_team_id"], m_info["away_team_id"]

    c3, c4 = st.columns(2)
    with c3:
        st.markdown(f"**🏠 {team_name(home_id)}**")
        home_lineup = m_lineup[m_lineup["team_id"] == home_id].copy()
        home_lineup["Jugador"] = home_lineup["player_id"].map(player_name)
        home_lineup["Titular"] = home_lineup["is_starter"].map({1: "✅", 0: "🔄"})
        st.dataframe(home_lineup[["jersey_number", "Jugador", "Titular"]].sort_values(["Titular", "jersey_number"], ascending=[False, True]), hide_index=True)

    with c4:
        st.markdown(f"**✈️ {team_name(away_id)}**")
        away_lineup = m_lineup[m_lineup["team_id"] == away_id].copy()
        away_lineup["Jugador"] = away_lineup["player_id"].map(player_name)
        away_lineup["Titular"] = away_lineup["is_starter"].map({1: "✅", 0: "🔄"})
        st.dataframe(away_lineup[["jersey_number", "Jugador", "Titular"]].sort_values(["Titular", "jersey_number"], ascending=[False, True]), hide_index=True)

    if not m_subs.empty:
        st.markdown("**🔄 Sustituciones**")
        m_subs["Sale"] = m_subs["player_out_id"].map(player_name)
        m_subs["Entra"] = m_subs["player_in_id"].map(player_name)
        m_subs["Equipo"] = m_subs["team_id"].map(team_name)
        st.dataframe(m_subs[["minute", "Equipo", "Sale", "Entra"]].sort_values("minute"), hide_index=True)

# ── Página: Goles ──────────────────────────────────────────────
elif page == "⚽ Goles":
    st.title("⚽ Goles")

    df = goals.copy()
    df["Goleador"] = df["scorer_player_id"].map(player_name)
    df["Equipo"] = df["scoring_team_id"].map(team_name)

    # Ranking goleadores
    st.subheader("🏆 Ranking de goleadores")
    ranking = df.groupby(["scorer_player_id"]).agg(
        Goles=("goal_id", "count"),
    ).reset_index()
    ranking["Jugador"] = ranking["scorer_player_id"].map(player_name)
    ranking = ranking.sort_values("Goles", ascending=False).reset_index(drop=True)
    ranking.index = ranking.index + 1
    st.dataframe(ranking[["Jugador", "Goles"]], use_container_width=True)

    st.subheader("Todos los goles")
    # Añadir info del partido
    df = df.merge(matches[["match_id", "match_date", "match_week", "home_team_id", "away_team_id", "home_score", "away_score"]], on="match_id", how="left")
    df["Partido"] = df.apply(lambda r: f"{team_name(r.home_team_id)} {int(r.home_score)}-{int(r.away_score)} {team_name(r.away_team_id)}", axis=1)
    st.dataframe(
        df[["match_date", "match_week", "Partido", "minute", "Goleador", "Equipo", "goal_type"]].sort_values(["match_date", "minute"]),
        use_container_width=True, hide_index=True,
    )

# ── Página: Tarjetas ───────────────────────────────────────────
elif page == "🟨 Tarjetas":
    st.title("🟨 Tarjetas")
    df = cards.copy()
    df["Jugador"] = df["player_id"].map(player_name)
    df["Equipo"] = df["team_id"].map(team_name)

    col1, col2 = st.columns(2)
    with col1:
        st.subheader("Amarillas por jugador")
        amarillas = df[df["card_type"] == "yellow"].groupby("player_id").size().reset_index(name="Amarillas")
        amarillas["Jugador"] = amarillas["player_id"].map(player_name)
        amarillas = amarillas.sort_values("Amarillas", ascending=False).reset_index(drop=True)
        amarillas.index += 1
        st.dataframe(amarillas[["Jugador", "Amarillas"]], use_container_width=True)

    with col2:
        st.subheader("Rojas por jugador")
        rojas = df[df["card_type"].isin(["red", "second_yellow"])].groupby("player_id").size().reset_index(name="Rojas")
        if rojas.empty:
            st.info("Sin rojas esta temporada")
        else:
            rojas["Jugador"] = rojas["player_id"].map(player_name)
            rojas = rojas.sort_values("Rojas", ascending=False).reset_index(drop=True)
            rojas.index += 1
            st.dataframe(rojas[["Jugador", "Rojas"]], use_container_width=True)

    st.subheader("Todas las tarjetas")
    df = df.merge(matches[["match_id", "match_date", "match_week"]], on="match_id", how="left")
    st.dataframe(
        df[["match_date", "match_week", "minute", "Jugador", "Equipo", "card_type"]].sort_values(["match_date", "minute"]),
        use_container_width=True, hide_index=True,
    )

# ── Página: Plantillas ────────────────────────────────────────
elif page == "👥 Plantillas":
    st.title("👥 Plantillas")
    sel = st.selectbox("Equipo", sorted(team_map.values()))
    tid = [k for k, v in team_map.items() if v == sel][0]

    # Jugadores del equipo (aparecen en lineups)
    equipo_lineup = lineups[lineups["team_id"] == tid].copy()
    jugadores_ids = equipo_lineup["player_id"].unique()
    equipo_players = equipo_lineup.drop_duplicates("player_id")
    equipo_players["Jugador"] = equipo_players["player_id"].map(player_name)
    equipo_players["Dorsal"] = equipo_players["jersey_number"]

    # Partidos titulares / suplentes
    titularidades = equipo_lineup.groupby("player_id").agg(
        Convocatorias=("match_id", "count"),
        Titularidades=("is_starter", "sum"),
    ).reset_index()
    titularidades["Suplencias"] = titularidades["Convocatorias"] - titularidades["Titularidades"]
    titularidades["Jugador"] = titularidades["player_id"].map(player_name)

    # Goles
    goles_equipo = goals[goals["scoring_team_id"] == tid].groupby("scorer_player_id").size().reset_index(name="Goles")
    goles_equipo = goles_equipo.rename(columns={"scorer_player_id": "player_id"})
    titularidades = titularidades.merge(goles_equipo, on="player_id", how="left").fillna({"Goles": 0})
    titularidades["Goles"] = titularidades["Goles"].astype(int)

    # Tarjetas
    tarjetas_equipo = cards[cards["team_id"] == tid].groupby("player_id")["card_type"].value_counts().unstack(fill_value=0).reset_index()
    if "yellow" not in tarjetas_equipo.columns:
        tarjetas_equipo["yellow"] = 0
    if "red" not in tarjetas_equipo.columns:
        tarjetas_equipo["red"] = 0
    tarjetas_equipo = tarjetas_equipo.rename(columns={"yellow": "🟨", "red": "🟥"})
    titularidades = titularidades.merge(tarjetas_equipo[["player_id", "🟨", "🟥"]], on="player_id", how="left").fillna({"🟨": 0, "🟥": 0})
    titularidades["🟨"] = titularidades["🟨"].astype(int)
    titularidades["🟥"] = titularidades["🟥"].astype(int)

    dorsal_map = dict(zip(equipo_players["player_id"], equipo_players["Dorsal"]))
    titularidades["Dorsal"] = titularidades["player_id"].map(dorsal_map)

    titularidades = titularidades.sort_values(["Titularidades", "Goles"], ascending=False).reset_index(drop=True)
    titularidades.index += 1
    st.dataframe(
        titularidades[["Dorsal", "Jugador", "Convocatorias", "Titularidades", "Suplencias", "Goles", "🟨", "🟥"]],
        use_container_width=True,
    )

    # Cuerpo técnico
    ct = coaching[coaching["team_id"] == tid]
    if not ct.empty:
        st.subheader("Cuerpo técnico")
        st.dataframe(ct[["name", "role"]].drop_duplicates(), hide_index=True)

# ── Página: Sustituciones ──────────────────────────────────────
elif page == "🔄 Sustituciones":
    st.title("🔄 Sustituciones")
    df = subs.copy()
    df["Sale"] = df["player_out_id"].map(player_name)
    df["Entra"] = df["player_in_id"].map(player_name)
    df["Equipo"] = df["team_id"].map(team_name)
    df = df.merge(matches[["match_id", "match_date", "match_week"]], on="match_id", how="left")
    df["Partido"] = df.apply(
        lambda r: f"J{int(r.match_week)} · {r.match_date}", axis=1
    )
    st.dataframe(
        df[["Partido", "Equipo", "minute", "Sale", "Entra"]].sort_values(["match_date", "minute"]),
        use_container_width=True, hide_index=True,
    )

# ── Página: Explorador CSV ────────────────────────────────────
elif page == "📊 Explorador CSV":
    st.title("📊 Explorador CSV")
    csv_files = [f for f in os.listdir(DATA_DIR) if f.endswith(".csv")]
    sel_csv = st.selectbox("Archivo CSV", sorted(csv_files))
    df = load_csv(sel_csv)
    st.caption(f"{len(df)} filas · {len(df.columns)} columnas")

    # Filtro de texto
    filtro = st.text_input("Buscar en tabla (texto libre)")
    if filtro:
        mask = df.astype(str).apply(lambda col: col.str.contains(filtro, case=False, na=False)).any(axis=1)
        df = df[mask]
        st.caption(f"{len(df)} filas coinciden")

    st.dataframe(df, use_container_width=True, hide_index=True)
