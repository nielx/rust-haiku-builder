#!/bin/bash

. "$HOME/.cargo/env"

cd /build/rust/src/tools/cargo
echo "Forcing cargo workspace tempfile to pick 3.7.1 (over 3.7.0)"
cargo update -p tempfile --precise 3.7.1
echo "Forcing cargo workspace socket2 to downgrade to 0.4.1"
cargo update -p socket2 --precise 0.4.1