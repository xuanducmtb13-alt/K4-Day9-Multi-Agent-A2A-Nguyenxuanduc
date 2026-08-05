import os
import glob
import json
import re

def validate():
    print("=== Validating Output JSON Files ===")
    files = sorted(glob.glob('output/EC_*.json'))
    assert len(files) == 50, f"Expected 50 output files, found {len(files)}"

    valid_primary_issues = {
        'canceled_order_paid', 'unavailable_order_paid', 'late_delivery_seller',
        'late_delivery_logistics', 'valid_split_payment', 'unsupported_late_claim'
    }

    valid_secondary_issues = {
        'multi_item_order', 'multi_seller_order', 'split_payment',
        'repeat_customer', 'multiple_categories'
    }

    evidence_pattern = re.compile(r'^(order|item|payment|seller|policy):.+$')

    errors = []

    for fpath in files:
        fname = os.path.basename(fpath)
        with open(fpath, 'r', encoding='utf-8') as f:
            data = json.load(f)

        # 1. Primary & Secondary
        ca = data.get('case_assessment', {})
        if ca.get('primary_issue') not in valid_primary_issues:
            errors.append(f"{fname}: Invalid primary_issue '{ca.get('primary_issue')}'")
        
        for sec in ca.get('secondary_issues', []):
            if sec not in valid_secondary_issues:
                errors.append(f"{fname}: Invalid secondary_issue '{sec}'")

        if ca.get('case_status') not in ['action_required', 'no_action']:
            errors.append(f"{fname}: Invalid case_status '{ca.get('case_status')}'")

        conf = ca.get('confidence', -1)
        if not (0 <= conf <= 1):
            errors.append(f"{fname}: Invalid confidence '{conf}'")

        # 2. Affected entities limits
        ae = data.get('affected_entities', {})
        if len(ae.get('order_ids', [])) > 5:
            errors.append(f"{fname}: order_ids > 5")
        if len(ae.get('item_ids', [])) > 5:
            errors.append(f"{fname}: item_ids > 5")
        if len(ae.get('seller_ids', [])) > 3:
            errors.append(f"{fname}: seller_ids > 3")
        if len(ae.get('payment_ids', [])) > 5:
            errors.append(f"{fname}: payment_ids > 5")

        # 3. Context limits
        cc = data.get('customer_context', {})
        if len(cc.get('related_order_ids', [])) > 5:
            errors.append(f"{fname}: related_order_ids > 5")

        pc = data.get('product_context', {})
        if len(pc.get('product_ids', [])) > 5:
            errors.append(f"{fname}: product_ids > 5")
        if len(pc.get('category_names', [])) > 5:
            errors.append(f"{fname}: category_names > 5")

        # 4. Root causes & evidence limits
        rc = data.get('root_cause_analysis', {})
        if len(rc.get('ranked_causes', [])) > 3:
            errors.append(f"{fname}: ranked_causes > 3")
        if len(rc.get('responsible_parties', [])) > 3:
            errors.append(f"{fname}: responsible_parties > 3")

        ev = data.get('evidence_ids', [])
        if len(ev) > 20:
            errors.append(f"{fname}: evidence_ids > 20")
        for eid in ev:
            if not evidence_pattern.match(eid):
                errors.append(f"{fname}: Invalid evidence ID format '{eid}'")

        act = data.get('resolution_actions', [])
        if len(act) > 5:
            errors.append(f"{fname}: resolution_actions > 5")

    if errors:
        print(f"Validation FAILED with {len(errors)} errors:")
        for err in errors[:10]:
            print(" -", err)
        raise ValueError("Validation errors detected.")
    else:
        print("Validation PASSED! All 50 output files conform strictly to the schema.")

if __name__ == '__main__':
    validate()
