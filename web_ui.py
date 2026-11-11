#!/usr/bin/env python3
"""
OPGAgent Interactive Web UI
Built with Gradio for auditable panoramic radiograph (OPG) interpretation.
"""

import os
import sys
import json
import logging
import tempfile
import argparse
import requests
import traceback
from pathlib import Path
from PIL import Image

# Configure logging so console shows all agent steps
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger("OPGAgent-WebUI")

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

    # CRITICAL: Ensure local microservices bypass the proxy
    no_proxy_vals = "localhost,127.0.0.1,0.0.0.0,::1"
    os.environ["NO_PROXY"] = no_proxy_vals
    os.environ["no_proxy"] = no_proxy_vals

_load_dotenv()

try:
    import gradio as gr
except ImportError:
    print("Gradio is not installed. Please install it with: uv pip install gradio")
    sys.exit(1)

from opgagent.agent import OPGReActAgent

AGENTS = {}

def get_agent(provider="openai", model=None, api_key=None, base_url=None):
    cache_key = (provider, model, api_key, base_url)
    if cache_key not in AGENTS:
        config_path = PROJECT_ROOT / "src" / "opgagent" / "config" / "agent_config.yaml"
        AGENTS[cache_key] = OPGReActAgent(
            config_path=str(config_path) if config_path.exists() else None,
            tool_service="api_service",
            llm_provider=provider,
            llm_model=model,
            api_key=api_key,
            base_url=base_url,
        )
    return AGENTS[cache_key]

def _parse_engine_choice(engine_choice: str):
    if "Qwen2.5-7B" in engine_choice or "8091" in engine_choice:
        return "qwen_local", "qwen2.5-7b-instruct"
    elif "OpenAI (GPT-4o-mini)" in engine_choice:
        return "openai", "gpt-4o-mini"
    elif "OpenAI" in engine_choice:
        return "openai", "gpt-4o"
    elif "Gemini" in engine_choice:
        return "gemini", "gemini-3.5-flash"
    elif "DentalGPT" in engine_choice:
        return "local", "DentalGPT-7B"
    elif "Custom" in engine_choice:
        return "custom", "gpt-4o"
    return "qwen_local", "qwen2.5-7b-instruct"

def test_engine_connection(engine_choice, api_key_input, model_name_input, base_url_input):
    provider, default_model = _parse_engine_choice(engine_choice or "")
    model = model_name_input.strip() if model_name_input and model_name_input.strip() else default_model
    api_key = api_key_input.strip() if api_key_input and api_key_input.strip() else None
    base_url = base_url_input.strip() if base_url_input and base_url_input.strip() else None

    try:
        if provider == "qwen_local":
            url = base_url or "http://127.0.0.1:8091/v1"
            import httpx
            with httpx.Client(trust_env=False, timeout=15.0) as client:
                res = client.post(
                    f"{url.rstrip('/')}/chat/completions",
                    json={"model": model or "qwen2.5-7b-instruct", "messages": [{"role": "user", "content": "Hello! Reply with 'Qwen2.5 connection OK'."}], "max_tokens": 25}
                )
                if res.status_code == 200:
                    data = res.json()
                    ans = data["choices"][0]["message"]["content"]
                    return f"✅ **Success!** Local Qwen2.5-7B Brain on Port 8091 responded:\n> {ans}"
                else:
                    return f"❌ **Error:** Port 8091 returned HTTP {res.status_code}: {res.text}"

        elif provider == "gemini":
            key = api_key or os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
            if not key:
                return "❌ **Error:** No Gemini API key provided. Please paste it above or set GEMINI_API_KEY in .env."
            from langchain_google_genai import ChatGoogleGenerativeAI
            llm = ChatGoogleGenerativeAI(model=model, google_api_key=key, timeout=30, max_retries=1)
            resp = llm.invoke("Hello! Reply with: 'Gemini connection successful.'")
            content = getattr(resp, "content", str(resp))
            return f"✅ **Success!** Gemini (`{model}`) connected successfully:\n> {content}"

        elif provider in ("local", "llama"):
            url = base_url or os.getenv("LOCAL_LLAMA_BASE_URL") or "http://127.0.0.1:8090/v1"
            import httpx
            with httpx.Client(trust_env=False, timeout=15.0) as client:
                res = client.post(
                    f"{url.rstrip('/')}/chat/completions",
                    json={"model": model or "DentalGPT-7B", "messages": [{"role": "user", "content": "Hello!"}], "max_tokens": 25}
                )
                if res.status_code == 200:
                    data = res.json()
                    ans = data["choices"][0]["message"]["content"]
                    return f"✅ **Success!** Local DentalGPT VLM (`{model}`) responded:\n> {ans}"
                else:
                    return f"❌ **Error:** llama-server returned HTTP {res.status_code}: {res.text}"

        else: # openai or custom
            key = api_key or os.getenv("OPENAI_API_KEY")
            if not key and not base_url:
                return "❌ **Error:** No OpenAI API key provided. Please paste it above or set OPENAI_API_KEY in .env."
            import openai
            kwargs = {"api_key": key or "dummy"}
            target_url = base_url or os.getenv("OPENAI_BASE_URL")
            if target_url:
                kwargs["base_url"] = target_url
            client = openai.OpenAI(**kwargs)
            res = client.chat.completions.create(
                model=model,
                messages=[{"role": "user", "content": "Hello! Reply with: 'OpenAI connection successful.'"}],
                max_tokens=25
            )
            ans = res.choices[0].message.content
            return f"✅ **Success!** OpenAI (`{model}`) connected successfully:\n> {ans}"

    except Exception as e:
        return f"❌ **Connection Failed:**\n```text\n{str(e)}\n```"

def get_service_status():
    services = {
        "YOLO Enumeration (Port 6600)": "http://localhost:6600/health",
        "TVEM MaskDINO (Port 6602)": "http://localhost:6602/health",
        "MedSAM Segmentation (Port 6603)": "http://localhost:6603/health",
        "OralGPT VLM (Port 6604)": "http://localhost:6604/health",
        "DentalGPT VLM (Port 6608)": "http://localhost:6608/health",
        "DentalGPT GGUF llama-server (Port 8090)": "http://localhost:8090/health",
        "Qwen2.5-7B Brain Server (Port 8091)": "http://localhost:8091/health",
    }
    lines = ["| Service | Status | Endpoint |", "| :--- | :--- | :--- |"]
    for name, url in services.items():
        try:
            r = requests.get(url, timeout=2.0, proxies={"http": None, "https": None})
            status = "🟢 Healthy (200)" if r.status_code == 200 else f"🔴 Error ({r.status_code})"
        except Exception as e:
            status = f"⚪ Offline ({type(e).__name__})"
        lines.append(f"| {name} | {status} | `{url}` |")
    return "\n".join(lines)

def analyze_opg(
    image,
    question,
    engine_choice,
    api_key_input,
    model_name_input,
    base_url_input,
    progress=gr.Progress(track_tqdm=True)
):
    if image is None:
        return "⚠️ **Please upload a panoramic radiograph (OPG) image first.**", {}, "No image provided."

    provider, default_model = _parse_engine_choice(engine_choice or "")
    model = model_name_input.strip() if model_name_input and model_name_input.strip() else default_model
    api_key = api_key_input.strip() if api_key_input and api_key_input.strip() else None
    base_url = base_url_input.strip() if base_url_input and base_url_input.strip() else None

    # Handle local Qwen brain on port 8091
    if provider == "qwen_local":
        base_url = base_url or "http://127.0.0.1:8091/v1"
        provider = "local"
        api_key = "local"

    # Inject into os.environ so all sub-tools (VLM, structured conversion) share the configuration
    if api_key:
        if provider in ("openai", "custom"):
            os.environ["OPENAI_API_KEY"] = api_key
        elif provider == "gemini":
            os.environ["GEMINI_API_KEY"] = api_key
    if model:
        if provider in ("openai", "custom"):
            os.environ["OPENAI_MODEL"] = model
        elif provider == "gemini":
            os.environ["GEMINI_MODEL"] = model
    if base_url:
        if provider in ("openai", "custom"):
            os.environ["OPENAI_BASE_URL"] = base_url
        elif provider == "local":
            os.environ["LOCAL_LLAMA_BASE_URL"] = base_url

    print("\n" + "="*50)
    print("📥 [Web UI] New Analysis Request Received!")
    print(f"🧠 Engine: {engine_choice} | Model: {model} | Provider: {provider}")
    print(f"❓ Question: {question}")
    print(f"🖼️ Image size: {image.size}")
    print("="*50)

    if not question or not question.strip():
        question = "Analyze this OPG and give a concise diagnostic summary."

    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
        image.save(tmp.name)
        tmp_path = tmp.name

    try:
        progress(0.1, desc=f"Initializing OPGAgent ({model}) & preloading CV detection cache...")
        print(f"⚙️ Initializing agent ({provider} / {model})...")
        agent = get_agent(provider=provider, model=model, api_key=api_key, base_url=base_url)

        progress(0.3, desc=f"Running visual models & ReAct reasoning loop with {model}...")
        print("🚀 Executing agent.run()...")
        result = agent.run(question=question, image_path=tmp_path)
        answer = result.get("answer", "No diagnosis generated.")
        print("✅ ReAct reasoning finished!")

        progress(0.85, desc="Extracting structured FDI report...")
        structured_json = {}
        try:
            structured_raw = agent.toolkit.convert_to_structured(answer)
            structured_json = json.loads(structured_raw).get("structured_report", {})
        except Exception as e:
            logger.warning(f"Structured extraction notice: {e}")
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
        progress(1.0, desc="Done!")
        print("🎉 Analysis successfully completed and returned to UI!\n")
        return answer, structured_json, steps_text

    except Exception as e:
        print(f"❌ Error during analysis: {e}")
        traceback.print_exc()
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

            with gr.Accordion("⚙️ AI Reasoning Engine & API Key Settings", open=True):
                engine_choice = gr.Dropdown(
                    label="🧠 Reasoning Engine (ReAct Brain)",
                    choices=[
                        "Local Brain Qwen2.5-7B (A100 Port 8091 - Recommended)",
                        "Google Gemini (gemini-3.5-flash)",
                        "OpenAI (GPT-4o)",
                        "OpenAI (GPT-4o-mini)",
                        "Local VLM (DentalGPT - Port 8090)",
                        "Custom OpenAI-Compatible (DeepSeek / Ollama / etc.)",
                    ],
                    value="Local Brain Qwen2.5-7B (A100 Port 8091 - Recommended)",
                    interactive=True,
                )
                with gr.Row():
                    api_key_input = gr.Textbox(
                        label="API Key (Optional)",
                        type="password",
                        placeholder="Paste OpenAI (sk-...) or Gemini API key (leave blank to use server .env)",
                    )
                    model_name_input = gr.Textbox(
                        label="Model Name (Optional)",
                        placeholder="e.g. gpt-4o, gpt-4o-mini, gemini-3.5-flash, DentalGPT-7B",
                    )
                base_url_input = gr.Textbox(
                    label="Custom Base URL (Optional)",
                    placeholder="e.g. http://127.0.0.1:8090/v1 (only for Local GPU or custom endpoint)",
                )
                with gr.Row():
                    test_conn_btn = gr.Button("🧪 Test Connection", size="sm")
                conn_status_box = gr.Markdown("")
                test_conn_btn.click(
                    fn=test_engine_connection,
                    inputs=[engine_choice, api_key_input, model_name_input, base_url_input],
                    outputs=[conn_status_box]
                )

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
        inputs=[image_input, question_input, engine_choice, api_key_input, model_name_input, base_url_input],
        outputs=[report_output, json_output, trace_output],
        show_progress="full"
    )

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=7860, help="Port to run Web UI on (default: 7860)")
    parser.add_argument("--share", action="store_true", help="Generate a public shareable Gradio link")
    args = parser.parse_args()

    print(f"Starting OPGAgent Web UI on port {args.port} (share={args.share})...")
    demo.launch(server_name="0.0.0.0", server_port=args.port, share=args.share)
