import streamlit as st
from supabase import create_client, Client

# --- KONFIGURACJA STRONY ---
st.set_page_config(page_title="Menadżer Magazynu", layout="centered")

# --- 1. POŁĄCZENIE Z SUPABASE ---
@st.cache_resource
def init_connection():
    try:
        url = st.secrets["SUPABASE_URL"]
        key = st.secrets["SUPABASE_KEY"]
        return create_client(url, key)
    except FileNotFoundError:
        st.error("❌ Brak pliku .streamlit/secrets.toml")
        st.stop()
    except KeyError:
        st.error("❌ Brak kluczy w secrets.toml")
        st.stop()

supabase = init_connection()

# --- NAZWY TABEL ---
# Używamy małych liter, zgodnie z Twoim ostatnim błędem
TABLE_PRODUCTS = "produkty"
TABLE_CATEGORIES = "kategorie"

st.title("📦 Menadżer Magazynu")

# --- ZAKŁADKI ---
tab1, tab2, tab3, tab4 = st.tabs(["Kategorie", "Produkty", "Wydanie", "Podgląd"])

# ==========================================
# ZAKŁADKA 1: DODAWANIE KATEGORII
# ==========================================
with tab1:
    st.header("Dodaj Kategorię")
    with st.form("cat_form", clear_on_submit=True):
        name = st.text_input("Nazwa")
        desc = st.text_area("Opis")
        if st.form_submit_button("Zapisz"):
            if name:
                try:
                    supabase.table(TABLE_CATEGORIES).insert({"nazwa": name, "opis": desc}).execute()
                    st.success("Zapisano!")
                    st.rerun() # Odświeżamy stronę natychmiast
                except Exception as e:
                    st.error(f"Błąd: {e}")
            else:
                st.warning("Podaj nazwę.")

# ==========================================
# ZAKŁADKA 2: DODAWANIE PRODUKTU
# ==========================================
with tab2:
    st.header("Dodaj Produkt")
    
    # Pobranie kategorii
    try:
        cats = supabase.table(TABLE_CATEGORIES).select("id, nazwa").execute().data
    except:
        cats = []
        
    if not cats:
        st.warning("Dodaj najpierw kategorię.")
    else:
        cat_map = {c['nazwa']: c['id'] for c in cats}
        
        with st.form("prod_form", clear_on_submit=True):
            p_name = st.text_input("Nazwa produktu")
            c1, c2 = st.columns(2)
            p_qty = c1.number_input("Ilość", min_value=0, step=1)
            p_price = c2.number_input("Cena", min_value=0.0, step=0.01)
            p_cat = st.selectbox("Kategoria", list(cat_map.keys()))
            
            if st.form_submit_button("Zapisz"):
                if p_name:
                    try:
                        data = {
                            "nazwa": p_name,
                            "liczba": p_qty,
                            "cena": p_price,
                            "kategoria": cat_map[p_cat]
                        }
                        supabase.table(TABLE_PRODUCTS).insert(data).execute()
                        st.success("Zapisano!")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Błąd: {e}")
                else:
                    st.warning("Podaj nazwę produktu.")

# ==========================================
# ZAKŁADKA 3: WYDANIE (AKTUALIZACJA)
# ==========================================
with tab3:
    st.header("Wydanie Towaru")
    
    try:
        prods = supabase.table(TABLE_PRODUCTS).select("id, nazwa, liczba").execute().data
    except:
        prods = []
        
    if not prods:
        st.info("Brak produktów.")
    else:
        # Lista wyboru z widocznym stanem
        prod_map = {f"{p['nazwa']} (Stan: {p['liczba']})": p for p in prods}
        sel_key = st.selectbox("Wybierz produkt", list(prod_map.keys()))
        sel_prod = prod_map[sel_key]
        
        with st.form("update_form"):
            to_remove = st.number_input("Ile wydać?", min_value=1, max_value=sel_prod['liczba'], step=1)
            
            if st.form_submit_button("Zatwierdź"):
                try:
                    new_qty = sel_prod['liczba'] - to_remove
                    supabase.table(TABLE_PRODUCTS).update({"liczba": new_qty}).eq("id", sel_prod['id']).execute()
                    st.success("Zaktualizowano!")
                    st.rerun()
                except Exception as e:
                    st.error(f"Błąd: {e}")

# ==========================================
# ZAKŁADKA 4: PODGLĄD
with tab4:
    st.header("Stan Magazynowy")
    if st.button("Odśwież"):
        st.rerun()
        
    try:
        # Próba pobrania z nazwą kategorii
        res = supabase.table(TABLE_PRODUCTS).select(f"*, {TABLE_CATEGORIES}(nazwa)").order('id').execute()
        
        # Proste formatowanie danych do listy słowników (Streamlit to wyświetli)
        display_data = []
        for item in res.data:
            # Bezpieczne wyciąganie nazwy kategorii
            cat_obj = item.get(TABLE_CATEGORIES)
            cat_name = cat_obj['nazwa'] if cat_obj else "-"
            
            display_data.append({
                "ID": item['id'],
                "Produkt": item['nazwa'],
                "Ilość": item['liczba'],
                "Cena": item['cena'],
                "Kategoria": cat_name
            })
            
        st.dataframe(display_data, use_container_width=True)
        
    except Exception as e:
        st.error(f"Błąd pobierania danych: {e}")
