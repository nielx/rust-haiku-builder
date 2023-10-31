# Generic Build System for Cross-Compiling Rust for Haiku

This repository contains a Docker build file that cross-compiles rust from a github source for
Haiku.

## Usage

The build can be configured with the following build arguments:

| Argument                 | Description
| ------------------------ | ------------------------------------------------------------------------------------ |
| HAIKU_CROSS_COMPILER_TAG | The tag of the Haiku cross-compiler image. For example `x86_64-r1beta4`.             |
| RUST_REV                 | The git tag/branch to build from, e.g. `1.69.0` or `haiku-nightly`.                  |
| RUST_REPO                | The rust repository to check out.                                                    |
| HAIKUPORTS_URL           | The base URL for the Haiku Ports package repository matching your compiler image.    |
| INSTALL_PACKAGES         | The packages that should be downloaded and installed from HaikuPorts for this build. |
| SOURCE_FIXUP_SCRIPT      | A script that is run after the checkout is completed, usually to fix dependencies    |
| RUST_XPY_COMMAND         | The command passed to x.py, usually `build` or `dist`.                               |
| RUST_XPY_CONFIG          | The `config.toml` for the build, for example `configs/config-stable-x86.toml`        |

The example below builds the tag `1.73.0` for the x86 platform, based on an Haiku
`r1beta4` cross compiler image. It uses a stable `config.toml`, and issues the `dist` command to
build the archive files that can be distributed onwards.

```bash
podman build --build-arg HAIKU_CROSS_COMPILER_TAG=x86_gcc2h-r1beta4 \
    --build-arg RUST_REV=1.73.0 \
    --build-arg RUST_REPO=https://github.com/rust-lang/rust \
    --build-arg HAIKUPORTS_URL=https://eu.hpkg.haiku-os.org/haikuports/master/x86_gcc2/current/ \
    --build-arg INSTALL_PACKAGES="openssl_x86 openssl_x86_devel nghttp2_x86 nghttp2_x86_devel" \
    --build-arg SOURCE_FIXUP_SCRIPT=patches/fix-1.73.0.sh \
    --build-arg RUST_XPY_COMMAND=dist \
    --build-arg RUST_XPY_CONFIG=configs/config-stable-x86.toml \
    --tag rust-haiku-x86_gcc2h:1.73.0 .
```

## Artifacts

All build artifacts are kept in `/build/rust`. If you pass the parameter `dist` to
`RUST_XPY_COMMAND`, then the packages can be found in `/build/rust/build/dist`.

## Using the Rust Cross-Compiler

If building rustc for Haiku is successful, then the image will be set up to allow you to use the
generated cross-compiler. You can use cargo's `--target` parameter to compile for the Haiku target
that matches the platform the image is built for.

For example:

```bash
cargo build --target x86_64-unknown-haiku
```
