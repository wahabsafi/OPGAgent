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
from PIL import Image, ImageDraw, ImageFont
import io
import base64

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

def get_agent(provider="openai", model=None, api_key=None, base_url=None, enable_cloud_vlm=True):
    cache_key = (provider, model, api_key, base_url, enable_cloud_vlm)
    if cache_key not in AGENTS:
        config_path = PROJECT_ROOT / "src" / "opgagent" / "config" / "agent_config.yaml"
        AGENTS[cache_key] = OPGReActAgent(
            config_path=str(config_path) if config_path.exists() else None,
            tool_service="api_service",
            llm_provider=provider,
            llm_model=model,
            api_key=api_key,
            base_url=base_url,
            enable_cloud_vlm=enable_cloud_vlm,
        )
    return AGENTS[cache_key]

def _parse_engine_choice(engine_choice: str):
    if "Qwen2.5-7B" in engine_choice or "8091" in engine_choice:
        return "qwen_local", "qwen2.5-7b-instruct"
    elif "OpenAI (GPT-4o-mini)" in engine_choice:
        return "openai", "gpt-4o-mini"
    elif "OpenAI" in engine_choice:
        return "openai", "gpt-4o"
    elif "Gemini (gemini-1.5-flash)" in engine_choice:
        return "gemini", "gemini-1.5-flash"
    elif "Gemini" in engine_choice:
        return "gemini", "gemini-2.0-flash"
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
    enable_cloud_vlm,
    detection_conf=0.25,
    progress=gr.Progress(track_tqdm=True)
):
    if image is None:
        return "⚠️ **Please upload a panoramic radiograph (OPG) image first.**", {}, "No image provided."

    provider, default_model = _parse_engine_choice(engine_choice or "")
    model = model_name_input.strip() if model_name_input and model_name_input.strip() else default_model
    api_key = api_key_input.strip() if api_key_input and api_key_input.strip() else None
    base_url = base_url_input.strip() if base_url_input and base_url_input.strip() else None

    # Set vision sensitivity threshold (default 0.25, previously hardcoded to 0.50)
    os.environ["DETECTION_CONFIDENCE"] = str(detection_conf)

    # Control whether cloud VLMs (OpenAI & Gemini) are permitted
    os.environ["ENABLE_CLOUD_VLM"] = "true" if enable_cloud_vlm else "false"

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
    print(f"🌐 Cloud VLMs (OpenAI & Gemini): {'ENABLED' if enable_cloud_vlm else 'DISABLED (100% Offline Local Mode)'}")
    print(f"❓ Question: {question}")
    print(f"🖼️ Image size: {image.size}")
    print("="*50)

    if not question or not question.strip():
        question = "Analyze this OPG and give a concise diagnostic summary."

    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
        image.save(tmp.name)
        tmp_path = tmp.name

    try:
        mode_label = "Local Offline" if not enable_cloud_vlm else "Cloud-Ensemble"
        progress(0.1, desc=f"Initializing OPGAgent ({model}, {mode_label}) & preloading CV detection cache...")
        print(f"⚙️ Initializing agent ({provider} / {model}, cloud_vlm={enable_cloud_vlm})...")
        agent = get_agent(provider=provider, model=model, api_key=api_key, base_url=base_url, enable_cloud_vlm=enable_cloud_vlm)

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

def _decode_base64_image(b64_str: str) -> Image.Image:
    """Decode base64 string to PIL RGB image."""
    if "," in b64_str:
        b64_str = b64_str.split(",", 1)[1]
    raw = base64.b64decode(b64_str)
    return Image.open(io.BytesIO(raw)).convert("RGB")

def _draw_boxes_pil(image: Image.Image, items: list, color: str = "#00ff66", width: int = 3) -> Image.Image:
    """Draw bounding boxes with background labels on a PIL image."""
    img = image.copy().convert("RGB")
    draw = ImageDraw.Draw(img)
    font = None
    for font_path in [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    ]:
        if os.path.exists(font_path):
            try:
                font = ImageFont.truetype(font_path, 16)
                break
            except Exception:
                pass
    if font is None:
        font = ImageFont.load_default()

    for item in items:
        box = item.get("box", [])
        if not box or len(box) != 4:
            continue
        x1, y1, x2, y2 = [int(v) for v in box]
        label = str(item.get("label", ""))
        draw.rectangle([x1, y1, x2, y2], outline=color, width=width)
        if label:
            tag_y = max(0, y1 - 20)
            tag_w = len(label) * 9 + 8
            draw.rectangle([x1, tag_y, x1 + tag_w, tag_y + 18], fill=color)
            draw.text((x1 + 4, tag_y + 1), label, fill="black", font=font)
    return img

def _draw_contours_pil(image: Image.Image, contours: list, color: str = "#00ffff", width: int = 3) -> Image.Image:
    """Draw polygon contours on a PIL image."""
    img = image.copy().convert("RGB")
    draw = ImageDraw.Draw(img)
    for c in contours:
        pts = [(int(p[0]), int(p[1])) for p in c if len(p) >= 2]
        if len(pts) > 2:
            draw.polygon(pts, outline=color, width=width)
    return img

def inspect_single_model(
    image,
    model_choice,
    confidence=0.15,
    vlm_prompt="",
    medsam_count=10,
    progress=gr.Progress(track_tqdm=True)
):
    """Directly calls an individual model service and displays its visual overlay and raw data."""
    if image is None:
        return None, "⚠️ **Please upload a panoramic radiograph (OPG) image first.**", {}

    local_proxies = {"http": None, "https": None}
    
    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
        image.save(tmp.name, format="PNG")
        tmp_path = tmp.name

    try:
        if "YOLO" in model_choice:
            progress(0.2, desc="Calling YOLO tooth enumeration service (Port 6600)...")
            url = "http://127.0.0.1:6600/detect"
            with open(tmp_path, "rb") as f:
                res = requests.post(
                    url,
                    files={"file": f},
                    data={"conf_threshold": str(confidence), "return_image": "true"},
                    timeout=30,
                    proxies=local_proxies
                )
            if res.status_code != 200:
                return image, f"❌ **YOLO Service Error (HTTP {res.status_code}):**\n```\n{res.text}\n```", {}
            data = res.json()
            vis_img = None
            if data.get("visualized_image"):
                vis_img = _decode_base64_image(data["visualized_image"])
            else:
                boxes = [
                    {"box": [d["bbox"]["x1"], d["bbox"]["y1"], d["bbox"]["x2"], d["bbox"]["y2"]], "label": f"{d['class_name']} ({d['confidence']:.2f})"}
                    for d in data.get("detections", [])
                ]
                vis_img = _draw_boxes_pil(image, boxes, color="#00ffcc")

            detections = data.get("detections", [])
            stats = data.get("statistics", {})
            type_counts = stats.get("tooth_count_by_type", {})
            summary_md = f"""### 🦷 YOLO Tooth Enumeration Results
- **Model:** YOLOv9c Tooth Detector (`http://127.0.0.1:6600`)
- **Total Teeth Detected:** `{len(detections)}`
- **Confidence Threshold:** `{confidence}`
- **Tooth Type Distribution (1=Central Incisor .. 8=Wisdom Tooth):**
"""
            for k, v in sorted(type_counts.items()):
                summary_md += f"  - Tooth Type {k}: **{v}**\n"

            return vis_img, summary_md, data

        elif "11 Dental Diseases" in model_choice or "11 Diseases" in model_choice:
            progress(0.2, desc="Calling TVEM MaskDINO 11 Diseases service (Port 6602)...")
            url = "http://127.0.0.1:6602/detect/11diseases"
            with open(tmp_path, "rb") as f:
                res = requests.post(
                    url,
                    files={"file": f},
                    data={"confidence": str(confidence), "return_vis": "true"},
                    timeout=45,
                    proxies=local_proxies
                )
            if res.status_code != 200:
                return image, f"❌ **TVEM Service Error (HTTP {res.status_code}):**\n```\n{res.text}\n```", {}
            data = res.json()
            
            TVEM_11DISEASES_CLASS_MAP = {
                0: "Caries",
                1: "Crown",
                2: "Filling",
                3: "Implant",
                4: "Mandibular Canal",
                5: "Missing teeth",
                6: "Periapical lesion",
                7: "Root Canal Treatment",
                8: "Root Piece",
                9: "impacted tooth",
                10: "maxillary sinus",
            }
            detections = data.get("detections", [])
            for d in detections:
                cid = d.get("class_id")
                if cid is not None and cid in TVEM_11DISEASES_CLASS_MAP:
                    d["class_name"] = TVEM_11DISEASES_CLASS_MAP[cid]

            vis_img = None
            if data.get("visualization_base64"):
                vis_img = _decode_base64_image(data["visualization_base64"])
            else:
                boxes = [
                    {"box": d.get("box", d.get("bbox", [])), "label": f"{d.get('class_name')} ({d.get('confidence', 0):.2f})"}
                    for d in detections
                ]
                vis_img = _draw_boxes_pil(image, boxes, color="#ff3366")

            counts = {}
            for d in detections:
                cname = d.get("class_name", "Unknown")
                counts[cname] = counts.get(cname, 0) + 1

            summary_md = f"""### 🩺 TVEM MaskDINO 11 Diseases Results
- **Model:** TVEM MaskDINO Multitask (`http://127.0.0.1:6602/detect/11diseases`)
- **Total Findings Detected:** `{len(detections)}`
- **Confidence Threshold:** `{confidence}`
- **Pathology Breakdown:**
"""
            if counts:
                for k, v in sorted(counts.items()):
                    summary_md += f"  - **{k}**: {v}\n"
            else:
                summary_md += "  - *No disease findings above the selected confidence threshold.*\n"

            return vis_img, summary_md, data

        elif "Bone Loss" in model_choice:
            progress(0.2, desc="Calling TVEM Periodontal Bone Loss service (Port 6602)...")
            url = "http://127.0.0.1:6602/detect/bone_loss"
            with open(tmp_path, "rb") as f:
                res = requests.post(
                    url,
                    files={"file": f},
                    data={"confidence": str(confidence), "return_vis": "true"},
                    timeout=45,
                    proxies=local_proxies
                )
            if res.status_code != 200:
                return image, f"❌ **TVEM Bone Loss Error (HTTP {res.status_code}):**\n```\n{res.text}\n```", {}
            data = res.json()
            vis_img = None
            if data.get("visualization_base64"):
                vis_img = _decode_base64_image(data["visualization_base64"])
            else:
                boxes = [
                    {"box": d.get("box", d.get("bbox", [])), "label": f"Bone Loss ({d.get('confidence', 0):.2f})"}
                    for d in data.get("detections", [])
                ]
                vis_img = _draw_boxes_pil(image, boxes, color="#ff9900")

            detections = data.get("detections", [])
            summary_md = f"""### 🦴 TVEM Periodontal Bone Loss Results
- **Model:** TVEM MaskDINO Bone Loss (`http://127.0.0.1:6602/detect/bone_loss`)
- **Detected Bone Resorption Zones:** `{len(detections)}`
- **Confidence Threshold:** `{confidence}`
"""
            return vis_img, summary_md, data

        elif "Anatomical" in model_choice or "Canal" in model_choice:
            progress(0.2, desc="Calling TVEM Anatomical Structures service (Port 6602)...")
            url = "http://127.0.0.1:6602/detect/mandibular_maxillary"
            with open(tmp_path, "rb") as f:
                res = requests.post(
                    url,
                    files={"file": f},
                    data={"confidence": str(confidence), "return_vis": "true"},
                    timeout=45,
                    proxies=local_proxies
                )
            if res.status_code != 200:
                return image, f"❌ **TVEM Anatomy Error (HTTP {res.status_code}):**\n```\n{res.text}\n```", {}
            data = res.json()
            vis_img = None
            if data.get("visualization_base64"):
                vis_img = _decode_base64_image(data["visualization_base64"])
            else:
                boxes = [
                    {"box": d.get("box", d.get("bbox", [])), "label": f"{d.get('class_name', 'Anatomy')} ({d.get('confidence', 0):.2f})"}
                    for d in data.get("detections", [])
                ]
                vis_img = _draw_boxes_pil(image, boxes, color="#9933ff")

            detections = data.get("detections", [])
            summary_md = f"""### 📐 TVEM Anatomical Structures (Canals & Sinuses)
- **Model:** TVEM MaskDINO Anatomy (`http://127.0.0.1:6602/detect/mandibular_maxillary`)
- **Detected Landmark Structures:** `{len(detections)}`
- **Confidence Threshold:** `{confidence}`
"""
            return vis_img, summary_md, data

        elif "Quadrants" in model_choice:
            progress(0.2, desc="Calling TVEM 4 Quadrants service (Port 6602)...")
            url = "http://127.0.0.1:6602/detect/4quadrants"
            with open(tmp_path, "rb") as f:
                res = requests.post(
                    url,
                    files={"file": f},
                    data={"confidence": str(confidence), "return_vis": "true"},
                    timeout=45,
                    proxies=local_proxies
                )
            if res.status_code != 200:
                return image, f"❌ **TVEM Quadrants Error (HTTP {res.status_code}):**\n```\n{res.text}\n```", {}
            data = res.json()
            vis_img = None
            if data.get("visualization_base64"):
                vis_img = _decode_base64_image(data["visualization_base64"])
            else:
                boxes = [
                    {"box": d.get("box", d.get("bbox", [])), "label": f"{d.get('class_name', 'Quadrant')}"}
                    for d in data.get("detections", [])
                ]
                vis_img = _draw_boxes_pil(image, boxes, color="#0099ff")

            detections = data.get("detections", [])
            summary_md = f"""### 🎯 TVEM 4-Quadrant Partitioning
- **Model:** TVEM MaskDINO Quadrant Detector (`http://127.0.0.1:6602/detect/4quadrants`)
- **Detected Quadrants:** `{len(detections)}`
- **Confidence Threshold:** `{confidence}`
"""
            return vis_img, summary_md, data

        elif "FDI" in model_choice:
            progress(0.1, desc="Step 1/2: Querying YOLO Tooth Enumeration...")
            url_yolo = "http://127.0.0.1:6600/detect"
            with open(tmp_path, "rb") as f:
                res_yolo = requests.post(url_yolo, files={"file": f}, data={"conf_threshold": str(confidence)}, timeout=30, proxies=local_proxies)
            if res_yolo.status_code != 200:
                return image, f"❌ **YOLO Error (HTTP {res_yolo.status_code}):** {res_yolo.text}", {}

            progress(0.4, desc="Step 2/2: Querying TVEM 4 Quadrants...")
            url_quad = "http://127.0.0.1:6602/detect/4quadrants"
            with open(tmp_path, "rb") as f:
                res_quad = requests.post(url_quad, files={"file": f}, data={"confidence": str(confidence)}, timeout=45, proxies=local_proxies)
            if res_quad.status_code != 200:
                return image, f"❌ **TVEM Quadrants Error (HTTP {res_quad.status_code}):** {res_quad.text}", {}

            from opgagent.tools.detection_merge import (
                build_fdi_teeth_like_refactor,
                _normalize_quadrants_for_merge,
                _normalize_teeth_for_merge,
            )
            q_norm = _normalize_quadrants_for_merge(res_quad.json())
            t_norm = _normalize_teeth_for_merge(res_yolo.json())
            teeth_fdi = build_fdi_teeth_like_refactor(quadrants=q_norm, teeth=t_norm)

            items_to_draw = []
            for fdi_num, tooth_info in teeth_fdi.items():
                box = tooth_info.get("box", [])
                if box and len(box) == 4:
                    items_to_draw.append({"box": box, "label": f"#{fdi_num}"})
            
            vis_img = _draw_boxes_pil(image, items_to_draw, color="#00ff66", width=3)
            
            present_fdi = sorted([int(k) for k in teeth_fdi.keys()])
            all_32 = set(range(11, 19)) | set(range(21, 29)) | set(range(31, 39)) | set(range(41, 49))
            missing_fdi = sorted(list(all_32 - set(present_fdi)))

            summary_md = f"""### ✨ Full FDI Tooth Numbering (YOLO + TVEM Fusion)
- **Pipeline:** YOLO enumeration merged with TVEM quadrant spatial boundaries
- **Present Teeth Count:** `{len(present_fdi)}` / 32
- **Present Teeth (FDI):** {' '.join([f'`[{n}]`' for n in present_fdi])}
- **Missing / Unerupted Teeth (FDI):** {' '.join([f'`[{n}]`' for n in missing_fdi]) if missing_fdi else '*None (Complete 32 dentition)*'}
"""
            return vis_img, summary_md, {"teeth_fdi": teeth_fdi, "present_teeth": present_fdi, "missing_teeth": missing_fdi}

        elif "MedSAM" in model_choice:
            progress(0.1, desc="Step 1: Detecting teeth with YOLO for MedSAM prompts...")
            url_yolo = "http://127.0.0.1:6600/detect"
            with open(tmp_path, "rb") as f:
                res_yolo = requests.post(url_yolo, files={"file": f}, data={"conf_threshold": str(confidence)}, timeout=30, proxies=local_proxies)
            if res_yolo.status_code != 200:
                return image, f"❌ **YOLO Error:** {res_yolo.text}", {}

            teeth_dets = res_yolo.json().get("detections", [])
            if not teeth_dets:
                return image, "⚠️ No teeth detected by YOLO at this confidence threshold to prompt MedSAM.", {}

            teeth_dets = sorted(teeth_dets, key=lambda d: d.get("confidence", 0), reverse=True)[:int(medsam_count)]
            
            progress(0.3, desc=f"Step 2: Prompting MedSAM for {len(teeth_dets)} tooth contours...")
            url_medsam = "http://127.0.0.1:6603/segment"
            contours = []
            medsam_results = []
            for td in teeth_dets:
                b = td["bbox"]
                bbox_str = f"{b['x1']},{b['y1']},{b['x2']},{b['y2']}"
                with open(tmp_path, "rb") as f:
                    r_seg = requests.post(url_medsam, files={"file": f}, data={"bbox": bbox_str}, timeout=30, proxies=local_proxies)
                if r_seg.status_code == 200:
                    seg_data = r_seg.json()
                    c = seg_data.get("mask_contour", [])
                    if c:
                        contours.append(c)
                        medsam_results.append({"tooth_type": td.get("class_name"), "contour_points": len(c), "bbox": bbox_str})

            vis_img = _draw_contours_pil(image, contours, color="#00ffff", width=3)
            summary_md = f"""### 📏 MedSAM Tooth Contour Segmentation Results
- **Model:** MedSAM ViT-B (`http://127.0.0.1:6603/segment`)
- **Prompted Teeth from YOLO:** `{len(teeth_dets)}`
- **Successfully Segmented Contours:** `{len(contours)}`
- **Visualization:** Cyan/turquoise polygons show exact anatomical tooth boundaries generated by MedSAM.
"""
            return vis_img, summary_md, {"segmented_teeth": medsam_results}

        elif "DentalGPT" in model_choice:
            progress(0.2, desc="Querying DentalGPT VLM for clinical vision analysis...")
            prompt = vlm_prompt.strip() if vlm_prompt and vlm_prompt.strip() else "Analyze this panoramic radiograph (OPG) and list all detected abnormalities."
            
            url_dental = "http://127.0.0.1:6608/analyze"
            vlm_text = ""
            raw_res = {}
            try:
                with open(tmp_path, "rb") as f:
                    r = requests.post(url_dental, files={"image": f}, data={"question": prompt}, timeout=120, proxies=local_proxies)
                if r.status_code == 200:
                    raw_res = r.json()
                    vlm_text = raw_res.get("analysis", raw_res.get("response", str(raw_res)))
                else:
                    raise Exception(f"Port 6608 returned HTTP {r.status_code}")
            except Exception as e_6608:
                progress(0.5, desc="Routing directly to llama-server (Port 8090)...")
                b64_img = ""
                with open(tmp_path, "rb") as f:
                    b64_img = base64.b64encode(f.read()).decode("utf-8")
                url_llama = "http://127.0.0.1:8090/v1/chat/completions"
                payload = {
                    "model": "DentalGPT-7B",
                    "messages": [
                        {
                            "role": "user",
                            "content": [
                                {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{b64_img}"}},
                                {"type": "text", "text": prompt}
                            ]
                        }
                    ],
                    "max_tokens": 1024
                }
                r_llama = requests.post(url_llama, json=payload, timeout=120, proxies=local_proxies)
                if r_llama.status_code == 200:
                    raw_res = r_llama.json()
                    vlm_text = raw_res["choices"][0]["message"]["content"]
                else:
                    return image, f"❌ **DentalGPT Error:** Port 6608 failed ({e_6608}) and Port 8090 returned {r_llama.status_code}: {r_llama.text}", {}

            summary_md = f"""### 👁️ DentalGPT VLM Direct Vision Analysis
- **Model:** DentalGPT-7B (`http://127.0.0.1:6608` / `http://127.0.0.1:8090`)
- **Prompt:** *"{prompt}"*

---
#### 🩺 Clinical Diagnostic Assessment:
{vlm_text}
"""
            return image, summary_md, raw_res

        else:
            return image, f"⚠️ Unknown model choice: {model_choice}", {}

    except Exception as e:
        traceback.print_exc()
        return image, f"❌ **Error running model:**\n```text\n{str(e)}\n```", {"error": str(e)}
    finally:
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)

with gr.Blocks(title="OPGAgent: Dental AI Diagnostic & Model Suite", theme=gr.themes.Soft()) as demo:
    gr.Markdown(
        """
        # 🦷 OPGAgent: Autonomous Dental Panoramic X-ray System
        > **MICCAI 2026** | Multimodal ReAct Agent with YOLO tooth enumeration, TVEM MaskDINO, MedSAM segmentation, and DentalGPT.
        """
    )

    with gr.Tabs():
        with gr.TabItem("🤖 Autonomous ReAct Agent"):
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
                                "Google Gemini (gemini-2.0-flash)",
                                "Google Gemini (gemini-1.5-flash)",
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
                                placeholder="e.g. gpt-4o, gpt-4o-mini, gemini-2.0-flash, gemini-1.5-flash, DentalGPT-7B",
                            )
                        base_url_input = gr.Textbox(
                            label="Custom Base URL (Optional)",
                            placeholder="e.g. http://127.0.0.1:8090/v1 (only for custom endpoint)",
                        )
                        enable_cloud_vlm_cb = gr.Checkbox(
                            label="🌐 Enable Cloud VLMs (OpenAI & Gemini calls)",
                            value=False,
                            info="Unchecked = 100% Offline Local Mode (A100 GPU only, no external calls). Checked = also query OpenAI and Gemini VLMs."
                        )
                        detection_conf_slider = gr.Slider(
                            minimum=0.05,
                            maximum=0.80,
                            value=0.25,
                            step=0.05,
                            label="🎯 Vision Detection Sensitivity (Confidence Threshold)",
                            info="Default: 0.25 (Original was hardcoded to 0.50, which discarded subtle cavities). Lower to 0.15-0.25 to detect faint caries and early bone loss."
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
                inputs=[image_input, question_input, engine_choice, api_key_input, model_name_input, base_url_input, enable_cloud_vlm_cb, detection_conf_slider],
                outputs=[report_output, json_output, trace_output],
                show_progress="full"
            )

        with gr.TabItem("🔬 Direct Model Inspector (Individual Testing)"):
            gr.Markdown(
                """
                ### 🔬 Direct Model Inspector & Vision Overlays
                Test any individual computer vision model or pipeline stage directly on your uploaded OPG image without running the full ReAct agent.
                """
            )
            with gr.Row():
                with gr.Column(scale=1):
                    inspector_image_input = gr.Image(type="pil", label="Upload Panoramic X-ray (OPG)")
                    
                    inspector_model_choice = gr.Dropdown(
                        label="🎯 Select Model / Pipeline Stage",
                        choices=[
                            "🦷 YOLO Tooth Enumeration (Port 6600)",
                            "✨ Full FDI Tooth Numbering (YOLO + TVEM Fusion)",
                            "🩺 TVEM 11 Dental Diseases (Port 6602)",
                            "🦴 TVEM Periodontal Bone Loss (Port 6602)",
                            "📐 TVEM Anatomical Structures (Canals & Sinuses - Port 6602)",
                            "🎯 TVEM 4 Quadrants Detection (Port 6602)",
                            "📏 MedSAM Tooth Contour Segmentation (Port 6603)",
                            "👁️ DentalGPT VLM Vision Analysis (Port 6608 / 8090)",
                        ],
                        value="🦷 YOLO Tooth Enumeration (Port 6600)",
                        interactive=True,
                    )
                    
                    with gr.Accordion("⚙️ Model Parameters & Options", open=True):
                        inspector_conf_slider = gr.Slider(
                            minimum=0.05,
                            maximum=0.95,
                            value=0.15,
                            step=0.05,
                            label="Detection Confidence Threshold (YOLO / TVEM)",
                            info="Default: 0.15. Lower to 0.10-0.20 to reveal faint cavities, early bone loss, and subtle apical shadows."
                        )
                        inspector_vlm_prompt = gr.Textbox(
                            label="Custom Prompt (DentalGPT only)",
                            value="Perform a detailed radiological assessment of this panoramic radiograph (OPG). Identify all teeth with caries, restorations, bone loss, or periapical lesions.",
                            lines=2,
                        )
                        inspector_medsam_count = gr.Slider(
                            minimum=1,
                            maximum=32,
                            value=12,
                            step=1,
                            label="Max Teeth to Segment (MedSAM only)",
                            info="Runs MedSAM segmentation on the top N detected teeth"
                        )

                    inspect_btn = gr.Button("🔬 Run Model Inspection", variant="primary", size="lg")

                with gr.Column(scale=1):
                    inspector_vis_image = gr.Image(type="pil", label="Model Visual Output / Bounding Box & Contour Overlay")
                    inspector_summary = gr.Markdown(value="*Upload an OPG image, select a model, and click 'Run Model Inspection' to view results.*")
                    with gr.Accordion("📋 Raw Model Output / Detections JSON", open=False):
                        inspector_json = gr.JSON(label="JSON Data")

            inspect_btn.click(
                fn=inspect_single_model,
                inputs=[inspector_image_input, inspector_model_choice, inspector_conf_slider, inspector_vlm_prompt, inspector_medsam_count],
                outputs=[inspector_vis_image, inspector_summary, inspector_json],
                show_progress="full"
            )

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=7860, help="Port to run Web UI on (default: 7860)")
    parser.add_argument("--share", action="store_true", help="Generate a public shareable Gradio link")
    args = parser.parse_args()

    print(f"Starting OPGAgent Web UI on port {args.port} (share={args.share})...")
    demo.launch(server_name="0.0.0.0", server_port=args.port, share=args.share)
