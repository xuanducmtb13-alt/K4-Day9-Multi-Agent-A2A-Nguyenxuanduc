import math

class PolicyEngine:
    def evaluate(self, ctx):
        order_status = ctx['order_status']
        payment_total = ctx['payment_total_brl']
        del_var = ctx['delivery_variance_hours']
        late_sellers = ctx['late_handoff_seller_ids']
        reconciled = ctx['reconciled']
        payments = ctx['payments']
        items = ctx['items']
        seller_ids = ctx['seller_ids']
        related_orders = ctx['related_order_ids']
        category_names = ctx['category_names']

        primary_issue = None
        responsible_parties = []
        recommended_refund = 0.0
        primary_action = None
        root_cause_code = None

        # 1. Canceled order paid
        if order_status == 'canceled' and payment_total > 0:
            primary_issue = 'canceled_order_paid'
            responsible_parties = [{"party_type": "platform", "party_id": "OLIST_PLATFORM"}]
            if len(seller_ids) > 0:
                for s_id in seller_ids[:2]:
                    responsible_parties.append({"party_type": "seller", "party_id": s_id})
            recommended_refund = payment_total
            primary_action = 'issue_full_refund'
            root_cause_code = 'ORDER_CANCELED_AFTER_PAYMENT'

        # 2. Unavailable order paid
        elif order_status == 'unavailable' and payment_total > 0:
            primary_issue = 'unavailable_order_paid'
            responsible_parties = [{"party_type": "platform", "party_id": "OLIST_PLATFORM"}]
            if len(seller_ids) > 0:
                for s_id in seller_ids[:2]:
                    responsible_parties.append({"party_type": "seller", "party_id": s_id})
            recommended_refund = payment_total
            primary_action = 'issue_full_refund'
            root_cause_code = 'ORDER_UNAVAILABLE_AFTER_PAYMENT'

        # 3. Late delivery seller
        elif del_var is not None and del_var > 0 and len(late_sellers) > 0:
            primary_issue = 'late_delivery_seller'
            responsible_parties = [{"party_type": "seller", "party_id": s_id} for s_id in late_sellers]
            recommended_refund = ctx['freight_total_brl']
            primary_action = 'refund_freight'
            root_cause_code = 'SELLER_HANDOFF_AFTER_LIMIT'

        # 4. Late delivery logistics
        elif del_var is not None and del_var > 0 and len(late_sellers) == 0:
            primary_issue = 'late_delivery_logistics'
            responsible_parties = [{"party_type": "logistics_provider", "party_id": "LOGISTICS_PROVIDER"}]
            recommended_refund = ctx['freight_total_brl']
            primary_action = 'refund_freight'
            root_cause_code = 'CARRIER_DELIVERED_AFTER_ESTIMATE'

        # 5. Valid split payment
        elif len(payments) >= 2 and reconciled is True:
            primary_issue = 'valid_split_payment'
            responsible_parties = []
            recommended_refund = 0.0
            primary_action = 'explain_valid_split_payment'
            root_cause_code = 'MULTIPLE_PAYMENTS_RECONCILED'

        # 6. Unsupported late claim / Default
        else:
            primary_issue = 'unsupported_late_claim'
            responsible_parties = []
            recommended_refund = 0.0
            primary_action = 'reject_late_refund'
            root_cause_code = 'DELIVERY_WITHIN_ESTIMATE'

        recommended_refund = round(recommended_refund, 2)
        case_status = "action_required" if recommended_refund > 0 else "no_action"

        # Evaluate secondary issues in exact order
        secondary_issues = []
        if len(items) >= 2:
            secondary_issues.append('multi_item_order')
        if len(seller_ids) >= 2:
            secondary_issues.append('multi_seller_order')
        if len(payments) >= 2:
            secondary_issues.append('split_payment')
        if len(related_orders) > 0:
            secondary_issues.append('repeat_customer')
        if len(category_names) >= 2:
            secondary_issues.append('multiple_categories')

        # Additional actions
        resolution_actions = [primary_action]
        if len(late_sellers) > 0:
            resolution_actions.append('review_seller_handoff')
        elif del_var is not None and del_var > 0:
            resolution_actions.append('review_carrier_delay')

        if recommended_refund > 0:
            resolution_actions.append('verify_refund_completion')
        if 'multi_seller_order' in secondary_issues:
            resolution_actions.append('coordinate_multi_seller_case')
        if 'split_payment' in secondary_issues and primary_issue != 'valid_split_payment':
            resolution_actions.append('verify_payment_allocation')

        # Evidence IDs (Only responsible sellers if any)
        oid = ctx['order_id']
        evidence_ids = [f"order:{oid}"]
        for it_id in ctx['item_ids']:
            evidence_ids.append(f"item:{it_id}")
        for pmt_id in ctx['payment_ids']:
            evidence_ids.append(f"payment:{pmt_id}")
        for rp in responsible_parties:
            if rp['party_type'] == 'seller':
                evidence_ids.append(f"seller:{rp['party_id']}")
        if root_cause_code:
            evidence_ids.append(f"policy:{root_cause_code}")

        # Dynamic confidence calculation aligned with policy precision
        if primary_issue in ['canceled_order_paid', 'unavailable_order_paid']:
            confidence = 0.99
        elif primary_issue == 'late_delivery_seller':
            confidence = 0.97
        elif primary_issue == 'late_delivery_logistics':
            confidence = 0.94
        elif primary_issue == 'valid_split_payment':
            confidence = 0.93
        elif primary_issue == 'unsupported_late_claim':
            confidence = 0.85
        else:
            confidence = 0.90

        # Assemble Output Schema according to strict rules
        output_schema = {
            "case_id": ctx.get('case_id', 'EC_001'),
            "case_assessment": {
                "primary_issue": primary_issue,
                "secondary_issues": secondary_issues,
                "case_status": case_status,
                "confidence": confidence
            },
            "affected_entities": {
                "order_ids": [oid],
                "item_ids": ctx['item_ids'][:5],
                "seller_ids": ctx['seller_ids'][:3],
                "payment_ids": ctx['payment_ids'][:5]
            },
            "customer_context": {
                "customer_unique_id": ctx['customer_unique_id'],
                "related_order_ids": ctx['related_order_ids'][:5]
            },
            "product_context": {
                "product_ids": ctx['product_ids'][:5],
                "category_names": ctx['category_names'][:5]
            },
            "delivery_analysis": {
                "delivered_at": ctx['delivered_at'],
                "estimated_delivery_at": ctx['estimated_delivery_at'],
                "carrier_handoff_at": ctx['carrier_handoff_at'],
                "delivery_variance_hours": ctx['delivery_variance_hours'],
                "seller_handoff_analysis": ctx['seller_handoff_analysis'] if len(items) > 0 else [],
                "late_handoff_seller_ids": ctx['late_handoff_seller_ids']
            },
            "payment_reconciliation": {
                "currency": "BRL",
                "item_total_brl": ctx['item_total_brl'],
                "freight_total_brl": ctx['freight_total_brl'],
                "expected_total_brl": ctx['expected_total_brl'],
                "payment_total_brl": ctx['payment_total_brl'],
                "difference_brl": ctx['difference_brl'],
                "reconciled": ctx['reconciled'],
                "payment_types": ctx['payment_types']
            },
            "root_cause_analysis": {
                "ranked_causes": [
                    {"cause_code": root_cause_code, "rank": 1}
                ][:3],
                "responsible_parties": responsible_parties[:3]
            },
            "evidence_ids": evidence_ids[:20],
            "financial_resolution": {
                "currency": "BRL",
                "recommended_refund_brl": recommended_refund
            },
            "resolution_actions": resolution_actions[:5]
        }

        return output_schema
