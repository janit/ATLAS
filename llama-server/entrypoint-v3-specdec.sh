#!/bin/bash
# V3: Generation + Self-Embeddings + Speculative Decoding (ROCm/Radeon VII)
#
# Requires ATLAS-patched llama-server (fix-embeddings-spec-decode.patch)
# that prevents --embeddings from poisoning the draft model context.
#
# Key: -b 4096 -ub 4096 keeps batch sizes equal, avoiding the n_batch
# clamp that --embeddings normally triggers. The patch ensures the draft
# model context is created WITHOUT embedding=true.
#
# Expected throughput: ~60-80 tok/s (with spec decode on Radeon VII)
# VRAM: ~6.5GB main + ~1.0GB draft + ~0.9GB draft KV + ~0.7GB main KV = ~9.5GB / 16GB
#
# Draft context (-cd): Reduced from 16384 to match main per-slot context (8192)
# to fit within 16GB VRAM. Draft needs full preceding context for spec decode.

SLOT_SAVE_PATH="${SLOT_SAVE_PATH:-/tmp/slots}"
mkdir -p "$SLOT_SAVE_PATH"

CTX_LENGTH="${CONTEXT_LENGTH:-16384}"
DRAFT_CTX="${DRAFT_CTX_LENGTH:-8192}"
KV_CACHE_TYPE="${KV_CACHE_TYPE:-q4_0}"
KV_FLAGS="-ctk $KV_CACHE_TYPE -ctv $KV_CACHE_TYPE"
TEMPLATE="${CHAT_TEMPLATE:-Qwen3-custom.jinja}"
PARALLEL="${PARALLEL_SLOTS:-1}"
DRAFT_MODEL="${DRAFT_MODEL:-/models/Qwen3-0.6B-Q8_0.gguf}"

# ROCm environment (replaces CUDA vars from upstream)
export HSA_OVERRIDE_GFX_VERSION="${HSA_OVERRIDE_GFX_VERSION:-9.0.6}"

echo "=== V3: Generation + Self-Embeddings + Speculative Decoding (ROCm) ==="
echo "  Context: $CTX_LENGTH (draft: $DRAFT_CTX) | KV: $KV_CACHE_TYPE | Parallel: $PARALLEL"
echo "  Embeddings: ENABLED (5120-dim Qwen3 self-embeddings)"
echo "  Draft model: $DRAFT_MODEL"
echo "  Slot save path: $SLOT_SAVE_PATH"
echo "  HSA_OVERRIDE_GFX_VERSION: $HSA_OVERRIDE_GFX_VERSION"

exec /usr/local/bin/llama-server \
  -m /models/Qwen3-14B-Q4_K_M.gguf \
  --model-draft "$DRAFT_MODEL" \
  -c $CTX_LENGTH \
  -cd $DRAFT_CTX \
  $KV_FLAGS \
  --parallel $PARALLEL \
  --cont-batching \
  -ngl 99 \
  --host 0.0.0.0 \
  --port 8000 \
  --flash-attn on \
  --mlock \
  --no-mmap \
  -b 4096 \
  -ub 4096 \
  --slot-save-path "$SLOT_SAVE_PATH" \
  --embeddings
