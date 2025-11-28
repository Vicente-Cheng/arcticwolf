# Earthfile

VERSION 0.8


common:
    FROM rust:1.91
    WORKDIR /src

    # Install xdrgen for XDR code generation
    RUN cargo install xdrgen

    # Copy Cargo files (Cargo.lock is optional, Earthly will ignore if missing)
    COPY Cargo.toml Cargo.lock* ./

    # Copy build script for XDR type generation
    COPY build.rs ./

    # Copy XDR protocol specifications
    COPY xdr ./xdr

    # Copy source code
    COPY src ./src

    # Pre-fetch dependencies to speed up subsequent builds
    RUN cargo fetch

# earthly +build
build:
    FROM +common
    RUN cargo build --release
    SAVE ARTIFACT target/release/arcticwolf AS LOCAL build/release/arcticwolf

# earthly +test
test:
    FROM +common
    RUN cargo test

# earthly +lint
lint:
    FROM +common
    RUN rustup component add clippy rustfmt
    RUN cargo fmt -- --check
    RUN cargo clippy -- -D warnings

# earthly +dev-image
dev-image:
    FROM +common
    RUN cargo build --release
    SAVE IMAGE nfs-like-server:dev
