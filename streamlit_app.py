import streamlit as st
from supabase import create_client, Client
import time

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
        st.error("❌ Brak pliku `.streamlit/secrets.toml`! Utwórz go i dodaj tam URL oraz KEY.")
        st.stop()
    except KeyError:
        st.error("❌ W pliku secrets brakuje klucza SUPABASE_URL lub SUPABASE_KEY.")
        st.stop()

supabase = init_connection()

# --- DEFINICJE NAZW TABEL ---
TABLE_PRODUCTS = "Produkty"   # Zgodnie z Twoim obrazkiem (duża litera)
TABLE_CATEGORIES = "kategorie" # Zgodnie z Twoim obrazkiem (mała litera)

st.title("📦 Menadżer Produktów i Kategorii")

# Tworzymy 4 zakładki (dodano nową: Wydanie z Magazynu)
tab1, tab2, tab3, tab4 = st.tabs(["➕ Dodaj Kategorię", "➕ Dodaj Produkt", "📉 Wydanie z Magazynu", "📋 Podgląd Bazy"])

# ==========================================
# ZAKŁADKA 1: DODAWANIE KATEGORII
# ==========================================
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
                    supabase.table(TABLE_CATEGORIES).insert(data).execute()
                    st.success(f"✅ Dodano kategorię: {cat_nazwa}")
                    time.sleep(1)
                    st.rerun() # Odśwież, aby zaktualizować listy w innych zakładkach
                except Exception as e:
                    st.error(f"Błąd bazy danych: {e}")

# ==========================================
# ZAKŁADKA 2: DODAWANIE PRODUKTU
# ==========================================
with tab2:
    st.header("Nowy Produkt")

    # Pobieranie kategorii
    categories = []
    try:
        response = supabase.table(TABLE_CATEGORIES).select("id, nazwa").execute()
        categories = response.data
    except Exception as e:
        st.error(f"Nie udało się pobrać kategorii: {e}")

    if not categories:
        st.warning("👉 Najpierw dodaj kategorię w pierwszej zakładce.")
    else:
        cat_options = {cat['nazwa']: cat['id'] for cat in categories}

        with st.form("product_form", clear_on_submit=True):
            prod_nazwa = st.text_input("Nazwa produktu")
            col1, col2 = st.columns(2)
            with col1:
                prod_liczba = st.number_input("Liczba początkowa (sztuki)", min_value=0, step=1)
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
                        time.sleep(1)
                        st.rerun()
                    except Exception as e:
                        st.error(f"Błąd zapisu: {e}")

# ==========================================
# ZAKŁADKA 3: WYDANIE TOWARU (NOWOŚĆ)
# ==========================================
with tab3:
    st.header("📉 Zmniejsz stan magazynowy")
    
    # 1. Pobieramy listę produktów z aktualnym stanem
    try:
        res_prod = supabase.table(TABLE_PRODUCTS).select("id, nazwa, liczba").execute()
        products_list = res_prod.data
    except Exception as e:
        st.error("Błąd pobierania produktów.")
        products_list = []

    if not products_list:
        st.info("Brak produktów w bazie.")
    else:
        # Tworzymy mapę { "Nazwa (x szt.)": cały_obiekt_produktu }
        # Dzięki temu w liście rozwijanej widzimy od razu ile jest sztuk
        prod_options = {f"{p['nazwa']} (Stan: {p['liczba']} szt.)": p for p in products_list}
        
        selected_option = st.selectbox("Wybierz produkt do wydania", options=list(prod_options.keys()))
        
        # Pobieramy wybrany produkt
        selected_product = prod_options[selected_option]
        current_stock = selected_product['liczba']
        product_id = selected_product['id']

        st.write(f"Wybrano: **{selected_product['nazwa']}**")
        st.write(f"Aktualny stan: **{current_stock}**")

        with st.form("stock_update_form"):
            remove_amount = st.number_input("Ile sztuk wydać?", min_value=1, step=1)
            submit_update = st.form_submit_button("Zatwierdź wydanie")

            if submit_update:
                if remove_amount > current_stock:
                    st.error(f"❌ Nie możesz wydać {remove_amount} szt., bo na stanie jest tylko {current_stock}!")
                else:
                    try:
                        new_stock = current_stock - remove_amount
                        # Aktualizacja w bazie
                        supabase.table(TABLE_PRODUCTS).update({"liczba": new_stock}).eq("id", product_id).execute()
                        
                        st.success(f"✅ Wydano {remove_amount} szt. Nowy stan: {new_stock}")
                        time.sleep(1)
                        st.rerun() # Odświeżamy stronę
                    except Exception as e:
                        st.error(f"Błąd aktualizacji: {e}")

# ==========================================
# ZAKŁADKA 4: PODGLĄD BAZY
# ==========================================
with tab4:
    st.subheader("Aktualne stany magazynowe")
    if st.button("Odśwież tabelę"):
        st.rerun()

    try:
        # Próbujemy JOIN (wymaga Foreign Key w Supabase)
        try:
            query = f"*, {TABLE_CATEGORIES}(nazwa)"
            res = supabase.table(TABLE_PRODUCTS).select(query).order('id').execute()
            
            clean_data = []
            for item in res.data:
                cat_info = item.get(TABLE_CATEGORIES)
                cat_name = cat_info['nazwa'] if cat_info else "---"
                
                clean_data.append({
                    "ID": item['id'],
                    "Produkt": item['nazwa'],
                    "Ilość": item['liczba'],
                    "Cena": f"{item['cena']} PLN",
                    "Kategoria": cat_name
                })
            st.dataframe(clean_data, use_container_width=True)
            
        except Exception:
            # Fallback (gdy brak relacji FK)
            st.warning("⚠️ Pokazuję surowe dane (brak relacji FK w bazie).")
            res = supabase.table(TABLE_PRODUCTS).select("*").order('id').execute()
            st.dataframe(res.data, use_container_width=True)

    except Exception as e:
        st.error(f"Wystąpił błąd ogólny: {e}")
