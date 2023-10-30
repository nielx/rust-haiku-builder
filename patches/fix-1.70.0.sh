#!/bin/bash

. "$HOME/.cargo/env"

cd /build/rust
echo "Forcing global workspace libc to run at 0.2.143"
cargo update -p libc --precise 0.2.143

echo "Forcing curl-sys to update to 0.4.63+curl-8.1.2"
cargo update -p curl-sys --precise 0.4.63+curl-8.1.2
