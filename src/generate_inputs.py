import os
import json
import pandas as pd

def generate_input_files():
    input_dir = 'input'
    os.makedirs(input_dir, exist_ok=True)

    # Load data
    df_orders = pd.read_csv('data/olist_orders_dataset.csv')
    df_items = pd.read_csv('data/olist_order_items_dataset.csv')
    df_payments = pd.read_csv('data/olist_order_payments_dataset.csv')
    df_customers = pd.read_csv('data/olist_customers_dataset.csv')
    df_products = pd.read_csv('data/olist_products_dataset.csv')

    # Merge customers to get customer_unique_id
    df_orders = df_orders.merge(df_customers[['customer_id', 'customer_unique_id']], on='customer_id', how='left')

    # Identify payment counts and sums
    pmt_stats = df_payments.groupby('order_id').agg(
        pmt_count=('payment_sequential', 'count'),
        total_pmt=('payment_value', 'sum')
    ).reset_index()
    df_orders = df_orders.merge(pmt_stats, on='order_id', how='left')

    # Merge items with products to get categories
    df_items_prod = df_items.merge(df_products[['product_id', 'product_category_name']], on='product_id', how='left')

    # Identify items stats
    items_stats = df_items_prod.groupby('order_id').agg(
        item_count=('order_item_id', 'count'),
        seller_count=('seller_id', lambda x: len(set(x))),
        cat_count=('product_category_name', lambda x: len(set(x.dropna()))),
        min_shipping_limit=('shipping_limit_date', 'min')
    ).reset_index()
    df_orders = df_orders.merge(items_stats, on='order_id', how='left')

    # Identify customer repeat orders count
    cust_orders_count = df_orders.groupby('customer_unique_id')['order_id'].transform('count')
    df_orders['is_repeat'] = cust_orders_count > 1

    # Calculate delivery variances on df_orders
    df_orders['is_late'] = df_orders['order_delivered_customer_date'] > df_orders['order_estimated_delivery_date']
    df_orders['seller_late'] = df_orders['order_delivered_carrier_date'] > df_orders['min_shipping_limit']

    selected_orders = []

    # Helper to add orders without duplicates
    def add_orders(candidates, limit):
        added = 0
        for oid in candidates:
            if oid not in selected_orders and pd.notna(oid):
                selected_orders.append(oid)
                added += 1
                if added >= limit:
                    break

    # 1. Canceled with payment > 0 (5 orders)
    canceled = df_orders[(df_orders['order_status'] == 'canceled') & (df_orders['total_pmt'] > 0)]['order_id'].tolist()
    add_orders(canceled, 5)

    # 2. Unavailable with payment > 0 (5 orders)
    unavailable = df_orders[(df_orders['order_status'] == 'unavailable') & (df_orders['total_pmt'] > 0)]['order_id'].tolist()
    add_orders(unavailable, 5)

    # 3. Multi-seller orders (5 orders)
    multi_seller = df_orders[(df_orders['seller_count'] >= 2) & (df_orders['order_status'] == 'delivered')]['order_id'].tolist()
    add_orders(multi_seller, 5)

    # 4. Multi-category orders (5 orders)
    multi_cat = df_orders[(df_orders['cat_count'] >= 2) & (df_orders['order_status'] == 'delivered')]['order_id'].tolist()
    add_orders(multi_cat, 5)

    # 5. Repeat customer orders (5 orders)
    repeat_cust = df_orders[df_orders['is_repeat'] & (df_orders['order_status'] == 'delivered')]['order_id'].tolist()
    add_orders(repeat_cust, 5)

    # 6. Late delivery seller (8 orders)
    late_seller = df_orders[(df_orders['order_status'] == 'delivered') & (df_orders['is_late']) & (df_orders['seller_late'])]['order_id'].tolist()
    add_orders(late_seller, 8)

    # 7. Late delivery logistics (8 orders)
    late_logistics = df_orders[(df_orders['order_status'] == 'delivered') & (df_orders['is_late']) & (~df_orders['seller_late'])]['order_id'].tolist()
    add_orders(late_logistics, 8)

    # 8. Split payment valid (5 orders)
    split_pmt = df_orders[(df_orders['pmt_count'] >= 2) & (df_orders['order_status'] == 'delivered')]['order_id'].tolist()
    add_orders(split_pmt, 5)

    # 9. Fill remaining up to 50 with regular delivered on-time orders
    regular = df_orders[(df_orders['order_status'] == 'delivered') & (~df_orders['is_late'])]['order_id'].tolist()
    remaining = 50 - len(selected_orders)
    if remaining > 0:
        add_orders(regular, remaining)

    print(f"Total selected orders: {len(selected_orders)}")

    for idx, order_id in enumerate(selected_orders, 1):
        case_id = f"EC_{idx:03d}"
        case_data = {
            "case_id": case_id,
            "customer_request": {
                "language": "vi",
                "message": "Hãy điều tra khiếu nại, kiểm tra lịch sử khách hàng và đối soát toàn bộ order.",
                "claimed_order_id": order_id
            },
            "investigation_scope": {
                "include_customer_history": True,
                "include_product_context": True
            },
            "policy_version": "EC_POLICY_V2"
        }
        file_path = os.path.join(input_dir, f"{case_id}.json")
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(case_data, f, ensure_ascii=False, indent=2)

    print(f"Generated {len(selected_orders)} input files in '{input_dir}/'")

if __name__ == '__main__':
    generate_input_files()
