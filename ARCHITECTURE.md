# Arctic Wolf NFS Server - Architecture

## Overview

Arctic Wolf is an NFS (Network File System) server implementation in Rust, providing NFSv3 and MOUNT protocol support with a clean, layered architecture inspired by [NFS-Ganesha](https://github.com/nfs-ganesha/nfs-ganesha).

## Design Principles

1. **Protocol Definition Separation**: XDR protocol specifications are centralized and separate from implementation
2. **Layered Architecture**: Clear separation between protocol, middleware, and business logic
3. **Type Safety**: Leverage Rust's type system with XDR-generated types
4. **One Operation Per File**: Each protocol operation in its own module for maintainability
5. **Version Isolation**: Different protocol versions are cleanly separated

## Directory Structure

```
arcticwolf/
├── xdr/                        # XDR Protocol Specifications (inspired by nfs-ganesha/Protocols/XDR)
│   ├── v3/                     # NFSv3 and related protocols
│   │   ├── rpc.x              # RPC protocol (RFC 5531)
│   │   ├── mount.x            # MOUNT protocol (RFC 1813)
│   │   └── nfs.x              # NFSv3 protocol (RFC 1813)
│   └── v4/                     # NFSv4 (future)
│       └── nfs.x
│
├── src/
│   ├── protocol/              # Protocol Middleware Layer
│   │   ├── mod.rs
│   │   └── v3/
│   │       ├── mod.rs
│   │       ├── rpc.rs         # RPC type wrappers + serialization helpers
│   │       ├── mount.rs       # MOUNT type wrappers + helpers
│   │       └── nfs.rs         # NFS type wrappers + helpers
│   │
│   ├── rpc/                   # RPC Implementation Layer
│   │   ├── mod.rs
│   │   └── server.rs          # TCP server + record marking (RFC 5531)
│   │
│   ├── mount/                 # MOUNT Protocol Handlers (future)
│   │   ├── mod.rs
│   │   ├── null.rs            # MOUNT NULL procedure
│   │   ├── mnt.rs             # MOUNT MNT procedure
│   │   └── umnt.rs            # MOUNT UMNT procedure
│   │
│   ├── nfs/                   # NFS Protocol Handlers (future)
│   │   ├── mod.rs
│   │   └── v3/
│   │       ├── mod.rs
│   │       ├── null.rs        # NFS NULL procedure
│   │       ├── getattr.rs     # GETATTR operation
│   │       ├── setattr.rs     # SETATTR operation
│   │       ├── lookup.rs      # LOOKUP operation
│   │       ├── read.rs        # READ operation
│   │       └── write.rs       # WRITE operation
│   │
│   ├── fsal/                  # Filesystem Abstraction Layer (future)
│   │   ├── mod.rs
│   │   └── local.rs           # Local filesystem backend
│   │
│   └── main.rs                # Server entry point
│
├── build.rs                   # XDR code generation (xdrgen)
├── Cargo.toml                 # Dependencies
├── Earthfile                  # Containerized build
├── tests/                     # Integration tests
│   ├── test_rpc_null.py      # RPC NULL test
│   └── README.md
└── ARCHITECTURE.md            # This file
```

## Architecture Layers

### Layer 1: XDR Protocol Specifications (`xdr/`)

**Purpose**: RFC-compliant protocol definitions in XDR (External Data Representation) format.

**Characteristics**:
- Pure data structure definitions
- Version-specific (v3/, v4/)
- Machine-readable, generates Rust code
- Single source of truth for protocol types

**Example** (`xdr/v3/rpc.x`):
```xdr
struct rpc_call_msg {
    unsigned int xid;
    unsigned int rpcvers;
    unsigned int prog;
    unsigned int vers;
    unsigned int proc;
    opaque_auth cred;
    opaque_auth verf;
};
```

**Build Process**:
```
xdr/v3/rpc.x → (xdrgen) → target/.../rpc_generated.rs
```

### Layer 2: Protocol Middleware (`src/protocol/`)

**Purpose**: Wraps generated XDR types with Rust-friendly interfaces and serialization helpers.

**Responsibilities**:
- Include XDR-generated types
- Provide serialization/deserialization methods
- Offer convenience constructors for responses
- Re-export types for use by upper layers

**Example** (`src/protocol/v3/rpc.rs`):
```rust
pub struct RpcMessage;

impl RpcMessage {
    // Deserialize RPC call from bytes
    pub fn deserialize_call(data: &[u8]) -> Result<rpc_call_msg> {
        let (msg, _) = rpc_call_msg::unpack(&mut Cursor::new(data))?;
        Ok(msg)
    }

    // Serialize RPC reply to bytes
    pub fn serialize_reply(reply: &rpc_reply_msg) -> Result<BytesMut> {
        let mut buf = Vec::new();
        reply.pack(&mut buf)?;
        Ok(BytesMut::from(&buf[..]))
    }

    // Create a successful NULL reply
    pub fn create_null_reply(xid: u32) -> rpc_reply_msg {
        // ...
    }
}
```

**Key Features**:
- Type-safe wrappers
- Automatic serialization via `xdr-codec` traits (`Pack`/`Unpack`)
- Convenience methods for common operations

### Layer 3: RPC Implementation (`src/rpc/`)

**Purpose**: TCP server handling and RPC record marking protocol.

**Responsibilities**:
- Accept TCP connections
- Handle RPC record marking (RFC 5531 §11)
- Parse RPC messages
- Route to procedure handlers
- Send formatted responses

**Record Marking Protocol**:
```
[last:1bit][length:31bits][fragment_data]
```

**Example** (`src/rpc/server.rs`):
```rust
async fn handle_connection(mut socket: TcpStream) -> Result<()> {
    loop {
        // Read record marking header (4 bytes)
        let header_u32 = socket.read_u32().await?;
        let is_last = (header_u32 & 0x80000000) != 0;
        let fragment_len = (header_u32 & 0x7FFFFFFF) as usize;

        // Read fragment
        // Process complete RPC message if last fragment
        // Route to handler
        // Send response
    }
}
```

### Layer 4: Protocol Handlers (`src/mount/`, `src/nfs/`)

**Purpose**: Business logic for individual protocol operations.

**Design**: One operation per file (following nfs-ganesha pattern).

**Example Structure** (future implementation):
```rust
// src/nfs/v3/getattr.rs
pub async fn handle_getattr(args: GETATTR3args) -> Result<GETATTR3res> {
    // 1. Validate file handle
    // 2. Call FSAL to get attributes
    // 3. Convert FSAL attributes to NFS format
    // 4. Return response
}
```

### Layer 5: Filesystem Abstraction (`src/fsal/`)

**Purpose**: Abstract different filesystem backends.

**Future Implementation**:
- `fsal/local.rs`: Local filesystem operations
- `fsal/memory.rs`: In-memory filesystem (testing)
- `fsal/s3.rs`: S3 backend
- Common trait for all backends

## Data Flow

### RPC NULL Call Example

```
Client
  ↓ TCP (port 4000)
[RPC Server: server.rs]
  ↓ Read record marking
  ↓ Parse RPC message
[Protocol Middleware: protocol::v3::rpc]
  ↓ Deserialize call (xdr-codec::Unpack)
  ↓ rpc_call_msg { xid, prog, proc, ... }
[Handler: handle_null_procedure]
  ↓ Create reply
  ↓ rpc_reply_msg { xid, stat: MSG_ACCEPTED, ... }
[Protocol Middleware]
  ↓ Serialize reply (xdr-codec::Pack)
[RPC Server]
  ↓ Add record marking
  ↓ Send TCP response
Client
```

### Future MOUNT/NFS Call Flow

```
Client
  ↓
[RPC Server]
  ↓ Parse RPC call
  ↓ Route by program number
[Dispatcher]
  ├── prog=100005 → [MOUNT Handler]
  │   ├── proc=0 → mount::null()
  │   ├── proc=1 → mount::mnt()
  │   └── proc=3 → mount::umnt()
  │
  └── prog=100003 → [NFS Handler]
      ├── proc=0 → nfs::v3::null()
      ├── proc=1 → nfs::v3::getattr()
      ├── proc=3 → nfs::v3::lookup()
      ├── proc=6 → nfs::v3::read()
      └── proc=7 → nfs::v3::write()
          ↓
      [FSAL: Filesystem Abstraction]
          ↓
      [Local Filesystem / S3 / Memory]
```

## Technology Stack

### Core Dependencies

| Component | Library | Version | Purpose |
|-----------|---------|---------|---------|
| **Async Runtime** | `tokio` | 1.x | Async TCP server, concurrency |
| **XDR Codegen** | `xdrgen` | 0.4 | Generate Rust types from .x files |
| **XDR Runtime** | `xdr-codec` | 0.4 | Pack/Unpack traits for serialization |
| **Error Handling** | `anyhow` | 1.0 | Ergonomic error propagation |
| **Logging** | `tracing` | 0.1 | Structured logging |
| **Bytes** | `bytes` | 1.5 | Efficient byte buffer management |

### Build Tools

- **xdrgen**: CLI tool for XDR→Rust code generation (installed via `cargo install xdrgen`)
- **build.rs**: Runs xdrgen during compilation
- **Earthly**: Containerized builds for reproducibility

## XDR Code Generation

### Process

1. Developer writes/modifies `.x` files in `xdr/v3/`
2. `build.rs` runs `xdrgen` for each `.x` file
3. Generated Rust code → `target/.../[protocol]_generated.rs`
4. Protocol middleware includes generated code via `include!()` macro
5. Upper layers use types through middleware exports

### Example Generation

**Input** (`xdr/v3/mount.x`):
```xdr
typedef string dirpath<MNTPATHLEN>;
typedef opaque fhandle3<FHSIZE3>;

enum mountstat3 {
    MNT3_OK = 0,
    MNT3ERR_PERM = 1,
    // ...
};

union mountres3 switch (mountstat3 fhs_status) {
    case MNT3_OK:
        mountres3_ok mountinfo;
    default:
        void;
};
```

**Output** (generated Rust):
```rust
pub struct dirpath(pub String);
pub struct fhandle3(pub Vec<u8>);

pub enum mountstat3 {
    MNT3_OK = 0,
    MNT3ERR_PERM = 1,
    // ...
}

pub enum mountres3 {
    MNT3_OK(mountres3_ok),
    default,
}

impl Pack for mountres3 { ... }
impl Unpack for mountres3 { ... }
```

### Why xdrgen + xdr-codec?

**Advantages over alternatives**:
- ✅ **Full XDR Support**: `string`, `union`, variable-length arrays
- ✅ **Automatic Serialization**: `Pack`/`Unpack` traits generated
- ✅ **RFC Compliant**: Follows RFC 4506 (XDR) and RFC 5531 (RPC)
- ✅ **Active Maintenance**: Used by Stellar project
- ✅ **Rust Idiomatic**: Generates standard Rust types

**Previous Attempt**: `fastxdr`
- ❌ Limited `string` support
- ❌ No `union` support
- ❌ Incomplete variable-length arrays
- ✅ Manual serialization required

## Protocol Support

### Current Implementation

| Protocol | Version | RFC | Status | Port |
|----------|---------|-----|--------|------|
| RPC | 2 | RFC 5531 | ✅ NULL procedure | - |
| MOUNT | 3 | RFC 1813 | 🚧 In progress | - |
| NFS | 3 | RFC 1813 | 🚧 Planned | - |

### Procedure Support

#### RPC (Program 100000)
- [x] NULL (0) - Ping test

#### MOUNT (Program 100005)
- [ ] NULL (0) - Ping test
- [ ] MNT (1) - Mount directory
- [ ] UMNT (3) - Unmount directory

#### NFSv3 (Program 100003)
- [ ] NULL (0) - Ping test
- [ ] GETATTR (1) - Get file attributes
- [ ] SETATTR (2) - Set file attributes
- [ ] LOOKUP (3) - Look up filename
- [ ] READ (6) - Read from file
- [ ] WRITE (7) - Write to file
- [ ] CREATE (8) - Create file
- [ ] MKDIR (9) - Create directory
- [ ] READDIR (16) - Read directory entries

## Design Decisions

### Why Centralize XDR Files in `xdr/`?

**Inspired by**: NFS-Ganesha's `src/Protocols/XDR/` directory

**Benefits**:
1. **Single Source of Truth**: All protocol definitions in one place
2. **Clear Separation**: Protocol specs vs. implementation
3. **Version Management**: Easy to see v3 vs. v4 differences
4. **Build Simplification**: One place to run code generation
5. **Future Extensibility**: Can support multiple generators (xdrgen, rpcgen, custom)

### Why One Operation Per File?

**Inspired by**: NFS-Ganesha's pattern (`nfs3_getattr.c`, `nfs4_op_read.c`)

**Benefits**:
1. **Easy Navigation**: `git grep "GETATTR"` → one file
2. **Clear Git History**: Changes to READ don't pollute WRITE history
3. **Parallel Development**: Different team members work on different operations
4. **Focused Testing**: Unit tests per operation
5. **Code Review**: Smaller, focused diffs

### Why Protocol Middleware Layer?

**Purpose**: Bridge between raw XDR types and business logic

**Without Middleware** (hypothetical):
```rust
// Handler directly uses generated types - messy!
use target::..::rpc_generated::*;  // ❌ Ugly path
let (msg, _) = rpc_call_msg::unpack(&mut cursor)?;  // ❌ Repeated everywhere
```

**With Middleware**:
```rust
use crate::protocol::v3::RpcMessage;  // ✅ Clean import
let msg = RpcMessage::deserialize_call(data)?;  // ✅ Ergonomic API
```

**Additional Benefits**:
- Type conversions (e.g., `fhandle3(Vec<u8>)` ↔ internal handle)
- Validation before reaching handlers
- Logging/tracing instrumentation points
- Future: metrics collection

## Testing

### Current Tests

**RPC NULL Test** (`tests/test_rpc_null.py`):
```python
# Sends: RPC call with record marking
# XID: 12345, Program: 100003, Version: 3, Procedure: 0

# Expects: RPC reply
# XID: 12345, Status: MSG_ACCEPTED, Accept: SUCCESS
```

**Run Tests**:
```bash
# Start server
cargo run

# Run test (separate terminal)
python3 tests/test_rpc_null.py
```

### Future Testing Strategy

1. **Unit Tests**: Per-operation handlers (`src/nfs/v3/getattr_test.rs`)
2. **Integration Tests**: Full RPC→FSAL flow
3. **Compliance Tests**: RFC 1813 test suite
4. **Performance Tests**: Throughput, latency benchmarks
5. **Compatibility Tests**: Real NFS clients (Linux mount, macOS, Windows)

## Build & Development

### Local Development

```bash
# Install xdrgen (one-time)
cargo install xdrgen

# Build
cargo build

# Run
cargo run

# Test
cargo test

# Test RPC NULL
python3 tests/test_rpc_null.py
```

### Docker Build (Earthly)

```bash
# Full build
make build

# Output: build/release/arcticwolf
./build/release/arcticwolf
```

### Adding a New NFS Operation

1. **Update XDR** (if needed): `xdr/v3/nfs.x`
2. **Add Handler**: `src/nfs/v3/operation_name.rs`
3. **Register in Dispatcher**: `src/nfs/v3/mod.rs`
4. **Add Test**: `tests/test_nfs_operation.py`
5. **Update Docs**: This file

## Future Roadmap

### Phase 1: MOUNT Protocol ✅ RPC NULL
- [x] RPC server with record marking
- [x] RPC NULL procedure
- [ ] MOUNT NULL procedure
- [ ] MOUNT MNT procedure (return file handle)
- [ ] MOUNT UMNT procedure

### Phase 2: NFSv3 Core Operations
- [ ] NFS NULL procedure
- [ ] GETATTR (file attributes)
- [ ] LOOKUP (filename to file handle)
- [ ] READ (read file data)
- [ ] WRITE (write file data)

### Phase 3: FSAL (Filesystem Abstraction)
- [ ] Local filesystem backend
- [ ] In-memory filesystem (testing)
- [ ] Handle mapping (file handle ↔ inode)
- [ ] Permission checking

### Phase 4: NFSv3 Complete
- [ ] CREATE, MKDIR, REMOVE, RMDIR
- [ ] READDIR, READDIRPLUS
- [ ] SYMLINK, READLINK
- [ ] COMMIT, FSSTAT, FSINFO

### Phase 5: NFSv4 Support
- [ ] New XDR specs in `xdr/v4/`
- [ ] Compound operations
- [ ] Stateful protocol
- [ ] Delegation

## References

### RFCs
- [RFC 5531](https://www.rfc-editor.org/rfc/rfc5531): RPC Protocol Specification Version 2
- [RFC 4506](https://www.rfc-editor.org/rfc/rfc4506): XDR: External Data Representation Standard
- [RFC 1813](https://www.rfc-editor.org/rfc/rfc1813): NFS Version 3 Protocol Specification
- [RFC 7530](https://www.rfc-editor.org/rfc/rfc7530): NFSv4 Protocol

### Inspirations
- [NFS-Ganesha](https://github.com/nfs-ganesha/nfs-ganesha): Production NFS server in C
- [nfs-server-rs](https://github.com/xetdata/nfs-server-rs): Rust NFS implementation
- [rust-xdr](https://github.com/jsgf/rust-xdr): xdrgen and xdr-codec libraries

### Crates
- [xdrgen](https://crates.io/crates/xdrgen): XDR code generator
- [xdr-codec](https://crates.io/crates/xdr-codec): XDR serialization runtime
- [tokio](https://tokio.rs/): Async runtime

## Contributing

### Code Style
- Follow Rust idioms and naming conventions
- One operation per file
- Document public APIs
- Add unit tests for new operations
- Run `cargo fmt` and `cargo clippy` before committing

### Architecture Changes
- Discuss in issues before major refactoring
- Keep layers separate and well-defined
- Maintain backwards compatibility with NFSv3 RFC

---

**Last Updated**: 2025-12-02
**Version**: 0.1.0 - Initial RPC NULL implementation complete
