import pandas as pd
import streamlit as st

# Page Configuration
st.set_page_config(
    page_title="Match Attax 25/26 Tracker", page_icon="⚽", layout="wide"
)

# Fetch secrets from Streamlit secrets.toml
PASSCODE = st.secrets["passcode"]
SHEET_URL = st.secrets["sheet_url"]


# Load Data directly from Google Sheets URL
@st.cache_data(ttl=60)
def load_data_from_gsheets():
  try:
    # Extract the Sheet/File ID cleanly from your URL
    file_id = SHEET_URL.split("/d/")[1].split("/")[0]
    
    # Use Google's direct download export endpoint for Excel files (.xlsx)
    excel_url = f"https://docs.google.com/spreadsheets/d/{file_id}/export?format=xlsx"

    # Read directly using pandas Excel engine
    df = pd.read_excel(excel_url)

    if df.empty:
      return pd.DataFrame()

    # Ensure tracking columns exist
    if "owned" not in df.columns:
      df["owned"] = False
    if "duplicates" not in df.columns:
      df["duplicates"] = 0
    return df
  except Exception as e:
    st.error(
        f"Error loading Excel file from Google Drive. Make sure sharing is set to 'Anyone with the link can view'. Details: {e}"
    )
    return pd.DataFrame()

df_master = load_data_from_gsheets()

st.title("⚽ Match Attax 25/26 Collection Tracker")

# Clean Tabs for Navigation
tab1, tab2 = st.tabs(["🏠 My Collection Gallery", "➕ Add / Update Cards"])

# ==========================================
# TAB 1: LANDING PAGE (Collection Gallery)
# ==========================================
with tab1:
  st.subheader("Visual Card Gallery")

  if df_master.empty:
    st.warning(
        "Your Google Sheet appears to be empty or inaccessible. Please populate"
        " it with your scraped data."
    )
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
          # Render image safely using updated container width parameter
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
      # Create dropdown label combining Player Name + Rarity + Card Number
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

        st.info(
            "Note: Since your Google Sheet is read via URL for fast loading,"
            " updates made here are saved to your local/session state view."
            " Paste your exported master dataset directly into your Google"
            " Sheet to sync permanently across devices!"
        )

        if st.button("Update Local View"):
          # Update dataframe value in memory
          df_master.loc[
              df_master["card_number"] == selected_row["card_number"], "owned"
          ] = is_owned
          df_master.loc[
              df_master["card_number"] == selected_row["card_number"],
              "duplicates",
          ] = num_dup

          # Clear cache so data updates immediately
          st.cache_data.clear()
          st.success("Successfully updated tracker view!")
          st.rerun()
