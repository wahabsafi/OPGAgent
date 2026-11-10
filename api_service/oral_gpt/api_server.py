#!/usr/bin/env python3
"""
OralGPT-omni API 服务
"""
from fastapi import FastAPI, File, UploadFile, Form, HTTPException
from fastapi.responses import JSONResponse
import sys
import os
from pathlib import Path
import tempfile

# 添加 OralGPT-omni 路径
ORALGPT_PATH = Path(__file__).parent
sys.path.insert(0, str(ORALGPT_PATH))

# 延迟导入（避免模块级别执行）
infer_module = None
LLAMA_SERVER_URL = os.environ.get("LLAMA_SERVER_URL") or os.environ.get("ORAL_GPT_LLAMA_URL")

app = FastAPI(
    title="OralGPT-omni API",
    description="OralGPT-omni 视觉模型服务",
    version="1.0.0"
)

# 服务状态
service_status = {
    "model_loaded": False,
    "device": "cuda"
}


@app.on_event("startup")
async def startup_event():
    """服务启动时加载模型"""
    global infer_module
    if LLAMA_SERVER_URL:
        print(f"🔧 Using llama-server backend at {LLAMA_SERVER_URL} for OralGPT...")
        service_status["model_loaded"] = True
        return

    print("🔧 初始化 OralGPT-omni 模型...")
    from infer_module import initialize_model, run_inference
    import infer_module as im
    infer_module = im
    initialize_model()
    service_status["model_loaded"] = True
    print("✅ 模型加载完成")


@app.get("/health")
async def health_check():
    """健康检查端点"""
    if LLAMA_SERVER_URL:
        try:
            import requests
            r = requests.get(f"{LLAMA_SERVER_URL}/health", timeout=3)
            is_healthy = r.status_code == 200
        except Exception:
            is_healthy = False
        return {
            "status": "healthy" if is_healthy else "unhealthy",
            "model_loaded": is_healthy,
            "backend": "llama-server",
            "service": "oral_gpt_omni"
        }
    return {
        "status": "healthy" if service_status["model_loaded"] else "loading",
        "model_loaded": service_status["model_loaded"],
        "service": "oral_gpt_omni"
    }


@app.post("/analyze")
async def analyze(
    file: UploadFile = File(...),
    prompt: str = Form("请详细分析这张口腔全景片(OPG)，描述牙齿状况、潜在问题和建议。"),
    temperature: float = Form(0.3),
    with_report: bool = Form(False),
):
    """
    分析 OPG 图像
    
    Args:
        file: 上传的图像文件
        prompt: 提示词
        
    Returns:
        {
            "analysis": "分析文本",
            "model": "OralGPT-omni"
        }
    """
    global infer_module
    
    if not service_status["model_loaded"]:
        raise HTTPException(status_code=503, detail="模型正在加载中")

    if LLAMA_SERVER_URL:
        import base64
        import requests
        try:
            content = await file.read()
            b64_img = base64.b64encode(content).decode("utf-8")
            img_data_url = f"data:image/jpeg;base64,{b64_img}"

            def _generate_text_llama(prompt_text: str) -> str:
                payload = {
                    "messages": [
                        {
                            "role": "user",
                            "content": [
                                {"type": "image_url", "image_url": {"url": img_data_url}},
                                {"type": "text", "text": prompt_text}
                            ]
                        }
                    ],
                    "temperature": float(temperature),
                    "max_tokens": 4096
                }
                res = requests.post(f"{LLAMA_SERVER_URL}/v1/chat/completions", json=payload, timeout=120)
                res.raise_for_status()
                return res.json()["choices"][0]["message"]["content"]

            if with_report:
                report_prompt = "\n".join(
                    [
                        "You are a dental radiologist.",
                        "Task: Based on this OPG, generate a 1-4 line objective, concise radiological report.",
                        "Rules: Use FDI tooth notation; avoid speculation; output only the report text.",
                    ]
                )
                report_text = _generate_text_llama(report_prompt)
                answer_text = _generate_text_llama(prompt)
                analysis = f"REPORT: {(report_text or '').strip()}\nFINAL_ANSWER: {(answer_text or '').strip()}"
            else:
                analysis = _generate_text_llama(prompt)

            return {
                "analysis": analysis,
                "model": "DentalGPT-GGUF"
            }
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"LLaMA server analyze failed: {e}")
    
    try:
        # 保存上传的文件
        with tempfile.NamedTemporaryFile(delete=False, suffix=".jpg") as tmp:
            content = await file.read()
            tmp.write(content)
            tmp_path = tmp.name
        
        # 核心说明：为满足“同一次 API 调用里先生成 report，再回答问题”的约束，
        # 这里在服务端同一次请求内串行做两次生成，并拼接成固定结构返回（REPORT + FINAL_ANSWER）。
        if with_report:
            report_prompt = "\n".join(
                [
                    "你是一名口腔颌面放射科专家。",
                    "任务：请基于这张口腔全景片(OPG)生成 1-4 行客观、简短的放射学报告。",
                    "规则：使用 FDI 牙号；避免臆测；仅输出报告正文。",
                ]
            )
            report_text = infer_module.run_inference(
                image_path=tmp_path,
                prompt=report_prompt,
                temperature=temperature,
            )
            answer_text = infer_module.run_inference(
                image_path=tmp_path,
                prompt=prompt,
                temperature=temperature,
            )
            result = f"REPORT: {(report_text or '').strip()}\nFINAL_ANSWER: {(answer_text or '').strip()}"
        else:
            # 运行推理（保持向后兼容：直接返回模型原始输出）
            result = infer_module.run_inference(
                image_path=tmp_path,
                prompt=prompt,
                temperature=temperature,
            )
        
        # 清理临时文件
        os.unlink(tmp_path)
        
        return JSONResponse(content={
            "analysis": result,
            "model": "OralGPT-omni"
        })
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/load_model")
async def load_model():
    """手动加载模型"""
    global infer_module
    
    if service_status["model_loaded"]:
        return {"status": "info", "message": "模型已加载"}
    
    try:
        print("🔧 手动加载 OralGPT-omni 模型...")
        from infer_module import initialize_model
        import infer_module as im
        infer_module = im
        initialize_model()
        service_status["model_loaded"] = True
        print("✅ 模型加载完成")
        return {"status": "success", "message": "模型加载成功"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"加载模型失败: {str(e)}")


@app.post("/unload_model")
async def unload_model():
    """卸载模型以释放 GPU 内存"""
    global infer_module
    
    if not service_status["model_loaded"]:
        return {"status": "info", "message": "模型未加载"}
    
    try:
        import torch
        from infer_module import unload_model as _unload
        _unload()
        infer_module = None
        service_status["model_loaded"] = False
        
        # 清理 GPU 缓存
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
        
        print("🗑️ OralGPT-omni 模型已卸载")
        return {"status": "success", "message": "模型已卸载，GPU 内存已释放"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"卸载模型失败: {str(e)}")


if __name__ == "__main__":
    import uvicorn
    import argparse
    
    parser = argparse.ArgumentParser(description="OralGPT-omni API 服务")
    parser.add_argument("--host", default="0.0.0.0", help="服务地址")
    parser.add_argument("--port", type=int, default=8004, help="服务端口")
    
    args = parser.parse_args()
    
    print(f"\n🚀 启动 OralGPT-omni API 服务")
    print(f"   地址: http://{args.host}:{args.port}")
    print(f"   文档: http://{args.host}:{args.port}/docs\n")
    
    uvicorn.run(
        app,
        host=args.host,
        port=args.port,
        log_level="info"
    )
