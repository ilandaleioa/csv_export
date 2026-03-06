import streamlit as st
import pandas as pd
import os
import zipfile
import io
import shutil
import re

# ── Configuración ──────────────────────────────────────────────
st.set_page_config(page_title="Athletic Club · CSV Explorer", layout="wide", page_icon="⚽")

APP_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_ROOT = os.path.join(APP_DIR, "data")
os.makedirs(DATA_ROOT, exist_ok=True)

# Migrar la carpeta csv_export original a data/ si aún no se ha hecho
_legacy_dir = os.path.join(APP_DIR, "csv_export")
if os.path.isdir(_legacy_dir) and os.path.isfile(os.path.join(_legacy_dir, "Match.csv")):
    _dest = os.path.join(DATA_ROOT, "csv_export")
    if not os.path.isdir(_dest):
        shutil.copytree(_legacy_dir, _dest)

# ── Descubrir carpetas de competición ──────────────────────────
REQUIRED_CSV = "Match.csv"

def discover_competitions():
    """Devuelve {nombre_carpeta: ruta} para cada subcarpeta de data/ que contenga Match.csv"""
    comps = {}
    for name in sorted(os.listdir(DATA_ROOT)):
        folder = os.path.join(DATA_ROOT, name)
        if os.path.isdir(folder) and os.path.isfile(os.path.join(folder, REQUIRED_CSV)):
            comps[name] = folder
    return comps

def competition_label(folder_path):
    """Intenta leer Competition_Season.csv para obtener un nombre legible."""
    cs_path = os.path.join(folder_path, "Competition_Season.csv")
    if os.path.isfile(cs_path):
        try:
            df = pd.read_csv(cs_path)
            if not df.empty:
                row = df.iloc[0]
                parts = []
                if pd.notna(row.get("competition_name")):
                    parts.append(str(row["competition_name"]))
                if pd.notna(row.get("season_name")):
                    parts.append(str(row["season_name"]))
                if parts:
                    return " · ".join(parts)
        except Exception:
            pass
    return os.path.basename(folder_path)

# ── Sidebar ────────────────────────────────────────────────────
st.sidebar.title("⚽ Athletic Club")
st.sidebar.caption("CSV Explorer")

# --- Importar nueva competición ---
st.sidebar.markdown("---")
st.sidebar.subheader("📥 Importar competición")
uploaded_zip = st.sidebar.file_uploader(
    "Sube un ZIP con los CSV", type=["zip"], help="El ZIP debe contener los CSV de StatsBomb (Match.csv, Team.csv, etc.)"
)
if uploaded_zip is not None:
    # Nombre de carpeta seguro a partir del nombre del ZIP
    safe_name = re.sub(r"[^\w\-.]", "_", os.path.splitext(uploaded_zip.name)[0])
    dest_folder = os.path.join(DATA_ROOT, safe_name)
    if os.path.isdir(dest_folder):
        st.sidebar.warning(f"Ya existe '{safe_name}'. Borra la carpeta para reimportar.")
    else:
        with zipfile.ZipFile(io.BytesIO(uploaded_zip.read())) as zf:
            # Buscar dónde está Match.csv dentro del ZIP
            csv_members = [m for m in zf.namelist() if m.endswith(".csv") and not m.startswith("__MACOSX")]
            if not csv_members:
                st.sidebar.error("No se encontraron CSVs en el ZIP.")
            else:
                # Detectar prefijo común (por si los CSV están en una subcarpeta del ZIP)
                match_member = [m for m in csv_members if m.endswith("/Match.csv") or m == "Match.csv"]
                prefix = ""
                if match_member:
                    prefix = match_member[0].rsplit("Match.csv", 1)[0]

                os.makedirs(dest_folder, exist_ok=True)
                for member in csv_members:
                    if member.startswith(prefix):
                        filename = os.path.basename(member)
                        if filename:
                            data = zf.read(member)
                            with open(os.path.join(dest_folder, filename), "wb") as f:
                                f.write(data)

                if os.path.isfile(os.path.join(dest_folder, REQUIRED_CSV)):
                    st.sidebar.success(f"✅ Importado: {safe_name}")
                    st.cache_data.clear()
                    st.rerun()
                else:
                    shutil.rmtree(dest_folder, ignore_errors=True)
                    st.sidebar.error("El ZIP no contiene Match.csv.")

# --- Selector de competición ---
competitions = discover_competitions()

if not competitions:
    st.error("No hay datos. Sube un ZIP con CSVs de StatsBomb usando el panel lateral.")
    st.stop()

st.sidebar.markdown("---")
comp_labels = {k: competition_label(v) for k, v in competitions.items()}
sel_comp_key = st.sidebar.selectbox(
    "🏆 Competición",
    list(competitions.keys()),
    format_func=lambda k: comp_labels[k],
)
DATA_DIR = competitions[sel_comp_key]

# ── Carga de datos ─────────────────────────────────────────────
@st.cache_data
def load_csv(data_dir, name):
    path = os.path.join(data_dir, name)
    if os.path.isfile(path):
        return pd.read_csv(path)
    return pd.DataFrame()

@st.cache_data
def load_all(data_dir):
    teams = load_csv(data_dir, "Team.csv")
    players = load_csv(data_dir, "Player.csv")
    matches = load_csv(data_dir, "Match.csv")
    goals = load_csv(data_dir, "Goal.csv")
    cards = load_csv(data_dir, "Card.csv")
    lineups = load_csv(data_dir, "Lineup.csv")
    subs = load_csv(data_dir, "Substitution.csv")
    stadiums = load_csv(data_dir, "Stadium.csv")
    referees = load_csv(data_dir, "Referee.csv")
    coaching = load_csv(data_dir, "CoachingStaff.csv")
    competition = load_csv(data_dir, "Competition_Season.csv")
    return teams, players, matches, goals, cards, lineups, subs, stadiums, referees, coaching, competition

teams, players, matches, goals, cards, lineups, subs, stadiums, referees, coaching, competition = load_all(DATA_DIR)

# Diccionarios auxiliares
team_map = dict(zip(teams["team_id"], teams["team_name"])) if not teams.empty else {}
player_map = dict(zip(players["player_id"], players["player_name"])) if not players.empty else {}
stadium_map = dict(zip(stadiums["stadium_id"], stadiums["name"])) if not stadiums.empty else {}
referee_map = dict(zip(referees["referee_id"], referees["name"])) if not referees.empty else {}

def team_name(tid):
    return team_map.get(tid, str(tid))

def player_name(pid):
    return player_map.get(pid, str(pid))

st.sidebar.markdown("---")
sel_equipo_global = st.sidebar.selectbox(
    "🔍 Filtrar por equipo",
    ["Todos"] + sorted(team_map.values()),
    key="filtro_equipo_global",
)

# IDs del equipo seleccionado (para usar en todas las secciones)
_equipo_ids = [k for k, v in team_map.items() if v == sel_equipo_global] if sel_equipo_global != "Todos" else []

# Filtro de jugador (dependiente del equipo)
if _equipo_ids:
    _jugadores_equipo = lineups[lineups["team_id"].isin(_equipo_ids)]["player_id"].unique()
    _opciones_jugador = sorted(
        [player_map[pid] for pid in _jugadores_equipo if pid in player_map]
    )
else:
    _opciones_jugador = sorted(player_map.values())

sel_jugador_global = st.sidebar.selectbox(
    "👤 Filtrar por jugador",
    ["Todos"] + _opciones_jugador,
    key="filtro_jugador_global",
)

_jugador_ids = [k for k, v in player_map.items() if v == sel_jugador_global] if sel_jugador_global != "Todos" else []

page = st.sidebar.radio(
    "Sección",
    ["🏠 Inicio", "📅 Partidos", "⚽ Goles", "🟨 Tarjetas", "👥 Plantillas", "🔄 Sustituciones", "📈 Gráficas", "📊 Explorador CSV"],
)

# ── Página: Inicio ─────────────────────────────────────────────
if page == "🏠 Inicio":
    st.title("Athletic Club · Datos de Competición")

    if not competition.empty:
        comp = competition.iloc[0]
        st.markdown(f"**Competición:** {comp.get('competition_name', '–')}  ·  **Temporada:** {comp.get('season_name', '–')}")

    _matches_inicio = matches.copy()
    _goals_inicio = goals.copy()
    _players_inicio = players.copy()
    if _equipo_ids:
        _matches_inicio = _matches_inicio[(_matches_inicio["home_team_id"].isin(_equipo_ids)) | (_matches_inicio["away_team_id"].isin(_equipo_ids))]
        _match_ids_inicio = _matches_inicio["match_id"].unique()
        _goals_inicio = _goals_inicio[_goals_inicio["match_id"].isin(_match_ids_inicio)]
        _lineup_inicio = lineups[lineups["match_id"].isin(_match_ids_inicio) & lineups["team_id"].isin(_equipo_ids)]
        _players_inicio = players[players["player_id"].isin(_lineup_inicio["player_id"].unique())]
    if _jugador_ids:
        _goals_inicio = _goals_inicio[_goals_inicio["scorer_player_id"].isin(_jugador_ids)]
        _players_inicio = _players_inicio[_players_inicio["player_id"].isin(_jugador_ids)]

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Equipos", len(teams) if not _equipo_ids else 1)
    col2.metric("Partidos", len(_matches_inicio))
    col3.metric("Jugadores", len(_players_inicio))
    col4.metric("Goles", len(_goals_inicio))

    st.subheader("Clasificación (puntos estimados)")
    # Calcular clasificación básica
    rows = []
    for _, m in _matches_inicio.iterrows():
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
            height=(len(tabla) + 1) * 35 + 3,
        )

# ── Página: Partidos ───────────────────────────────────────────
elif page == "📅 Partidos":
    st.title("📅 Partidos")

    # Aplicar filtros globales
    df = matches.copy()
    if _equipo_ids:
        df = df[(df["home_team_id"].isin(_equipo_ids)) | (df["away_team_id"].isin(_equipo_ids))]
    if _jugador_ids:
        _match_ids_jugador = lineups[lineups["player_id"].isin(_jugador_ids)]["match_id"].unique()
        df = df[df["match_id"].isin(_match_ids_jugador)]

    # Filtro de jornada
    jornadas = sorted(df["match_week"].dropna().unique())
    sel_jornada = st.selectbox("Jornada", ["Todas"] + [int(j) for j in jornadas])

    if sel_jornada != "Todas":
        df = df[df["match_week"] == sel_jornada]

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
    _matches_detail = matches.copy()
    if _equipo_ids:
        _matches_detail = _matches_detail[(_matches_detail["home_team_id"].isin(_equipo_ids)) | (_matches_detail["away_team_id"].isin(_equipo_ids))]
    if _jugador_ids:
        _match_ids_detail_jug = lineups[lineups["player_id"].isin(_jugador_ids)]["match_id"].unique()
        _matches_detail = _matches_detail[_matches_detail["match_id"].isin(_match_ids_detail_jug)]
    match_options = {
        f"J{int(r.match_week)} · {team_name(r.home_team_id)} {int(r.home_score)}-{int(r.away_score)} {team_name(r.away_team_id)} ({r.match_date})": r.match_id
        for _, r in _matches_detail.iterrows()
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
    if _equipo_ids:
        _match_ids_goles = matches[(matches["home_team_id"].isin(_equipo_ids)) | (matches["away_team_id"].isin(_equipo_ids))]["match_id"].unique()
        df = df[df["match_id"].isin(_match_ids_goles)]
    if _jugador_ids:
        df = df[df["scorer_player_id"].isin(_jugador_ids)]
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
    if _equipo_ids:
        _match_ids_tarj = matches[(matches["home_team_id"].isin(_equipo_ids)) | (matches["away_team_id"].isin(_equipo_ids))]["match_id"].unique()
        df = df[df["match_id"].isin(_match_ids_tarj)]
    if _jugador_ids:
        df = df[df["player_id"].isin(_jugador_ids)]
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
    if _equipo_ids:
        # Si hay filtro global de equipo, usarlo directamente
        _plantilla_opciones = [team_map[tid] for tid in _equipo_ids]
    else:
        _plantilla_opciones = sorted(team_map.values())
    sel = st.selectbox("Equipo", _plantilla_opciones, index=0)
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
    _n_rows = len(titularidades)
    _table_height = min(36 * (_n_rows + 1) + 2, 36 * 26 + 2)  # hasta 25 filas sin scroll
    st.dataframe(
        titularidades[["Dorsal", "Jugador", "Convocatorias", "Titularidades", "Suplencias", "Goles", "🟨", "🟥"]],
        use_container_width=True,
        height=_table_height,
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
    if _equipo_ids:
        _match_ids_subs = matches[(matches["home_team_id"].isin(_equipo_ids)) | (matches["away_team_id"].isin(_equipo_ids))]["match_id"].unique()
        df = df[df["match_id"].isin(_match_ids_subs)]
    if _jugador_ids:
        df = df[(df["player_out_id"].isin(_jugador_ids)) | (df["player_in_id"].isin(_jugador_ids))]
    df["Sale"] = df["player_out_id"].map(player_name)
    df["Entra"] = df["player_in_id"].map(player_name)
    df["Equipo"] = df["team_id"].map(team_name)
    df = df.merge(matches[["match_id", "match_date", "match_week"]], on="match_id", how="left")
    df["Partido"] = df.apply(
        lambda r: f"J{int(r.match_week)} · {r.match_date}", axis=1
    )
    st.dataframe(
        df.sort_values(["match_date", "minute"])[["Partido", "Equipo", "minute", "Sale", "Entra"]],
        use_container_width=True, hide_index=True,
    )

# ── Página: Gráficas ──────────────────────────────────────────
elif page == "📈 Gráficas":
    import altair as alt

    st.title("📈 Gráficas")

    _g_matches = matches.copy()
    _g_goals = goals.copy()
    if _equipo_ids:
        _g_matches = _g_matches[(_g_matches["home_team_id"].isin(_equipo_ids)) | (_g_matches["away_team_id"].isin(_equipo_ids))]
    _g_match_ids = _g_matches["match_id"].unique()
    _g_goals = _g_goals[_g_goals["match_id"].isin(_g_match_ids)]

    # ── Gráficas de EQUIPO ─────────────────────────────────────────
    st.header("🏟️ Estadísticas por equipo")

    team_rows = []
    for _, m in _g_matches.iterrows():
        hs, aws = m["home_score"], m["away_score"]
        ht, at = m["home_team_id"], m["away_team_id"]
        if hs > aws:
            team_rows.append({"team_id": ht, "PJ": 1, "PG": 1, "PE": 0, "PP": 0, "GF": hs, "GC": aws})
            team_rows.append({"team_id": at, "PJ": 1, "PG": 0, "PE": 0, "PP": 1, "GF": aws, "GC": hs})
        elif hs < aws:
            team_rows.append({"team_id": ht, "PJ": 1, "PG": 0, "PE": 0, "PP": 1, "GF": hs, "GC": aws})
            team_rows.append({"team_id": at, "PJ": 1, "PG": 1, "PE": 0, "PP": 0, "GF": aws, "GC": hs})
        else:
            team_rows.append({"team_id": ht, "PJ": 1, "PG": 0, "PE": 1, "PP": 0, "GF": hs, "GC": aws})
            team_rows.append({"team_id": at, "PJ": 1, "PG": 0, "PE": 1, "PP": 0, "GF": aws, "GC": hs})

    if team_rows:
        team_stats = pd.DataFrame(team_rows).groupby("team_id").sum().reset_index()
        team_stats["Equipo"] = team_stats["team_id"].map(team_name)
        team_stats = team_stats.sort_values("PJ", ascending=False)

        st.subheader("Partidos jugados por equipo")
        chart_pj = alt.Chart(team_stats).mark_bar(color="#1f77b4").encode(
            x=alt.X("PJ:Q", title="Partidos jugados"),
            y=alt.Y("Equipo:N", sort="-x", title=""),
            tooltip=["Equipo", "PJ", "PG", "PE", "PP"],
        ).properties(height=max(len(team_stats) * 22, 200))
        st.altair_chart(chart_pj, use_container_width=True)

        st.subheader("Resultados: Victorias, Empates y Derrotas")
        results_melt = team_stats.melt(
            id_vars=["Equipo"], value_vars=["PG", "PE", "PP"],
            var_name="Resultado", value_name="Cantidad",
        )
        results_melt["Resultado"] = results_melt["Resultado"].map({"PG": "Victorias", "PE": "Empates", "PP": "Derrotas"})
        chart_res = alt.Chart(results_melt).mark_bar().encode(
            x=alt.X("Cantidad:Q", title=""),
            y=alt.Y("Equipo:N", sort=alt.EncodingSortField(field="Cantidad", op="sum", order="descending"), title=""),
            color=alt.Color("Resultado:N", scale=alt.Scale(domain=["Victorias", "Empates", "Derrotas"], range=["#2ca02c", "#ff7f0e", "#d62728"])),
            tooltip=["Equipo", "Resultado", "Cantidad"],
        ).properties(height=max(len(team_stats) * 22, 200))
        st.altair_chart(chart_res, use_container_width=True)

        st.subheader("Goles a favor y en contra por equipo")
        goals_melt = team_stats.melt(
            id_vars=["Equipo"], value_vars=["GF", "GC"],
            var_name="Tipo", value_name="Goles",
        )
        goals_melt["Tipo"] = goals_melt["Tipo"].map({"GF": "A favor", "GC": "En contra"})
        chart_goals = alt.Chart(goals_melt).mark_bar().encode(
            x=alt.X("Goles:Q", title=""),
            y=alt.Y("Equipo:N", sort=alt.EncodingSortField(field="Goles", op="sum", order="descending"), title=""),
            color=alt.Color("Tipo:N", scale=alt.Scale(domain=["A favor", "En contra"], range=["#2ca02c", "#d62728"])),
            tooltip=["Equipo", "Tipo", "Goles"],
            xOffset="Tipo:N",
        ).properties(height=max(len(team_stats) * 22, 200))
        st.altair_chart(chart_goals, use_container_width=True)
    else:
        st.info("No hay datos de partidos para generar gráficas.")

    # ── Gráficas de JUGADOR ────────────────────────────────────────
    st.header("👤 Estadísticas por jugador")

    if _equipo_ids:
        _graf_opciones = [team_map[tid] for tid in _equipo_ids]
    else:
        _graf_opciones = sorted(team_map.values())
    sel_equipo_graf = st.selectbox("Equipo", _graf_opciones, index=0, key="graf_equipo")
    _sel_tid = [k for k, v in team_map.items() if v == sel_equipo_graf][0]

    _eq_matches = matches[(matches["home_team_id"] == _sel_tid) | (matches["away_team_id"] == _sel_tid)]
    _eq_match_ids = _eq_matches["match_id"].unique()
    _eq_lineup = lineups[(lineups["team_id"] == _sel_tid) & (lineups["match_id"].isin(_eq_match_ids))].copy()

    if _eq_lineup.empty:
        st.info("No hay datos de alineación para este equipo.")
    else:
        player_stats = _eq_lineup.groupby("player_id").agg(
            Convocatorias=("match_id", "count"),
            Titularidades=("is_starter", "sum"),
        ).reset_index()
        player_stats["Suplencias"] = player_stats["Convocatorias"] - player_stats["Titularidades"]

        # Minutos jugados (estimación)
        _eq_subs = subs[subs["match_id"].isin(_eq_match_ids) & (subs["team_id"] == _sel_tid)].copy()
        min_rows = []
        for _, row in _eq_lineup.iterrows():
            pid = row["player_id"]
            mid = row["match_id"]
            is_starter = row["is_starter"] == 1
            sub_out = _eq_subs[(_eq_subs["match_id"] == mid) & (_eq_subs["player_out_id"] == pid)]
            sub_in = _eq_subs[(_eq_subs["match_id"] == mid) & (_eq_subs["player_in_id"] == pid)]
            if is_starter:
                mins = int(sub_out.iloc[0]["minute"]) if not sub_out.empty else 90
            else:
                mins = 90 - int(sub_in.iloc[0]["minute"]) if not sub_in.empty else 0
            min_rows.append({"player_id": pid, "Minutos": mins})

        min_df = pd.DataFrame(min_rows).groupby("player_id")["Minutos"].sum().reset_index()
        player_stats = player_stats.merge(min_df, on="player_id", how="left").fillna({"Minutos": 0})
        player_stats["Minutos"] = player_stats["Minutos"].astype(int)

        # Goles
        _eq_goals = goals[(goals["scoring_team_id"] == _sel_tid) & (goals["match_id"].isin(_eq_match_ids))]
        goles_jug = _eq_goals.groupby("scorer_player_id").size().reset_index(name="Goles")
        goles_jug = goles_jug.rename(columns={"scorer_player_id": "player_id"})
        player_stats = player_stats.merge(goles_jug, on="player_id", how="left").fillna({"Goles": 0})
        player_stats["Goles"] = player_stats["Goles"].astype(int)

        player_stats["Jugador"] = player_stats["player_id"].map(player_name)

        # Filtrar por jugador global si aplica
        if _jugador_ids:
            player_stats = player_stats[player_stats["player_id"].isin(_jugador_ids)]

        player_stats = player_stats.sort_values("Minutos", ascending=False)

        top_n = st.slider("Mostrar top jugadores", 5, max(len(player_stats), 5), min(15, len(player_stats)), key="graf_topn")
        p_top = player_stats.head(top_n)

        st.subheader("Partidos: Titularidades y Suplencias")
        conv_melt = p_top.melt(
            id_vars=["Jugador"], value_vars=["Titularidades", "Suplencias"],
            var_name="Tipo", value_name="Partidos",
        )
        chart_conv = alt.Chart(conv_melt).mark_bar().encode(
            x=alt.X("Partidos:Q", title=""),
            y=alt.Y("Jugador:N", sort=alt.EncodingSortField(field="Partidos", op="sum", order="descending"), title=""),
            color=alt.Color("Tipo:N", scale=alt.Scale(domain=["Titularidades", "Suplencias"], range=["#1f77b4", "#aec7e8"])),
            tooltip=["Jugador", "Tipo", "Partidos"],
        ).properties(height=max(top_n * 25, 200))
        st.altair_chart(chart_conv, use_container_width=True)

        st.subheader("Minutos jugados")
        chart_min = alt.Chart(p_top).mark_bar(color="#ff7f0e").encode(
            x=alt.X("Minutos:Q", title="Minutos"),
            y=alt.Y("Jugador:N", sort="-x", title=""),
            tooltip=["Jugador", "Minutos", "Convocatorias", "Titularidades"],
        ).properties(height=max(top_n * 25, 200))
        st.altair_chart(chart_min, use_container_width=True)

        st.subheader("Goles por jugador")
        p_goles = player_stats[player_stats["Goles"] > 0].sort_values("Goles", ascending=False)
        if p_goles.empty:
            st.info("No hay goles registrados para este equipo.")
        else:
            chart_gol = alt.Chart(p_goles).mark_bar(color="#2ca02c").encode(
                x=alt.X("Goles:Q", title="Goles"),
                y=alt.Y("Jugador:N", sort="-x", title=""),
                tooltip=["Jugador", "Goles", "Minutos"],
            ).properties(height=max(len(p_goles) * 25, 150))
            st.altair_chart(chart_gol, use_container_width=True)

        st.subheader("Tabla resumen")
        tabla_graf = player_stats[["Jugador", "Convocatorias", "Titularidades", "Suplencias", "Minutos", "Goles"]].reset_index(drop=True)
        tabla_graf.index += 1
        st.dataframe(tabla_graf, use_container_width=True)

# ── Página: Explorador CSV ────────────────────────────────────
elif page == "📊 Explorador CSV":
    st.title("📊 Explorador CSV")
    csv_files = [f for f in os.listdir(DATA_DIR) if f.endswith(".csv")]
    sel_csv = st.selectbox("Archivo CSV", sorted(csv_files))
    df = load_csv(DATA_DIR, sel_csv)
    st.caption(f"{len(df)} filas · {len(df.columns)} columnas")

    # Aplicar filtros globales transversales
    _total_antes = len(df)
    if _equipo_ids:
        _team_cols = [c for c in df.columns if c in ("team_id", "home_team_id", "scoring_team_id")]
        _match_cols = [c for c in df.columns if c == "match_id"]
        if _team_cols:
            _mask_team = pd.DataFrame(False, index=df.index, columns=["_hit"])
            for tc in _team_cols:
                _mask_team["_hit"] = _mask_team["_hit"] | df[tc].isin(_equipo_ids)
            # Si hay away_team_id, incluirlo también
            if "away_team_id" in df.columns:
                _mask_team["_hit"] = _mask_team["_hit"] | df["away_team_id"].isin(_equipo_ids)
            df = df[_mask_team["_hit"]]
        elif _match_cols:
            _match_ids_filtro = matches[(matches["home_team_id"].isin(_equipo_ids)) | (matches["away_team_id"].isin(_equipo_ids))]["match_id"].unique()
            df = df[df["match_id"].isin(_match_ids_filtro)]
    if _jugador_ids:
        _player_cols = [c for c in df.columns if c in ("player_id", "scorer_player_id", "player_out_id", "player_in_id")]
        if _player_cols:
            _mask_player = pd.DataFrame(False, index=df.index, columns=["_hit"])
            for pc in _player_cols:
                _mask_player["_hit"] = _mask_player["_hit"] | df[pc].isin(_jugador_ids)
            df = df[_mask_player["_hit"]]
        elif "match_id" in df.columns:
            _match_ids_jug_csv = lineups[lineups["player_id"].isin(_jugador_ids)]["match_id"].unique()
            df = df[df["match_id"].isin(_match_ids_jug_csv)]
    if len(df) < _total_antes:
        st.caption(f"🔍 Filtros globales aplicados: {len(df)} de {_total_antes} filas")

    # Filtro de texto
    filtro = st.text_input("Buscar en tabla (texto libre)")
    if filtro:
        mask = df.astype(str).apply(lambda col: col.str.contains(filtro, case=False, na=False)).any(axis=1)
        df = df[mask]
        st.caption(f"{len(df)} filas coinciden")

    st.dataframe(df, use_container_width=True, hide_index=True)
