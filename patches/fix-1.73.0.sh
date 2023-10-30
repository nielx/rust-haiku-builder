#!/bin/bash

. "$HOME/.cargo/env"

cd /build/rust/src/tools/cargo
echo "Forcing cargo dependency tempfile to pick 3.7.1 (over 3.7.0)"
cargo update -p tempfile --precise 3.7.1
