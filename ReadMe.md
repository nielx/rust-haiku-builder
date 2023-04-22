# Generic Build System for Cross-Compiling Rust for Haiku

This repository contains a Docker build file that cross-compiles rust from a github source for
Haiku.

## Usage

The build can be configured with the following build arguments:

| Argument                 | Description
| ------------------------ | ------------------------------------------------------------------------------------ |
| HAIKU_CROSS_COMPILER_TAG | The tag of the Haiku cross-compiler image. For example `x86_64-r1beta4`.             |
| RUST_REV                 | The git tag/branch to build from, e.g. `1.69.0` or `haiku-nightly`.                  |
| HAIKUPORTS_URL           | The base URL for the Haiku Ports package repository matching your compiler image.    |
| INSTALL_PACKAGES         | The packages that should be downloaded and installed from HaikuPorts for this build. |
| RUST_XPY_COMMAND         | The command passed to x.py, usually `build` or `dist`.                               |
| RUST_XPY_CONFIG          | The `config.toml` for the build, for example `configs/config-stable-x86.toml`        |

The example below builds the tag `rust-haiku-1.69.0` for the x86 platform, based on an Haiku
`r1beta4` cross compiler image. It uses a stable `config.toml`, and issues the `dist` command to
build the archive files that can be distributed onwards.

```bash
podman build --build-arg HAIKU_CROSS_COMPILER_TAG=x86_gcc2h-r1beta4 \
    --build-arg RUST_REV=rust-haiku-1.69.0 \
    --build-arg HAIKUPORTS_URL=https://eu.hpkg.haiku-os.org/haikuports/master/x86_gcc2/current/ \
    --build-arg INSTALL_PACKAGES="openssl_x86 openssl_x86_devel curl_x86 curl_x86_devel nghttp2_x86 nghttp2_x86_devel libssh2_x86 libssh2_x86_devel" \
    --build-arg RUST_XPY_COMMAND=dist \
    --build-arg RUST_XPY_CONFIG=configs/config-stable-x86.toml .
```

## Output

When running a `dist` build (meaning `RUST_XPY_COMMAND` is set to dist), all the packages will be
moved to `/output`.

The intermediate build artifacts are kept in `/build/rust`.
