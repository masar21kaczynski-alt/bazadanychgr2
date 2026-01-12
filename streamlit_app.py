import streamlit as st
from supabase import create_client, Client

# --- KONFIGURACJA STRONY ---
st.set_page_config(page_title="Menadżer Magazynu", layout="centered")

# --- 1. POŁĄCZENIE Z SUPABASE ---
# Używamy cache, żeby nie łączyć się z bazą przy każdym kliknięciu
@st.cache_resource
def init_connection():
    try:
        url = st.secrets["SUPABASE_URL"]
        key = st.secrets["SUPABASE_KEY"]
        return create_client(url, key)
    except FileNotFoundError:
        st.error("❌ Brak pliku `.streamlit/secrets.toml`! Utwórz go i dodaj tam URL oraz KEY.")
        st.stop()
    except KeyError:
        st.error("❌ W pliku secrets brakuje klucza SUPABASE_URL lub SUPABASE_KEY.")
        st.stop()

supabase = init_connection()

# --- DEFINICJE NAZW TABEL (ZGODNIE Z OBRAZKIEM) ---
TABLE_PRODUCTS = "Produkty"   # Na obrazku z Wielkiej litery
TABLE_CATEGORIES = "kategorie" # Na obrazku z małej litery

st.title("📦 Menadżer Produktów i Kategorii")

# Tworzymy zakładki
tab1, tab2, tab3 = st.tabs(["➕ Dodaj Kategorię", "➕ Dodaj Produkt", "📋 Podgląd Bazy"])

# --- ZAKŁADKA 1: DODAWANIE KATEGORII ---
with tab1:
    st.header("Nowa Kategoria")
    with st.form("category_form", clear_on_submit=True):
        cat_nazwa = st.text_input("Nazwa kategorii (wymagane)")
        cat_opis = st.text_area("Opis kategorii (opcjonalne)")
        
        submitted_cat = st.form_submit_button("Zapisz kategorię")
        
        if submitted_cat:
            if not cat_nazwa:
                st.warning("⚠️ Nazwa kategorii jest wymagana!")
            else:
                try:
                    data = {"nazwa": cat_nazwa, "opis": cat_opis}
                    # Używamy zmiennej TABLE_CATEGORIES
                    supabase.table(TABLE_CATEGORIES).insert(data).execute()
                    st.success(f"✅ Dodano kategorię: {cat_nazwa}")
                except Exception as e:
                    st.error(f"Błąd bazy danych: {e}")

# --- ZAKŁADKA 2: DODAWANIE PRODUKTU ---
with tab2:
    st.header("Nowy Produkt")

    # Pobieranie kategorii do listy rozwijanej
    categories = []
    try:
        # Pobieramy id i nazwa z tabeli kategorie
        response = supabase.table(TABLE_CATEGORIES).select("id, nazwa").execute()
        categories = response.data
    except Exception as e:
        st.error(f"Nie udało się pobrać kategorii. Sprawdź czy tabela '{TABLE_CATEGORIES}' istnieje w Supabase.")
        st.write(f"Szczegóły błędu: {e}")

    if not categories:
        st.warning("👉 Najpierw dodaj przynajmniej jedną kategorię w pierwszej zakładce.")
    else:
        # Mapa: Nazwa -> ID
        cat_options = {cat['nazwa']: cat['id'] for cat in categories}

        with st.form("product_form", clear_on_submit=True):
            prod_nazwa = st.text_input("Nazwa produktu")
            col1, col2 = st.columns(2)
            with col1:
                prod_liczba = st.number_input("Liczba (sztuki)", min_value=0, step=1)
            with col2:
                prod_cena = st.number_input("Cena", min_value=0.0, step=0.01, format="%.2f")
            
            selected_cat_name = st.selectbox("Wybierz kategorię", options=list(cat_options.keys()))
            
            submitted_prod = st.form_submit_button("Zapisz produkt")
            
            if submitted_prod:
                if not prod_nazwa:
                    st.warning("⚠️ Nazwa produktu jest wymagana!")
                else:
                    try:
                        selected_cat_id = cat_options[selected_cat_name]
                        data = {
                            "nazwa": prod_nazwa,
                            "liczba": prod_liczba,
                            "cena": prod_cena,
                            "kategoria": selected_cat_id 
                        }
                        supabase.table(TABLE_PRODUCTS).insert(data).execute()
                        st.success(f"✅ Dodano produkt: {prod_nazwa}")
                    except Exception as e:
                        st.error(f"Błąd zapisu produktu: {e}")

# --- ZAKŁADKA 3: PODGLĄD (NAPRAWIONY) ---
with tab3:
    st.subheader("Aktualne stany magazynowe")
    if st.button("Odśwież dane"):
        try:
            # Próbujemy pobrać dane z połączeniem tabel (JOIN)
            # Jeśli relacja w Supabase nie jest ustawiona, to zapytanie wywali błąd.
            # Dlatego robimy try/except ze zwykłym pobraniem.
            
            try:
                # Próba 1: Pobierz z nazwą kategorii (wymaga ustawionego Foreign Key w Supabase)
                # Składnia: tabela_zrodlowa!kolumna_fk(pola_z_tabeli_obcej)
                query = f"*, {TABLE_CATEGORIES}(nazwa)"
                res = supabase.table(TABLE_PRODUCTS).select(query).execute()
                
                # Formatowanie danych do ładnej tabelki
                clean_data = []
                for item in res.data:
                    # Spłaszczamy strukturę (wyciągamy nazwę z zagnieżdżonego słownika)
                    cat_info = item.get(TABLE_CATEGORIES)
                    cat_name = cat_info['nazwa'] if cat_info else "Brak"
                    
                    clean_data.append({
                        "ID": item['id'],
                        "Produkt": item['nazwa'],
                        "Ilość": item['liczba'],
                        "Cena": item['cena'],
                        "Kategoria": cat_name
                    })
                st.dataframe(clean_data)
                
            except Exception:
                # Próba 2: Jeśli JOIN nie działa (np. brak relacji w Supabase), pobierz surowe dane
                st.warning("⚠️ Nie udało się pobrać nazw kategorii (sprawdź relacje Foreign Key w Supabase). Pokazuję surowe dane.")
                res = supabase.table(TABLE_PRODUCTS).select("*").execute()
                st.dataframe(res.data)

        except Exception as e:
            st.error(f"Wystąpił błąd ogólny: {e}")
