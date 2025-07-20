# # Deploy a model with `lmdeploy`
#
# This script is used to deploy a model using [lmdeploy](https://github.com/InternLM/lmdeploy) with OpenAI compatible API.

import subprocess

import modal
from modal import App, Image, Secret

########## CONSTANTS ##########


# define model for serving and path to store in modal container
MODEL_NAME = "openbmb/MiniCPM-V-2_6"
MODEL_DIR = f"/models/{MODEL_NAME}"
SERVE_MODEL_NAME = "X"
HF_SECRET = Secret.from_name("huggingface-secret")
SECONDS = 60  # for timeout


########## UTILS FUNCTIONS ##########


def download_hf_model(model_dir: str, model_name: str):
    """Retrieve model from HuggingFace Hub and save into
    specified path within the modal container.

    Args:
        model_dir (str): Path to save model weights in container.
        model_name (str): HuggingFace Model ID.
    """
    import os

    from huggingface_hub import snapshot_download  # type: ignore

    os.makedirs(model_dir, exist_ok=True)

    snapshot_download(
        model_name,
        local_dir=model_dir,
        # consolidated.safetensors is prevent error here: https://github.com/vllm-project/vllm/pull/5005
        ignore_patterns=["*.pt", "*.bin", "consolidated.safetensors"],
        token=os.environ["HF_TOKEN"],
    )


########## IMAGE DEFINITION ##########

# define image for modal environment
lmdeploy_image = (
    Image.from_registry(
        "openmmlab/lmdeploy:v0.9.1-cu11",
    )
    .pip_install(["lmdeploy[all]", "huggingface_hub", "hf-transfer", "grpclib", "transformers"])
    .env({"HF_HUB_ENABLE_HF_TRANSFER": "1"})
    .run_function(
        download_hf_model,
        timeout=60 * SECONDS,
        kwargs={"model_dir": MODEL_DIR, "model_name": MODEL_NAME},
        secrets=[HF_SECRET],
    )
)

########## APP SETUP ##########


app = App(f"lmdeploy-{SERVE_MODEL_NAME}")



@app.function(
    image=lmdeploy_image,
    gpu="A100-40GB:1",
    scaledown_window=20 * SECONDS,
)
@modal.concurrent(max_inputs=256)  # https://modal.com/docs/guide/concurrent-inputs
@modal.web_server(port=23333, startup_timeout=60 * SECONDS)
def serve():
    cmd = f"""
    lmdeploy serve api_server {MODEL_DIR} \
        --model-name {SERVE_MODEL_NAME} \
        --server-port 23333 \
        --session-len 4092
    """
    subprocess.Popen(cmd, shell=True)