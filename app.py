from collections import Counter
import pandas as pd
import requests
import streamlit as st

st.set_page_config(page_title="Equinox Shop Search", layout="wide")


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

def main():
    st.markdown("<h3>Equinox Shop Search</h3>", unsafe_allow_html=True)
    # Initialize session state
    if 'initialized' not in st.session_state:
        st.session_state.initialized = True
        st.cache_data.clear()  # Clear on first load only
    URL = 'http://shop.equinox.com'
    products = fetch_shopify_products(URL)

    vendors = [k for k, _ in Counter([p['vendor'] for p in products]).most_common()]
    selected_vendor = st.selectbox("Select a vendor", vendors)
    filtered_products = [p for p in products if p['vendor'] == selected_vendor]

    selected_gender = st.selectbox("Select a gender (optional)", ["", "Women", "Men"], index=0)
    filtered_products = [p for p in filtered_products if selected_gender in p['title']]

    product_types = [k for k, _ in Counter([p['product_type'] for p in filtered_products]).most_common()]
    selected_product_type = st.selectbox("Select a product type", product_types)
    filtered_products = [p for p in filtered_products if p['product_type'] == selected_product_type]

    sizes = sorted(set(i['option2'] for p in filtered_products for i in p['variants']))

    # Determine default sizes based on vendor
    default_opts = ['6', '6.5'] if selected_vendor == 'On' else []
    # Ensure defaults are valid options
    valid_defaults = [s for s in default_opts if s in sizes]

    selected_sizes = st.multiselect("Select sizes", sizes, default=valid_defaults, key=f"size_{selected_vendor}")

    # Only filter products if specific sizes are selected
    if selected_sizes:
        filtered_products = [p for p in filtered_products if any(i['available'] and i['option2'] in selected_sizes for i in p['variants'])]

    num_filtered_products = len(filtered_products)
    st.write(f"Found {num_filtered_products} matched products.")

    if num_filtered_products > 0:
        df_display = []
        for product in filtered_products:
            product_available_sizes = [i['option2'] for i in product['variants'] if i['available']]
            if selected_sizes:
                matched_sizes = [s for s in product_available_sizes if s in selected_sizes]
            else:
                matched_sizes = product_available_sizes
            df_display.append({
                'Title': product['title'],
                'Url': f'<a href="{URL}/products/{product["handle"]}" target="_blank">Link</a>',
                'Matched Sizes': matched_sizes,
                'Available Sizes': product_available_sizes,
                'Option': product['variants'][0]['option1'] if product['variants'] else None,
                'Price': product['variants'][0]['price'] if product['variants'] else None,
                # 'Description': product['body_html'],
                # 'Images': product['images']
            })
        df_display = pd.DataFrame(df_display)
        
        # Extract actual URLs from HTML links
        df_display['Url'] = df_display['Url'].str.extract(r'href="([^"]+)"')[0]
        
        # Calculate height to show all rows without extra space
        num_rows = len(df_display)
        row_height = 35  # Approximate height per row in pixels
        header_height = 35  # Height for table header
        table_height = (num_rows * row_height) + header_height
        
        # Display using Streamlit's data_editor with pinned first column
        st.data_editor(
            df_display,
            width='content',  # Fit to content width, no extra space
            height=table_height,  # Dynamic height to show all rows without extra space
            disabled=True,  # Make it read-only
            column_config={
                "Title": st.column_config.Column(
                    "Title",
                    pinned=True  # Pin the first column
                ),
                "Url": st.column_config.LinkColumn(
                    "Link",
                    display_text="Url"
                ),
                "Matched Sizes": st.column_config.ListColumn(
                    "Matched Sizes"
                ),
                "Available Sizes": st.column_config.ListColumn(
                    "Available Sizes"
                ),
                "Price": st.column_config.NumberColumn(
                    "Price",
                    format="$%.2f"
                )
            },
            hide_index=True
        )


if __name__ == "__main__":
    main()
