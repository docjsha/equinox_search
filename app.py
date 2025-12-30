import streamlit as st
import requests
from collections import Counter
import pandas as pd

# Add custom CSS to hide the GitHub icon
# st.markdown(
#     """
#     <style>
#     .css-1jc7ptx, .e1ewe7hr3, .viewerBadge_container__1QSob,
#     .styles_viewerBadge__1yB5_, .viewerBadge_link__1S137,
#     .viewerBadge_text__1JaDK {
#         display: none;
#     }
#     </style>
#     """,
#     unsafe_allow_html=True
# )

# st.set_page_config(page_title="Equinox Quick Search", layout="wide")

@st.cache_data(show_spinner="Fetching products...")
def fetch_shopify_products(base_url):
    """
    Fetches products from a Shopify store's public JSON API.
    Handles pagination to retrieve all products (max 250 per page).
    """
    # Ensure URL ends with /products.json
    clean_url = base_url.rstrip('/')
    if not clean_url.endswith('products.json'):
        base_api_url = f"{clean_url}/products.json"
    else:
        base_api_url = clean_url
    
    all_products = []
    page = 1
    
    while True:
        try:
            # Fetch products for current page
            params = {'limit': 250, 'page': page}
            response = requests.get(base_api_url, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()
            products = data.get('products', [])
            
            # If no products returned, we've reached the end
            if not products:
                break
            
            all_products.extend(products)
            page += 1
            
        except requests.exceptions.RequestException as e:
            st.error(f"Error fetching data on page {page}: {e}")
            break
        except ValueError:
            st.error("Invalid JSON response. Is this a Shopify site?")
            break
    
    return all_products

# UI
st.markdown("<h3>Equinox Quick Search</h3>", unsafe_allow_html=True)
URL = 'http://shop.equinox.com'
products = fetch_shopify_products(URL)

vendors = [k for k, _ in Counter([p['vendor'] for p in products]).most_common()]
selected_vendor = st.selectbox("Select a vendor", vendors)
filtered_products = [p for p in products if p['vendor'] == selected_vendor]

selected_gender = st.selectbox("Select a gender", ["Women", "Men"])
filtered_products = [p for p in filtered_products if selected_gender in p['title']]

product_types = [k for k, _ in Counter([p['product_type'] for p in filtered_products]).most_common()]
selected_product_type = st.selectbox("Select a product type", product_types)
filtered_products = [p for p in filtered_products if p['product_type'] == selected_product_type]

sizes = sorted(set(i['option2'] for p in filtered_products for i in p['variants']))
# selected_size = st.selectbox("Select a size", sizes)
# filtered_products = [p for p in filtered_products if any(i['option1'] == selected_size for i in p['variants'])]
selected_sizes = st.multiselect("Select sizes", sizes)
if selected_sizes:
    filtered_products = [p for p in filtered_products if any(i['available'] and i['option2'] in selected_sizes for i in p['variants'])]

st.write(f"Found {len(filtered_products)} matched products.")

df_display = []
for product in filtered_products:
    product_available_sizes = [i['option2'] for i in product['variants'] if i['available']]
    if selected_sizes:
        matched_sizes = [s for s in product_available_sizes if s in selected_sizes]
    else:
        matched_sizes = product_available_sizes
    df_display.append({
        'Title': product['title'],
        'Url': f'{URL}/products/{product['handle']}',
        'Matched Sizes': matched_sizes,
        'Available Sizes': product_available_sizes,
        'Price': product['variants'][0]['price'] if product['variants'] else None,
        # 'Description': product['body_html'],
        # 'Images': product['images']
    })
df_display = pd.DataFrame(df_display)
st.markdown(df_display.to_html(render_links=True), unsafe_allow_html=True)
