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

# Initialize Google Sheets Connection for reading
conn = st.connection("gsheets", type=GSheetsConnection)


# Load Data: Local file first, fallback to Google Sheet connection
@st.cache_data(ttl=10)
def load_data():
  file_path = Path(EXCEL_FILE)
  df = pd.DataFrame()

  if file_path.is_file():
    try:
      df = pd.read_excel(file_path)
    except Exception:
      pass

  if df.empty:
    try:
      df = conn.read(spreadsheet=SHEET_URL, ttl=5)
    except Exception as e:
      st.error(f"Error loading Google Sheet: {e}")
      return pd.DataFrame()

  if df.empty:
    return pd.DataFrame()

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

# Three Clean Tabs for Navigation
tab1, tab2, tab3 = st.tabs(
    ["🏠 My Collection Gallery", "🏷️ Categories", "➕ Add / Update Cards"]
)

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
# TAB 2: CATEGORIES & TIERS (Drill-down view)
# ==========================================
with tab2:
  st.subheader("Card Categories & Rarity Tiers")

  if df_master.empty:
    st.warning("No categories available.")
  else:
    # Initialize session state for drill-down category view if not present
    if "selected_category" not in st.session_state:
      st.session_state.selected_category = None

    # VIEW A: Show grid of all categories if none is selected
    if st.session_state.selected_category is None:
      categories = df_master["rarity_tier"].dropna().unique()
      cat_cols = st.columns(5)

      for idx, category in enumerate(categories):
        col_idx = idx % 5
        cat_df = df_master[df_master["rarity_tier"] == category]

        total_cards = len(cat_df)
        owned_cards = len(cat_df[cat_df["owned"] == True])

        # Find a representative image for this category
        valid_imgs = cat_df[
            cat_df["image_url"].str.startswith("http", na=False)
        ]
        rep_img = (
            valid_imgs.iloc[0]["image_url"]
            if not valid_imgs.empty
            else "Unknown"
        )

        with cat_cols[col_idx]:
          st.markdown(f"### {category}")
          if rep_img != "Unknown":
            st.image(rep_img, use_container_width=True)
          else:
            st.markdown("🖼️️ *No Preview Image*")

          st.progress(
              owned_cards / total_cards if total_cards > 0 else 0,
              text=f"Progress: {owned_cards}/{total_cards} collected",
          )

          if st.button(f"Explore {category}", key=f"btn_{category}"):
            st.session_state.selected_category = category
            st.rerun()
          st.divider()

    # VIEW B: Drill-down view when a specific category is clicked
    else:
      active_cat = st.session_state.selected_category
      if st.button("⬅️ Back to All Categories"):
        st.session_state.selected_category = None
        st.rerun()

      st.markdown(f"## Category: {active_cat}")
      sub_df = df_master[df_master["rarity_tier"] == active_cat]

      num_cols = 4
      cols = st.columns(num_cols)

      for index, row in sub_df.reset_index().iterrows():
        col_idx = index % num_cols
        with cols[col_idx]:
          img_url = row.get("image_url")
          if pd.notna(img_url) and str(img_url).startswith("http"):
            st.image(img_url, use_container_width=True)
          else:
            st.markdown("🖼️ *No Image Available*")

          st.markdown(f"**{row['player_name']}**")
          st.caption(f"ID: `{row['card_number']}`")

          if row["owned"]:
            st.success("Collected ✓")
          else:
            st.error("Missing ❌")
          st.divider()


# ==========================================
# TAB 3: SECURE CARD ENTRY PORTAL
# ==========================================
with tab3:
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
          df_master.loc[
              df_master["card_number"] == selected_row["card_number"], "owned"
          ] = is_owned
          df_master.loc[
              df_master["card_number"] == selected_row["card_number"],
              "duplicates",
          ] = num_dup

          df_to_save = df_master.drop(columns=["display_label"])

          try:
            conn.update(spreadsheet=SHEET_URL, data=df_to_save)
            df_to_save.to_excel(EXCEL_FILE, index=False)
            st.cache_data.clear()
            st.success("Successfully updated and synced to your Google Sheet!")
            st.rerun()
          except Exception as e:
            st.error(f"Failed to update sheet: {e}")
