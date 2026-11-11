#!/usr/bin/env python3
"""
OPGAgent Interactive Web UI
Built with Gradio for auditable panoramic radiograph (OPG) interpretation.
"""

import os
import sys
import json
import tempfile
import argparse
import requests
from pathlib import Path
from PIL import Image

PROJECT_ROOT = Path(__file__).parent.resolve()
sys.path.insert(0, str(PROJECT_ROOT / "src"))

def _load_dotenv():
    env_file = PROJECT_ROOT / ".env"
    loaded_keys = set()
    if env_file.exists():
        with open(env_file, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, v = line.split("=", 1)
                    k, v = k.strip(), v.strip().strip("'\"")
                    if k:
                        os.environ[k] = v
                        loaded_keys.add(k)

    # If OPENAI_API_KEY was commented out or is dummy placeholder, purge it so it doesn't mask Gemini
    if "OPENAI_API_KEY" not in loaded_keys:
        os.environ.pop("OPENAI_API_KEY", None)
    elif os.environ.get("OPENAI_API_KEY", "").startswith("sk-...") or os.environ.get("OPENAI_API_KEY", "").startswith("your-"):
        os.environ.pop("OPENAI_API_KEY", None)

    # If Gemini is configured and OpenAI is not, ensure LLM_PROVIDER is gemini
    if (os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")) and not os.environ.get("OPENAI_API_KEY"):
        os.environ["LLM_PROVIDER"] = "gemini"

_load_dotenv()

try:
    import gradio as gr
except ImportError:
    print("Gradio is not installed. Please install it with: uv pip install gradio")
    sys.exit(1)

from opgagent.agent import OPGReActAgent

AGENT = None

def get_agent():
    global AGENT
    if AGENT is None:
        config_path = PROJECT_ROOT / "src" / "opgagent" / "config" / "agent_config.yaml"
        AGENT = OPGReActAgent(
            config_path=str(config_path) if config_path.exists() else None,
            tool_service="api_service"
        )
    return AGENT

def get_service_status():
    services = {
        "YOLO Enumeration (Port 6600)": "http://localhost:6600/health",
        "TVEM MaskDINO (Port 6602)": "http://localhost:6602/health",
        "MedSAM Segmentation (Port 6603)": "http://localhost:6603/health",
        "OralGPT VLM (Port 6604)": "http://localhost:6604/health",
        "DentalGPT VLM (Port 6608)": "http://localhost:6608/health",
        "DentalGPT GGUF llama-server (Port 8090)": "http://localhost:8090/health",
    }
    lines = ["| Service | Status | Endpoint |", "| :--- | :--- | :--- |"]
    for name, url in services.items():
        try:
            r = requests.get(url, timeout=1.5)
            status = "🟢 Healthy (200)" if r.status_code == 200 else f"🔴 Error ({r.status_code})"
        except Exception:
            status = "⚪ Offline"
        lines.append(f"| {name} | {status} | `{url}` |")
    return "\n".join(lines)

def analyze_opg(image, question):
    if image is None:
        return "⚠️ **Please upload a panoramic radiograph (OPG) image first.**", {}, "No image provided."

    if not question or not question.strip():
        question = "Analyze this OPG and give a concise diagnostic summary."

    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
        image.save(tmp.name)
        tmp_path = tmp.name

    try:
        agent = get_agent()
        result = agent.run(question=question, image_path=tmp_path)
        answer = result.get("answer", "No diagnosis generated.")

        structured_json = {}
        try:
            structured_raw = agent.toolkit.convert_to_structured(answer)
            structured_json = json.loads(structured_raw).get("structured_report", {})
        except Exception as e:
            structured_json = {"raw_report": answer, "note": f"Structured format extraction note: {e}"}

        # Summarize ReAct steps
        steps_log = []
        if "intermediate_steps" in result:
            for idx, step in enumerate(result["intermediate_steps"], start=1):
                action, observation = step
                tool_name = getattr(action, "tool", "Tool")
                tool_input = getattr(action, "tool_input", "")
                steps_log.append(f"### Step {idx}: `{tool_name}`")
                steps_log.append(f"**Query Input:**\n```json\n{json.dumps(tool_input, indent=2, ensure_ascii=False) if isinstance(tool_input, (dict, list)) else tool_input}\n```")
                obs_str = str(observation)
                if len(obs_str) > 600:
                    obs_str = obs_str[:600] + "\n... [truncated]"
                steps_log.append(f"**Tool Observation:**\n```text\n{obs_str}\n```\n")

        steps_text = "\n".join(steps_log) if steps_log else "Reasoning completed in a single pass."
        return answer, structured_json, steps_text

    except Exception as e:
        return f"❌ **Error during analysis:**\n\n```text\n{str(e)}\n```", {}, str(e)
    finally:
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)

def set_preset(text):
    return text

with gr.Blocks(title="OPGAgent: Dental X-ray Interpretation") as demo:
    gr.Markdown(
        """
        # 🦷 OPGAgent: Autonomous Dental Panoramic X-ray Interpretation
        > **MICCAI 2026** | Reasoning LLM ReAct agent with YOLO tooth enumeration, TVEM MaskDINO, MedSAM, and DentalGPT.
        """
    )

    with gr.Row():
        with gr.Column(scale=1):
            image_input = gr.Image(type="pil", label="Upload Panoramic X-ray (OPG)")
            
            question_input = gr.Textbox(
                label="Diagnostic Question / Focus",
                value="Analyze this OPG and give a concise diagnostic summary.",
                lines=3,
                placeholder="Ask a diagnostic question (e.g. check tooth 36, examine bone loss, identify caries)..."
            )

            gr.Markdown("**Quick Question Presets:**")
            with gr.Row():
                btn_preset1 = gr.Button("📋 Full Diagnostic Exam", size="sm")
                btn_preset2 = gr.Button("🦷 Caries & Cavities", size="sm")
            with gr.Row():
                btn_preset3 = gr.Button("🦴 Periodontal Bone Loss", size="sm")
                btn_preset4 = gr.Button("🔍 Missing / Impacted Teeth", size="sm")

            btn_preset1.click(lambda: "Analyze this OPG and give a concise diagnostic summary covering all teeth, restorations, bone loss, and lesions.", outputs=[question_input])
            btn_preset2.click(lambda: "Inspect all teeth in this OPG specifically for dental caries, deep cavities, or recurrent decay. List affected FDI tooth numbers.", outputs=[question_input])
            btn_preset3.click(lambda: "Evaluate the alveolar bone level and identify any regions or quadrants with horizontal or vertical periodontal bone loss.", outputs=[question_input])
            btn_preset4.click(lambda: "Identify all missing teeth and impacted wisdom teeth using FDI standard tooth notation.", outputs=[question_input])

            submit_btn = gr.Button("🩺 Run Dental AI Analysis", variant="primary", size="lg")

            with gr.Accordion("🔍 Backend Services Status", open=False):
                status_box = gr.Markdown(get_service_status)
                refresh_status_btn = gr.Button("🔄 Refresh Status", size="sm")
                refresh_status_btn.click(get_service_status, outputs=[status_box])

        with gr.Column(scale=1):
            with gr.Tabs():
                with gr.TabItem("📄 Diagnostic Report"):
                    report_output = gr.Markdown(label="Clinical Report", value="*Upload an OPG radiograph and click 'Run Dental AI Analysis' to generate findings.*")
                
                with gr.TabItem("📊 Structured JSON"):
                    json_output = gr.JSON(label="Structured Report (FDI Standard)")
                
                with gr.TabItem("🧠 ReAct Agent Trace"):
                    trace_output = gr.Markdown(label="Step-by-step Tool Execution")

    submit_btn.click(
        fn=analyze_opg,
        inputs=[image_input, question_input],
        outputs=[report_output, json_output, trace_output]
    )

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=7860, help="Port to run Web UI on (default: 7860)")
    parser.add_argument("--share", action="store_true", help="Generate a public shareable Gradio link")
    args = parser.parse_args()

    print(f"Starting OPGAgent Web UI on port {args.port} (share={args.share})...")
    demo.launch(server_name="0.0.0.0", server_port=args.port, share=args.share)
