FROM docker.io/haiku/cross-compiler:x86_64-r1beta4

ARG RUST_REV=haiku-beta
ARG RUST_REPO=https://github.com/nielx/rust

RUN mkdir /build

RUN wget https://eu.hpkg.haiku-os.org/haikuports/master/x86_64/current/packages/openssl-1.1.1s-2-x86_64.hpkg -P /build/ && \
    wget https://eu.hpkg.haiku-os.org/haikuports/master/x86_64/current/packages/openssl_devel-1.1.1s-2-x86_64.hpkg -P /build/ && \
    wget https://eu.hpkg.haiku-os.org/haikuports/master/x86_64/current/packages/curl-7.85.0-2-x86_64.hpkg -P /build/ && \
    wget https://eu.hpkg.haiku-os.org/haikuports/master/x86_64/current/packages/curl_devel-7.85.0-2-x86_64.hpkg -P /build/ && \
    wget https://eu.hpkg.haiku-os.org/haikuports/master/x86_64/current/packages/nghttp2-1.43.0-1-x86_64.hpkg -P /build/ && \
    wget https://eu.hpkg.haiku-os.org/haikuports/master/x86_64/current/packages/nghttp2_devel-1.43.0-1-x86_64.hpkg -P /build/ && \
    wget https://eu.hpkg.haiku-os.org/haikuports/master/x86_64/current/packages/libssh2-1.9.0-2-x86_64.hpkg -P /build/ && \
    wget https://eu.hpkg.haiku-os.org/haikuports/master/x86_64/current/packages/libssh2_devel-1.9.0-2-x86_64.hpkg -P /build/ && \
    find /build/ -name '*.hpkg' -exec package extract -C /system {} \;

RUN cd /build/ && git clone --depth=1 --branch $RUST_REV --shallow-submodules --recurse-submodules $RUST_REPO

COPY config.toml /build/rust/

RUN cd /build/rust/ && \
    X86_64_UNKNOWN_HAIKU_OPENSSL_LIB_DIR=/system/develop/lib/ \
    X86_64_UNKNOWN_HAIKU_OPENSSL_INCLUDE_DIR=/system/develop/headers/ \
    ./x.py -j 8 build

WORKDIR /build/rust/
