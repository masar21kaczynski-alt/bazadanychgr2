import streamlit as st
from supabase import create_client, Client

# 1. Konfiguracja połączenia z Supabase
# Pobieramy dane z sekretów Streamlit (bezpieczny sposób)
try:
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_KEY"]
    supabase: Client = create_client(url, key)
except Exception as e:
    st.error("Błąd konfiguracji: Upewnij się, że zdefiniowałeś sekrety SUPABASE_URL i SUPABASE_KEY.")
    st.stop()

st.title("📦 Menadżer Produktów i Kategorii")

# Tworzymy zakładki dla lepszej czytelności
tab1, tab2 = st.tabs(["Dodaj Kategorię", "Dodaj Produkt"])

# --- ZAKŁADKA 1: DODAWANIE KATEGORII ---
with tab1:
    st.header("Nowa Kategoria")
    
    with st.form("category_form", clear_on_submit=True):
        cat_nazwa = st.text_input("Nazwa kategorii (wymagane)")
        cat_opis = st.text_area("Opis kategorii (opcjonalne)")
        
        submitted_cat = st.form_submit_button("Zapisz kategorię")
        
        if submitted_cat:
            if not cat_nazwa:
                st.warning("Nazwa kategorii jest wymagana!")
            else:
                try:
                    data = {
                        "nazwa": cat_nazwa,
                        "opis": cat_opis
                    }
                    supabase.table("Kategorie").insert(data).execute()
                    st.success(f"Dodano kategorię: {cat_nazwa}")
                except Exception as e:
                    st.error(f"Wystąpił błąd: {e}")

# --- ZAKŁADKA 2: DODAWANIE PRODUKTU ---
with tab2:
    st.header("Nowy Produkt")

    # Najpierw musimy pobrać listę kategorii, aby wypełnić listę rozwijaną (Foreign Key)
    try:
        response = supabase.table("Kategorie").select("id, nazwa").execute()
        categories = response.data
    except Exception as e:
        st.error("Nie udało się pobrać kategorii.")
        categories = []

    # Jeśli nie ma kategorii, blokujemy dodawanie produktów
    if not categories:
        st.warning("Najpierw dodaj przynajmniej jedną kategorię w zakładce obok!")
    else:
        # Tworzymy słownik { "Nazwa Kategorii": ID_Kategorii } dla łatwego wyboru
        cat_options = {cat['nazwa']: cat['id'] for cat in categories}

        with st.form("product_form", clear_on_submit=True):
            prod_nazwa = st.text_input("Nazwa produktu (wymagane)")
            
            # Kolumny dla lepszego układu liczb
            col1, col2 = st.columns(2)
            with col1:
                prod_liczba = st.number_input("Liczba (sztuki)", min_value=0, step=1)
            with col2:
                prod_cena = st.number_input("Cena", min_value=0.0, step=0.01, format="%.2f")
            
            # Wybór kategorii
            selected_cat_name = st.selectbox("Wybierz kategorię", options=cat_options.keys())
            
            submitted_prod = st.form_submit_button("Zapisz produkt")
            
            if submitted_prod:
                if not prod_nazwa:
                    st.warning("Nazwa produktu jest wymagana!")
                else:
                    try:
                        # Pobieramy ID na podstawie wybranej nazwy
                        selected_cat_id = cat_options[selected_cat_name]
                        
                        data = {
                            "nazwa": prod_nazwa,
                            "liczba": prod_liczba,
                            "cena": prod_cena,
                            "kategoria": selected_cat_id  # To jest relacja do tabeli Kategorie
                        }
                        
                        supabase.table("Produkty").insert(data).execute()
                        st.success(f"Dodano produkt: {prod_nazwa}")
                    except Exception as e:
                        st.error(f"Wystąpił błąd podczas dodawania produktu: {e}")

# --- OPCJONALNIE: PODGLĄD DANYCH ---
st.divider()
st.subheader("Podgląd bazy danych")
if st.checkbox("Pokaż aktualne produkty"):
    # Pobieramy produkty wraz z nazwą kategorii (tzw. join)
    try:
        # Składnia: tabela_zrodlowa!relacja (wybieramy kolumny)
        # Zakładam, że relacja w Supabase nazywa się standardowo. 
        # Jeśli select nie zadziała z relacją, pobierzemy surowe dane.
        res = supabase.table("Produkty").select("*, Kategorie(nazwa)").execute()
        st.dataframe(res.data)
    except Exception as e:
        st.write("Błąd pobierania podglądu:", e)
