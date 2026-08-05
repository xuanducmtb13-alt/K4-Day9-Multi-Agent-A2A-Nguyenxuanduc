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

    # Merge customers to get customer_unique_id
    df_orders = df_orders.merge(df_customers[['customer_id', 'customer_unique_id']], on='customer_id', how='left')

    # Identify payment counts and sums
    pmt_stats = df_payments.groupby('order_id').agg(
        pmt_count=('payment_sequential', 'count'),
        total_pmt=('payment_value', 'sum')
    ).reset_index()
    df_orders = df_orders.merge(pmt_stats, on='order_id', how='left')

    # Identify items stats
    items_stats = df_items.groupby('order_id').agg(
        item_count=('order_item_id', 'count'),
        seller_count=('seller_id', lambda x: len(set(x))),
        min_shipping_limit=('shipping_limit_date', 'min'),
        total_item_val=('price', 'sum'),
        total_freight=('freight_value', 'sum')
    ).reset_index()
    df_orders = df_orders.merge(items_stats, on='order_id', how='left')

    selected_orders = []

    # 1. Canceled with payment > 0 (5 orders)
    canceled = df_orders[(df_orders['order_status'] == 'canceled') & (df_orders['total_pmt'] > 0)]['order_id'].dropna().tolist()
    selected_orders.extend(canceled[:5])

    # 2. Unavailable with payment > 0 (5 orders)
    unavailable = df_orders[(df_orders['order_status'] == 'unavailable') & (df_orders['total_pmt'] > 0)]['order_id'].dropna().tolist()
    selected_orders.extend(unavailable[:5])

    # Calculate delivery variances on df_orders
    df_orders['is_late'] = df_orders['order_delivered_customer_date'] > df_orders['order_estimated_delivery_date']
    df_orders['seller_late'] = df_orders['order_delivered_carrier_date'] > df_orders['min_shipping_limit']

    # 3. Late delivery seller (10 orders)
    late_seller = df_orders[(df_orders['order_status'] == 'delivered') & (df_orders['is_late']) & (df_orders['seller_late'])]['order_id'].dropna().tolist()
    selected_orders.extend(late_seller[:10])

    # 4. Late delivery logistics (10 orders)
    late_logistics = df_orders[(df_orders['order_status'] == 'delivered') & (df_orders['is_late']) & (~df_orders['seller_late'])]['order_id'].dropna().tolist()
    selected_orders.extend(late_logistics[:10])

    # 5. Split payment valid (10 orders)
    split_pmt = df_orders[(df_orders['pmt_count'] >= 2) & (df_orders['order_status'] == 'delivered') & (~df_orders['order_id'].isin(selected_orders))]['order_id'].dropna().tolist()
    selected_orders.extend(split_pmt[:10])

    # 6. Regular on-time / unsupported late claim (fill up to 50)
    remaining_needed = 50 - len(selected_orders)
    regular = df_orders[(df_orders['order_status'] == 'delivered') & (~df_orders['is_late']) & (~df_orders['order_id'].isin(selected_orders))]['order_id'].dropna().tolist()
    selected_orders.extend(regular[:remaining_needed])

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

    print(f"Generated 50 input files in '{input_dir}/'")

if __name__ == '__main__':
    generate_input_files()
