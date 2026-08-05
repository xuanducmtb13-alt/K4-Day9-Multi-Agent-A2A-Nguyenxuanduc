import os
import glob
import json
from src.data_engine import DataEngine
from src.policy_engine import PolicyEngine
from src.agents import CoordinatorAgent
from src.generate_inputs import generate_input_files

def main():
    print("=== Multi-Agent E-commerce Dispute Resolution Pipeline ===")

    input_files = sorted(glob.glob('input/EC_*.json'))
    if len(input_files) < 50:
        print("Input files missing or incomplete. Generating 50 input cases...")
        generate_input_files()
        input_files = sorted(glob.glob('input/EC_*.json'))

    print(f"Found {len(input_files)} input files.")

    data_engine = DataEngine(data_dir='data')
    policy_engine = PolicyEngine()
    coordinator = CoordinatorAgent(data_engine, policy_engine)

    os.makedirs('output', exist_ok=True)
    os.makedirs('logging', exist_ok=True)

    all_traces = []

    for idx, input_path in enumerate(input_files, 1):
        with open(input_path, 'r', encoding='utf-8') as f:
            case_input = json.load(f)

        case_id = case_input['case_id']
        output_schema, traces = coordinator.process_case(case_input)
        all_traces.extend(traces)

        output_path = os.path.join('output', f"{case_id}.json")
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(output_schema, f, ensure_ascii=False, indent=2)

    # Write trace.jsonl
    with open('trace.jsonl', 'w', encoding='utf-8') as f:
        for t in all_traces:
            f.write(json.dumps(t, ensure_ascii=False) + '\n')

    with open('logging/trace.jsonl', 'w', encoding='utf-8') as f:
        for t in all_traces:
            f.write(json.dumps(t, ensure_ascii=False) + '\n')

    # Write metadata.json
    metadata = {
        "model": "Qwen2.5-Coder-7B-Instruct",
        "parameter_size": "7B",
        "framework": "Custom A2A Multi-Agent Framework (Python + Pydantic)",
        "runtime": "Python 3.11",
        "total_cases_processed": len(input_files),
        "policy_version": "EC_POLICY_V2",
        "timestamp": "2026-08-05"
    }

    with open('metadata.json', 'w', encoding='utf-8') as f:
        json.dump(metadata, f, ensure_ascii=False, indent=2)

    with open('logging/metadata.json', 'w', encoding='utf-8') as f:
        json.dump(metadata, f, ensure_ascii=False, indent=2)

    # Automatically package output.zip with output/ folder prefix
    import zipfile
    out_files = sorted(glob.glob('output/EC_*.json'))
    with zipfile.ZipFile('output.zip', 'w', zipfile.ZIP_DEFLATED) as zipf:
        for f in out_files:
            zipf.write(f, arcname=os.path.join('output', os.path.basename(f)))

    print(f"Successfully processed {len(input_files)} cases.")
    print("Outputs written to 'output/'")
    print("Packaged 50 files into 'output.zip' (wrapped in output/ folder)")
    print("Trace written to 'trace.jsonl' and 'logging/trace.jsonl'")
    print("Metadata written to 'metadata.json'")

if __name__ == '__main__':
    main()
