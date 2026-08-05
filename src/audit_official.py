import glob
import json
import pandas as pd

def audit():
    files = sorted(glob.glob('output/EC_*.json'))
    print(f"Auditing {len(files)} official output files...")

    issues = []

    for fpath in files:
        with open(fpath, 'r', encoding='utf-8') as f:
            d = json.load(f)

        cid = d['case_id']
        ca = d['case_assessment']
        ae = d['affected_entities']
        cc = d['customer_context']
        pc = d['product_context']
        da = d['delivery_analysis']
        pr = d['payment_reconciliation']
        rc = d['root_cause_analysis']
        ev = d['evidence_ids']
        fr = d['financial_resolution']
        ra = d['resolution_actions']

        # Check 1: case_status vs refund
        ref = fr['recommended_refund_brl']
        st = ca['case_status']
        if ref > 0 and st != 'action_required':
            issues.append(f"{cid}: Refund > 0 ({ref}) but status is {st}")
        elif ref == 0 and st != 'no_action':
            issues.append(f"{cid}: Refund == 0 but status is {st}")

        # Check 2: seller evidence vs responsible sellers
        resp_sellers = [p['party_id'] for p in rc['responsible_parties'] if p['party_type'] == 'seller']
        seller_evs = [e.split('seller:')[1] for e in ev if e.startswith('seller:')]
        for s in seller_evs:
            if s not in resp_sellers:
                issues.append(f"{cid}: Evidence contains non-responsible seller {s} (responsible: {resp_sellers})")

        # Check 3: category names nan check
        for cat in pc['category_names']:
            if cat == 'nan' or cat is None:
                issues.append(f"{cid}: category_name is nan or null")

        # Check 4: secondary issues order
        expected_sec_order = ['multi_item_order', 'multi_seller_order', 'split_payment', 'repeat_customer', 'multiple_categories']
        actual_secs = ca['secondary_issues']
        filtered_expected = [s for s in expected_sec_order if s in actual_secs]
        if actual_secs != filtered_expected:
            issues.append(f"{cid}: Secondary issues out of order! Actual: {actual_secs}, Expected: {filtered_expected}")

        # Check 5: actions order
        pri_act = ra[0]
        add_acts = ra[1:]
        expected_act_order = ['review_seller_handoff', 'review_carrier_delay', 'verify_refund_completion', 'coordinate_multi_seller_case', 'verify_payment_allocation']
        filtered_acts = [a for a in expected_act_order if a in add_acts]
        if add_acts != filtered_acts:
            issues.append(f"{cid}: Resolution actions out of order! Actual: {add_acts}, Expected: {filtered_acts}")

    print(f"\nAudit complete. Total issues detected: {len(issues)}")
    for iss in issues[:20]:
        print(" -", iss)

if __name__ == '__main__':
    audit()
