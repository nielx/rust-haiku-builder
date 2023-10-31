#!/bin/bash

. "$HOME/.cargo/env"

cd /build/rust/src/tools/cargo
echo "Forcing cargo workspace socket2 to downgrade to 0.4.1"
cargo update -p socket2 --precise 0.4.1
