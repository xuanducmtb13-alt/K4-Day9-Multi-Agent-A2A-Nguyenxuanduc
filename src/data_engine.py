import os
import pandas as pd
from datetime import datetime

class DataEngine:
    def __init__(self, data_dir='data'):
        self.data_dir = data_dir
        self.load_datasets()

    def load_datasets(self):
        print("Loading Olist datasets...")
        self.df_orders = pd.read_csv(os.path.join(self.data_dir, 'olist_orders_dataset.csv'))
        self.df_items = pd.read_csv(os.path.join(self.data_dir, 'olist_order_items_dataset.csv'))
        self.df_payments = pd.read_csv(os.path.join(self.data_dir, 'olist_order_payments_dataset.csv'))
        self.df_customers = pd.read_csv(os.path.join(self.data_dir, 'olist_customers_dataset.csv'))
        self.df_sellers = pd.read_csv(os.path.join(self.data_dir, 'olist_sellers_dataset.csv'))
        self.df_products = pd.read_csv(os.path.join(self.data_dir, 'olist_products_dataset.csv'))
        self.df_translation = pd.read_csv(os.path.join(self.data_dir, 'product_category_name_translation.csv'))

        # Map category translations
        cat_map = dict(zip(self.df_translation['product_category_name'], self.df_translation['product_category_name_english']))
        self.df_products['category_english'] = self.df_products['product_category_name'].map(cat_map).fillna(self.df_products['product_category_name'])

        # Pre-index tables by order_id and customer_id for fast lookup
        self.orders_by_id = self.df_orders.set_index('order_id').to_dict('index')
        self.customers_by_id = self.df_customers.set_index('customer_id').to_dict('index')
        
        # Group items by order_id (sorted by order_item_id)
        self.items_by_order = {}
        for row in self.df_items.sort_values(['order_id', 'order_item_id']).to_dict('records'):
            oid = row['order_id']
            self.items_by_order.setdefault(oid, []).append(row)

        # Group payments by order_id (sorted by payment_sequential)
        self.payments_by_order = {}
        for row in self.df_payments.sort_values(['order_id', 'payment_sequential']).to_dict('records'):
            oid = row['order_id']
            self.payments_by_order.setdefault(oid, []).append(row)

        # Map products by product_id
        self.products_by_id = self.df_products.set_index('product_id').to_dict('index')

        # Map customer_unique_id to related order_ids (preserving order_purchase_timestamp order)
        self.orders_by_unique_cust = {}
        cust_map = self.df_customers.set_index('customer_id')['customer_unique_id'].to_dict()
        for oid, o_row in self.orders_by_id.items():
            cid = o_row['customer_id']
            uniq_id = cust_map.get(cid)
            if uniq_id:
                self.orders_by_unique_cust.setdefault(uniq_id, []).append(oid)

        print("Datasets loaded successfully.")

    def get_order_context(self, claimed_order_id):
        order_info = self.orders_by_id.get(claimed_order_id)
        if not order_info:
            return None

        customer_id = order_info['customer_id']
        cust_info = self.customers_by_id.get(customer_id, {})
        cust_unique_id = cust_info.get('customer_unique_id')

        # Related orders for repeat customer (excluding current order)
        all_cust_orders = self.orders_by_unique_cust.get(cust_unique_id, [])
        related_order_ids = [oid for oid in all_cust_orders if oid != claimed_order_id]

        # Items
        items = self.items_by_order.get(claimed_order_id, [])
        item_ids = [f"{claimed_order_id}:{it['order_item_id']}" for it in items]
        seller_ids = list(dict.fromkeys([it['seller_id'] for it in items]))

        # Products and categories
        product_ids = list(dict.fromkeys([it['product_id'] for it in items]))
        category_names = []
        for pid in product_ids:
            p_info = self.products_by_id.get(pid, {})
            cat = p_info.get('category_english')
            if cat and pd.notna(cat) and str(cat).lower() != 'nan' and cat not in category_names:
                category_names.append(cat)

        # Payments
        payments = self.payments_by_order.get(claimed_order_id, [])
        payment_ids = [f"{claimed_order_id}:{pmt['payment_sequential']}" for pmt in payments]
        payment_types = list(dict.fromkeys([pmt['payment_type'] for pmt in payments]))

        # Calculate Delivery Variance
        delivered_at = order_info.get('order_delivered_customer_date')
        estimated_delivery_at = order_info.get('order_estimated_delivery_date')
        carrier_handoff_at = order_info.get('order_delivered_carrier_date')

        delivery_variance_hours = None
        if pd.notna(delivered_at) and pd.notna(estimated_delivery_at):
            dt_del = datetime.strptime(str(delivered_at), "%Y-%m-%d %H:%M:%S")
            dt_est = datetime.strptime(str(estimated_delivery_at), "%Y-%m-%d %H:%M:%S")
            delivery_variance_hours = round((dt_del - dt_est).total_seconds() / 3600.0, 2)

        # Seller Handoff Analysis
        seller_handoff_analysis = []
        late_handoff_seller_ids = []
        
        # Group items by seller to get min shipping limit date per seller
        seller_shipping_limits = {}
        for it in items:
            s_id = it['seller_id']
            limit_date = it['shipping_limit_date']
            if s_id not in seller_shipping_limits or (pd.notna(limit_date) and limit_date < seller_shipping_limits[s_id]):
                seller_shipping_limits[s_id] = limit_date

        for s_id, limit_date in seller_shipping_limits.items():
            h_variance = None
            is_late = False
            if pd.notna(carrier_handoff_at) and pd.notna(limit_date):
                dt_carrier = datetime.strptime(str(carrier_handoff_at), "%Y-%m-%d %H:%M:%S")
                dt_limit = datetime.strptime(str(limit_date), "%Y-%m-%d %H:%M:%S")
                h_variance = round((dt_carrier - dt_limit).total_seconds() / 3600.0, 2)
                is_late = h_variance > 0

            if is_late:
                late_handoff_seller_ids.append(s_id)

            seller_handoff_analysis.append({
                "seller_id": s_id,
                "shipping_limit_at": str(limit_date) if pd.notna(limit_date) else None,
                "handoff_variance_hours": h_variance,
                "late_handoff": is_late
            })

        # Payment Reconciliation
        item_total_brl = round(sum(it['price'] for it in items), 2)
        freight_total_brl = round(sum(it['freight_value'] for it in items), 2)
        payment_total_brl = round(sum(pmt['payment_value'] for pmt in payments), 2)

        if len(items) == 0:
            expected_total_brl = None
            difference_brl = None
            reconciled = None
        else:
            expected_total_brl = round(item_total_brl + freight_total_brl, 2)
            difference_brl = round(payment_total_brl - expected_total_brl, 2)
            reconciled = abs(difference_brl) <= 0.10

        return {
            "order_id": claimed_order_id,
            "order_status": order_info.get('order_status'),
            "customer_unique_id": cust_unique_id,
            "related_order_ids": related_order_ids,
            "items": items,
            "item_ids": item_ids,
            "seller_ids": seller_ids,
            "product_ids": product_ids,
            "category_names": category_names,
            "payments": payments,
            "payment_ids": payment_ids,
            "payment_types": payment_types,
            "delivered_at": str(delivered_at) if pd.notna(delivered_at) else None,
            "estimated_delivery_at": str(estimated_delivery_at) if pd.notna(estimated_delivery_at) else None,
            "carrier_handoff_at": str(carrier_handoff_at) if pd.notna(carrier_handoff_at) else None,
            "delivery_variance_hours": delivery_variance_hours,
            "seller_handoff_analysis": seller_handoff_analysis,
            "late_handoff_seller_ids": late_handoff_seller_ids,
            "item_total_brl": item_total_brl,
            "freight_total_brl": freight_total_brl,
            "expected_total_brl": expected_total_brl,
            "payment_total_brl": payment_total_brl,
            "difference_brl": difference_brl,
            "reconciled": reconciled
        }
