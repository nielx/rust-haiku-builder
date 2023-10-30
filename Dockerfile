ARG HAIKU_CROSS_COMPILER_TAG=x86_64-r1beta4
FROM docker.io/haiku/cross-compiler:${HAIKU_CROSS_COMPILER_TAG}

ARG RUST_REV=haiku-nightly
ARG RUST_REPO=https://github.com/nielx/rust
ARG HAIKUPORTS_URL=https://eu.hpkg.haiku-os.org/haikuports/master/x86_64/current/
ARG INSTALL_PACKAGES="openssl openssl_devel curl curl_devel nghttp2 nghttp2_devel libssh2 libssh2_devel"
ARG SOURCE_FIXUP_SCRIPT=patches/noop.sh
ARG RUST_XPY_COMMAND=build
ARG RUST_XPY_CONFIG=configs/config-nightly-x86_64.toml

COPY tools/pkgman.py /pkgman.py

RUN python3 pkgman.py add-repo ${HAIKUPORTS_URL} && \
    python3 pkgman.py install ${INSTALL_PACKAGES}

RUN curl https://sh.rustup.rs -sSf | sh -s -- -y --profile minimal \
    && . "$HOME/.cargo/env"

RUN mkdir build && cd /build/ && git clone --depth=1 --branch ${RUST_REV} --shallow-submodules --recurse-submodules ${RUST_REPO}

COPY ${SOURCE_FIXUP_SCRIPT} /fixup.sh
RUN cd / && chmod a+x fixup.sh && ./fixup.sh

COPY ${RUST_XPY_CONFIG} /build/rust/config.toml

RUN cd /build/rust/ && \
    I686_UNKNOWN_HAIKU_OPENSSL_LIB_DIR=/system/develop/lib/x86 \
    I686_UNKNOWN_HAIKU_OPENSSL_INCLUDE_DIR=/system/develop/headers/ \
    X86_64_UNKNOWN_HAIKU_OPENSSL_LIB_DIR=/system/develop/lib/ \
    X86_64_UNKNOWN_HAIKU_OPENSSL_INCLUDE_DIR=/system/develop/headers/ \
    ./x.py -j 8 ${RUST_XPY_COMMAND}

RUN . "$HOME/.cargo/env" \
    && rustup toolchain link haiku-cross /build/rust/build/x86_64-unknown-linux-gnu/stage1 \
    && rustup default haiku-cross

WORKDIR /build/
