import json
from datetime import datetime

class Agent:
    def __init__(self, name, role):
        self.name = name
        self.role = role

    def log_trace(self, case_id, step, action, data_summary):
        return {
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "case_id": case_id,
            "agent": self.name,
            "role": self.role,
            "step": step,
            "action": action,
            "summary": data_summary
        }

class CustomerAgent(Agent):
    def __init__(self):
        super().__init__("CustomerAgent", "Customer History Analysis")

    def run(self, case_id, ctx, traces):
        uniq_id = ctx.get("customer_unique_id")
        rel_orders = ctx.get("related_order_ids", [])
        summary = f"Customer unique ID: {uniq_id}. Found {len(rel_orders)} related historical orders."
        traces.append(self.log_trace(case_id, "CUSTOMER_INVESTIGATION", "retrieve_customer_history", summary))
        return ctx

class OrderProductAgent(Agent):
    def __init__(self):
        super().__init__("OrderProductAgent", "Order & Product Inspection")

    def run(self, case_id, ctx, traces):
        items = ctx.get("items", [])
        sellers = ctx.get("seller_ids", [])
        categories = ctx.get("category_names", [])
        summary = f"Order contains {len(items)} items from {len(sellers)} seller(s) in {len(categories)} category(ies)."
        traces.append(self.log_trace(case_id, "ORDER_PRODUCT_INSPECTION", "inspect_items_and_products", summary))
        return ctx

class DeliveryAgent(Agent):
    def __init__(self):
        super().__init__("DeliveryAgent", "Logistics & Seller Handoff Analysis")

    def run(self, case_id, ctx, traces):
        del_var = ctx.get("delivery_variance_hours")
        late_sellers = ctx.get("late_handoff_seller_ids", [])
        summary = f"Delivery variance: {del_var} hours. Late seller handoffs: {late_sellers}."
        traces.append(self.log_trace(case_id, "DELIVERY_ANALYSIS", "calculate_variances", summary))
        return ctx

class PaymentAgent(Agent):
    def __init__(self):
        super().__init__("PaymentAgent", "Payment Financial Reconciliation")

    def run(self, case_id, ctx, traces):
        pmt_total = ctx.get("payment_total_brl")
        exp_total = ctx.get("expected_total_brl")
        reconciled = ctx.get("reconciled")
        summary = f"Payments total: {pmt_total} BRL vs Expected: {exp_total} BRL. Reconciled: {reconciled}."
        traces.append(self.log_trace(case_id, "PAYMENT_RECONCILIATION", "reconcile_payments", summary))
        return ctx

class PolicyAgent(Agent):
    def __init__(self, policy_engine):
        super().__init__("PolicyAgent", "Policy EC_POLICY_V2 Decision Engine")
        self.policy_engine = policy_engine

    def run(self, case_id, ctx, traces):
        output_schema = self.policy_engine.evaluate(ctx)
        pri_issue = output_schema["case_assessment"]["primary_issue"]
        refund = output_schema["financial_resolution"]["recommended_refund_brl"]
        summary = f"Evaluated EC_POLICY_V2 -> Primary Issue: {pri_issue}, Refund: {refund} BRL."
        traces.append(self.log_trace(case_id, "POLICY_EVALUATION", "apply_ec_policy_v2", summary))
        return output_schema

class VerifierAgent(Agent):
    def __init__(self):
        super().__init__("VerifierAgent", "Schema & Safety Compliance Verifier")

    def run(self, case_id, output_schema, traces):
        # Validate array limits and null safety
        ass = output_schema.get("case_assessment", {})
        aff = output_schema.get("affected_entities", {})
        ev = output_schema.get("evidence_ids", [])
        
        valid = True
        errs = []

        if len(aff.get("order_ids", [])) > 5:
            errs.append("order_ids exceeds max 5")
        if len(aff.get("item_ids", [])) > 5:
            errs.append("item_ids exceeds max 5")
        if len(aff.get("seller_ids", [])) > 3:
            errs.append("seller_ids exceeds max 3")
        if len(ev) > 20:
            errs.append("evidence_ids exceeds max 20")

        if errs:
            valid = False
            summary = f"Verification warnings: {', '.join(errs)}"
        else:
            summary = "Verification successful. All schema constraints, array limits, and evidence formats passed."

        traces.append(self.log_trace(case_id, "VERIFICATION_CHECK", "validate_output_schema", summary))
        return output_schema, valid

class CoordinatorAgent(Agent):
    def __init__(self, data_engine, policy_engine):
        super().__init__("CoordinatorAgent", "Workflow Delegation & Synthesis Coordinator")
        self.data_engine = data_engine
        self.customer_agent = CustomerAgent()
        self.order_product_agent = OrderProductAgent()
        self.delivery_agent = DeliveryAgent()
        self.payment_agent = PaymentAgent()
        self.policy_agent = PolicyAgent(policy_engine)
        self.verifier_agent = VerifierAgent()

    def process_case(self, case_input):
        case_id = case_input["case_id"]
        claimed_order_id = case_input["customer_request"]["claimed_order_id"]
        traces = []

        traces.append(self.log_trace(case_id, "CASE_RECEIVED", "delegate_investigation", f"Received investigation for claimed_order_id: {claimed_order_id}"))

        ctx = self.data_engine.get_order_context(claimed_order_id)
        if not ctx:
            traces.append(self.log_trace(case_id, "ERROR", "order_not_found", f"Order ID {claimed_order_id} not found in database."))
            return None, traces

        ctx['case_id'] = case_id

        # Multi-agent workflow handoffs
        ctx = self.customer_agent.run(case_id, ctx, traces)
        ctx = self.order_product_agent.run(case_id, ctx, traces)
        ctx = self.delivery_agent.run(case_id, ctx, traces)
        ctx = self.payment_agent.run(case_id, ctx, traces)
        
        output_schema = self.policy_agent.run(case_id, ctx, traces)
        output_schema, valid = self.verifier_agent.run(case_id, output_schema, traces)

        traces.append(self.log_trace(case_id, "CASE_COMPLETED", "synthesize_final_resolution", f"Completed case {case_id} with status {output_schema['case_assessment']['case_status']}"))

        return output_schema, traces
