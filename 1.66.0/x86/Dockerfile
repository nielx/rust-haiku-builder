FROM docker.io/haiku/cross-compiler:x86_gcc2h-r1beta4

ARG RUST_REV=rust-haiku-1.66.0
ARG RUST_REPO=https://github.com/nielx/rust

RUN mkdir /build

RUN wget https://eu.hpkg.haiku-os.org/haikuports/master/x86_gcc2/current/packages/openssl_x86-1.1.1s-2-x86_gcc2.hpkg -P /build/ && \
    wget https://eu.hpkg.haiku-os.org/haikuports/master/x86_gcc2/current/packages/openssl_x86_devel-1.1.1s-2-x86_gcc2.hpkg -P /build/ && \
    wget https://eu.hpkg.haiku-os.org/haikuports/master/x86_gcc2/current/packages/curl_x86-7.85.0-2-x86_gcc2.hpkg -P /build/ && \
    wget https://eu.hpkg.haiku-os.org/haikuports/master/x86_gcc2/current/packages/curl_x86_devel-7.85.0-2-x86_gcc2.hpkg -P /build/ && \
    wget https://eu.hpkg.haiku-os.org/haikuports/master/x86_gcc2/current/packages/nghttp2_x86-1.43.0-1-x86_gcc2.hpkg -P /build/ && \
    wget https://eu.hpkg.haiku-os.org/haikuports/master/x86_gcc2/current/packages/nghttp2_x86_devel-1.43.0-1-x86_gcc2.hpkg -P /build/ && \
    wget https://eu.hpkg.haiku-os.org/haikuports/master/x86_gcc2/current/packages/libssh2_x86-1.9.0-2-x86_gcc2.hpkg -P /build/ && \
    wget https://eu.hpkg.haiku-os.org/haikuports/master/x86_gcc2/current/packages/libssh2_x86_devel-1.9.0-2-x86_gcc2.hpkg -P /build/ && \
    find /build/ -name '*.hpkg' -exec package extract -C /system {} \;

RUN cd /build/ && git clone --depth=1 --branch $RUST_REV --shallow-submodules --recurse-submodules $RUST_REPO

COPY config.toml /build/rust/

RUN cd /build/rust/ && \
    I686_UNKNOWN_HAIKU_OPENSSL_LIB_DIR=/system/develop/lib/x86 \
    I686_UNKNOWN_HAIKU_OPENSSL_INCLUDE_DIR=/system/develop/headers/ \
    ./x.py -j 8 dist

RUN mkdir /output/ && mv /build/rust/build/dist/* /output && rm -rf /build/

WORKDIR /output/
