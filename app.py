from pathlib import Path
import pandas as pd
import streamlit as st
from streamlit_gsheets import GSheetsConnection

# Page Configuration
st.set_page_config(
    page_title="Match Attax 25/26 Tracker", page_icon="⚽", layout="wide"
)

PASSCODE = st.secrets["passcode"]
SHEET_URL = st.secrets["sheet_url"]
EXCEL_FILE = "match_attax_checklist.xlsx"

# Initialize Google Sheets Connection
conn = st.connection("gsheets", type=GSheetsConnection)


# Load Data: Local file first, fallback to Google Sheet connection
@st.cache_data(ttl=10)
def load_data():
  file_path = Path(EXCEL_FILE)
  df = pd.DataFrame()

  # 1. Try loading local file first (great for local running/scraper updates)
  if file_path.is_file():
    try:
      df = pd.read_excel(file_path)
    except Exception:
      pass

  # 2. If local file doesn't exist or failed, load from live Google Sheet connection
  if df.empty:
    try:
      df = conn.read(spreadsheet=SHEET_URL, ttl=5)
    except Exception as e:
      st.error(f"Error loading Google Sheet: {e}")
      return pd.DataFrame()

  if df.empty:
    return pd.DataFrame()

  # Ensure tracking columns exist & clean NaN values
  if "owned" not in df.columns:
    df["owned"] = False
  else:
    df["owned"] = df["owned"].fillna(False).astype(bool)

  if "duplicates" not in df.columns:
    df["duplicates"] = 0
  else:
    df["duplicates"] = df["duplicates"].fillna(0).astype(int)

  return df


df_master = load_data()

st.title("⚽ Match Attax 25/26 Collection Tracker")

tab1, tab2 = st.tabs(["🏠 My Collection Gallery", "➕ Add / Update Cards"])

# ==========================================
# TAB 1: LANDING PAGE (Collection Gallery)
# ==========================================
with tab1:
  st.subheader("Visual Card Gallery")

  if df_master.empty:
    st.warning("Your collection checklist is empty.")
  else:
    show_only_owned = st.checkbox(
        "Show only collected cards", value=False, key="filter_owned"
    )

    display_df = (
        df_master[df_master["owned"] == True] if show_only_owned else df_master
    )

    if display_df.empty:
      st.info("No cards match your filter criteria.")
    else:
      num_cols = 4
      cols = st.columns(num_cols)

      for index, row in display_df.iterrows():
        col_idx = index % num_cols
        with cols[col_idx]:
          img_url = row.get("image_url")
          if pd.notna(img_url) and str(img_url).startswith("http"):
            st.image(img_url, use_container_width=True)
          else:
            st.markdown("🖼️ *No Image Available*")

          st.markdown(f"**{row['player_name']}**")
          st.caption(f"ID: `{row['card_number']}` | Tier: {row['rarity_tier']}")

          if row["owned"]:
            st.success("Collected ✓")
          else:
            st.error("Missing ❌")
          st.divider()

# ==========================================
# TAB 2: SECURE CARD ENTRY PORTAL
# ==========================================
with tab2:
  st.subheader("Card Management Portal")

  if "authenticated" not in st.session_state:
    st.session_state.authenticated = False

  if not st.session_state.authenticated:
    st.warning("🔒 This section is password protected.")
    entered_passcode = st.text_input(
        "Enter Passcode to Unlock:", type="password", key="pass_input"
    )

    if st.button("Unlock Portal"):
      if entered_passcode == PASSCODE:
        st.session_state.authenticated = True
        st.rerun()
      else:
        st.error("Incorrect passcode!")
  else:
    st.success("Unlocked successfully!")

    if st.button("Lock Portal Again"):
      st.session_state.authenticated = False
      st.rerun()

    st.divider()

    if df_master.empty:
      st.error("No data available to update.")
    else:
      df_master["display_label"] = (
          df_master["player_name"]
          + " — "
          + df_master["rarity_tier"]
          + " ("
          + df_master["card_number"]
          + ")"
      )

      selected_label = st.selectbox(
          "Select Card to Update:",
          df_master["display_label"].tolist(),
          key="card_select",
      )

      selected_row = df_master[
          df_master["display_label"] == selected_label
      ].iloc[0]

      col_img, col_form = st.columns([1, 2])
      with col_img:
        img_url = selected_row.get("image_url")
        if pd.notna(img_url) and str(img_url).startswith("http"):
          st.image(img_url, use_container_width=True)

      with col_form:
        is_owned = st.checkbox(
            "I own this card",
            value=bool(selected_row["owned"]),
            key="own_check",
        )
        num_dup = st.number_input(
            "Number of Duplicates",
            min_value=0,
            max_value=10,
            value=int(selected_row["duplicates"]),
            key="dup_num",
        )

        if st.button("Save Changes to Live Google Sheet"):
          # 1. Update dataframe value in memory
          df_master.loc[
              df_master["card_number"] == selected_row["card_number"], "owned"
          ] = is_owned
          df_master.loc[
              df_master["card_number"] == selected_row["card_number"],
              "duplicates",
          ] = num_dup

          # 2. Clean up temporary display column before saving
          df_to_save = df_master.drop(columns=["display_label"])

          try:
            # 3. Write changes back to the live Google Sheet
            conn.update(spreadsheet=SHEET_URL, data=df_to_save)

            # 4. Also save locally if running on a local machine
            df_to_save.to_excel(EXCEL_FILE, index=False)

            # 5. Clear cache so changes reflect instantly
            st.cache_data.clear()
            st.success("Successfully updated and synced to your Google Sheet!")
            st.rerun()
          except Exception as e:
            st.error(f"Failed to update sheet: {e}")
