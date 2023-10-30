#!/bin/bash

. "$HOME/.cargo/env"

cd /build/rust
echo "Forcing global workspace libc to run at 0.2.143"
cargo update -p libc --precise 0.2.143

cd src/tools/cargo
echo "Forcing cargo workspace libc to run at 0.2.143"
cargo update -p libc --precise 0.2.143
echo "Forcing cargo workspace socket2 to downgrade to 0.4.1"
cargo update -p socket2 --precise 0.4.1
