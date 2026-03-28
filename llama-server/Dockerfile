# Build llama.cpp with ROCm/gfx906 (Radeon VII)
# Pinned to ROCm 6.2.4 -- last version with reliable gfx906 support
FROM rocm/dev-ubuntu-24.04:6.2.4-complete AS builder
RUN apt-get update && apt-get install -y cmake git && rm -rf /var/lib/apt/lists/*
RUN git clone https://github.com/ggml-org/llama.cpp /llama.cpp && \
    cd /llama.cpp && \
    # Pin to pre-FP8 commit — llama.cpp HEAD (2026-03-26+) uses __hip_fp8_e4m3
    # which requires ROCm 6.3+, but we need 6.2.4 for gfx906 support.
    git checkout c0159f9c1f874da15e94f371d136f5920b4b5335 && \
    # ATLAS patch: prevent --embeddings from poisoning the draft model context.
    # Without this, embedding=true propagates to the draft via params_dft = params_base,
    # causing output_all=true and n_ubatch mismatch → 0% spec decode acceptance.
    sed -i '/auto params_dft = params_base;/a\        params_dft.embedding = false;  // ATLAS: draft never needs embeddings' \
        tools/server/server-context.cpp && \
    cmake -B build -DGGML_HIP=ON -DAMDGPU_TARGETS=gfx906 && \
    cmake --build build --target llama-server -j$(nproc)
# Smoke test: verify binary links against ROCm
RUN ldd /llama.cpp/build/bin/llama-server && /llama.cpp/build/bin/llama-server --help > /dev/null

FROM rocm/dev-ubuntu-24.04:6.2.4-complete
COPY --from=builder /llama.cpp/build/bin/llama-server /usr/local/bin/
COPY --from=builder /llama.cpp/build/bin/llama-cli /usr/local/bin/
# Copy shared libraries built by llama.cpp
COPY --from=builder /llama.cpp/build /tmp/llama-build/
RUN find /tmp/llama-build -name '*.so*' -exec cp {} /usr/local/lib/ \; && rm -rf /tmp/llama-build && ldconfig
RUN mkdir -p /models /templates
COPY templates/ /templates/
COPY entrypoint-v3-specdec.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh
ENV HSA_OVERRIDE_GFX_VERSION=9.0.6
EXPOSE 8000
ENTRYPOINT ["/entrypoint.sh"]
