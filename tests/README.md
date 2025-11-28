# Arctic Wolf NFS Server - Testing Guide

## Overview

This directory contains integration tests for the Arctic Wolf NFS server. Tests verify protocol compliance, message handling, and end-to-end functionality.

## Current Test Coverage

### Phase 1: RPC NULL Call ✅

**Status**: Complete
**Purpose**: Verify basic RPC infrastructure

**What it tests**:
1. TCP connection handling
2. RPC record marking protocol (RFC 5531 §11)
3. XDR message deserialization (using xdrgen + xdr-codec)
4. RPC NULL procedure handler
5. XDR message serialization
6. RPC record marking response

## Running Tests

### Prerequisites

```bash
# Install dependencies
pip3 install socket struct

# Ensure xdrgen is installed (for development)
cargo install xdrgen
```

### Quick Start

```bash
# Terminal 1: Start server
cargo run

# Terminal 2: Run tests
python3 tests/test_rpc_null.py
```

### Using Docker Build

```bash
# Build with Earthly
make build

# Run server
./build/release/arcticwolf

# Run tests (separate terminal)
python3 tests/test_rpc_null.py
```

## Test Details

### RPC NULL Test (`test_rpc_null.py`)

**Objective**: Verify RPC layer functionality

**Test Flow**:
```
Client (Python)
  ↓ 1. Create RPC NULL call message
  ↓ 2. Add record marking header
  ↓ 3. Send via TCP to localhost:4000
Server (Rust)
  ↓ 4. Accept connection
  ↓ 5. Parse record marking
  ↓ 6. Deserialize RPC call (xdr-codec::Unpack)
  ↓ 7. Route to NULL handler
  ↓ 8. Create reply message
  ↓ 9. Serialize reply (xdr-codec::Pack)
  ↓ 10. Add record marking
  ↓ 11. Send response
Client
  ↓ 12. Receive and validate response
  ✅ Success!
```

**Expected Output**:
```
Sending RPC NULL call to localhost:4000
  XID: 12345
  Program: 100003, Version: 3, Procedure: 0
  Message size: 36 bytes
  Message (hex): 0000303900000002000186a3000000030000000000000000000000000000000000000000

Waiting for response...
Response fragment: last=True, length=20
Response (hex): 0000303900000000000000000000000000000000

Parsed response:
  XID: 12345 (expected 12345)
  Reply stat: 0 (0=MSG_ACCEPTED)
  Verf flavor: 0 (0=AUTH_NONE)
  Verf length: 0
  Accept stat: 0 (0=SUCCESS)

✅ RPC NULL call succeeded!
```

**Server Logs** (with `RUST_LOG=debug`):
```
2025-12-02T10:00:00.000Z INFO  rpc::server] RPC server listening on 0.0.0.0:4000
2025-12-02T10:00:01.234Z INFO  rpc::server] New connection from 127.0.0.1:54321
2025-12-02T10:00:01.235Z DEBUG rpc::server] Record marking: last=true, length=36
2025-12-02T10:00:01.236Z DEBUG rpc::server] Complete RPC message received (36 bytes)
2025-12-02T10:00:01.237Z DEBUG rpc::server] RPC call: xid=12345, prog=100003, vers=3, proc=0
2025-12-02T10:00:01.238Z DEBUG rpc::server] Handling NULL procedure for xid=12345
2025-12-02T10:00:01.239Z DEBUG rpc::server] Sent response (20 bytes)
```

## Protocol Details

### RPC Message Structure

**Call Message** (36 bytes):
```
┌─────────────────────────────────────────────────────────────────────┐
│ RPC Call Message (XDR Format)                                      │
├──────────┬──────────────┬───────────┬──────────────────────────────┤
│ Offset   │ Field        │ Value     │ Description                  │
├──────────┼──────────────┼───────────┼──────────────────────────────┤
│ 0-3      │ xid          │ 12345     │ Transaction ID               │
│ 4-7      │ rpcvers      │ 2         │ RPC version (always 2)       │
│ 8-11     │ prog         │ 100003    │ Program (NFS)                │
│ 12-15    │ vers         │ 3         │ Version (NFSv3)              │
│ 16-19    │ proc         │ 0         │ Procedure (NULL)             │
│ 20-23    │ cred.flavor  │ 0         │ AUTH_NONE                    │
│ 24-27    │ cred.length  │ 0         │ No credentials               │
│ 28-31    │ verf.flavor  │ 0         │ AUTH_NONE                    │
│ 32-35    │ verf.length  │ 0         │ No verifier                  │
└──────────┴──────────────┴───────────┴──────────────────────────────┘
```

**Reply Message** (20 bytes):
```
┌─────────────────────────────────────────────────────────────────────┐
│ RPC Reply Message (XDR Format)                                     │
├──────────┬──────────────┬───────────┬──────────────────────────────┤
│ Offset   │ Field        │ Value     │ Description                  │
├──────────┼──────────────┼───────────┼──────────────────────────────┤
│ 0-3      │ xid          │ 12345     │ Same as request              │
│ 4-7      │ reply_stat   │ 0         │ MSG_ACCEPTED                 │
│ 8-11     │ verf.flavor  │ 0         │ AUTH_NONE                    │
│ 12-15    │ verf.length  │ 0         │ No verifier                  │
│ 16-19    │ accept_stat  │ 0         │ SUCCESS                      │
└──────────┴──────────────┴───────────┴──────────────────────────────┘
```

### RPC Record Marking (RFC 5531 §11)

**Purpose**: Frame RPC messages over TCP streams

**Format**:
```
┌────────────────────────────┬──────────────────────────────────┐
│ Fragment Header (4 bytes)  │ Fragment Data (N bytes)          │
└────────────────────────────┴──────────────────────────────────┘
       │
       └─> [L:1bit][Length:31bits]
           │
           └─> L=1: Last fragment
               L=0: More fragments follow
```

**Examples**:
- `0x80000024` = Last fragment, 36 bytes
  - Binary: `1000 0000 0000 0000 0000 0000 0010 0100`
  - Last bit = 1, Length = 0x24 = 36
- `0x00000100` = Not last, 256 bytes (more to come)
  - Binary: `0000 0000 0000 0000 0000 0001 0000 0000`
  - Last bit = 0, Length = 0x100 = 256

**Multi-fragment Example**:
```
Message 1: [0x00000100][...256 bytes...]  ← More fragments
Message 2: [0x00000080][...128 bytes...]  ← More fragments
Message 3: [0x80000040][...64 bytes...]   ← Last fragment
Total: 256 + 128 + 64 = 448 bytes
```

### XDR Code Generation

The server uses **xdrgen** to generate Rust types from XDR specifications:

**Source** (`xdr/v3/rpc.x`):
```xdr
struct rpc_call_msg {
    unsigned int xid;
    unsigned int rpcvers;
    unsigned int prog;
    unsigned int vers;
    unsigned int proc_;
    opaque_auth cred;
    opaque_auth verf;
};
```

**Generated** (`target/.../rpc_generated.rs`):
```rust
pub struct rpc_call_msg {
    pub xid: u32,
    pub rpcvers: u32,
    pub prog: u32,
    pub vers: u32,
    pub proc_: u32,
    pub cred: opaque_auth,
    pub verf: opaque_auth,
}

impl Pack for rpc_call_msg { ... }
impl Unpack for rpc_call_msg { ... }
```

## Architecture Integration

### Where Tests Fit

```
┌─────────────────────────────────────────────────────────────────┐
│ Python Test Script (tests/test_rpc_null.py)                    │
└───────────────────────┬─────────────────────────────────────────┘
                        │ TCP Socket
                        ↓
┌─────────────────────────────────────────────────────────────────┐
│ RPC Server (src/rpc/server.rs)                                  │
│  • Accept connections                                           │
│  • Parse record marking                                         │
│  • Route to handlers                                            │
└───────────────────────┬─────────────────────────────────────────┘
                        │
                        ↓
┌─────────────────────────────────────────────────────────────────┐
│ Protocol Middleware (src/protocol/v3/rpc.rs)                    │
│  • RpcMessage::deserialize_call()                               │
│  • RpcMessage::serialize_reply()                                │
│  • Uses xdr-codec Pack/Unpack traits                            │
└───────────────────────┬─────────────────────────────────────────┘
                        │
                        ↓
┌─────────────────────────────────────────────────────────────────┐
│ XDR Generated Types (target/.../rpc_generated.rs)               │
│  • rpc_call_msg, rpc_reply_msg, etc.                            │
│  • Generated from xdr/v3/rpc.x by xdrgen                        │
└─────────────────────────────────────────────────────────────────┘
```

## Debugging

### Enable Debug Logging

```bash
# Full debug output
RUST_LOG=debug cargo run

# Specific module
RUST_LOG=rpc::server=debug cargo run

# Trace level (very verbose)
RUST_LOG=trace cargo run
```

### Capture Network Traffic

```bash
# Capture on localhost (loopback)
sudo tcpdump -i lo -X port 4000

# Save to file
sudo tcpdump -i lo -w nfs-capture.pcap port 4000

# View with Wireshark
wireshark nfs-capture.pcap
```

### Manual Testing with netcat

```bash
# Send raw RPC NULL call
echo "800000240000303900000002000186a3000000030000000000000000000000000000000000000000" \
  | xxd -r -p | nc localhost 4000 | xxd

# Expected output (hex dump of reply):
# 80000014 00003039 00000000 00000000 00000000
```

### Manual Testing with Python

```python
import socket
import struct

# Connect
sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
sock.connect(('localhost', 4000))

# Build RPC NULL call
xid = 12345
call = struct.pack('>IIIIIII II',
    xid, 2, 100003, 3, 0,  # RPC header
    0, 0,                   # cred (AUTH_NONE, length 0)
    0, 0)                   # verf (AUTH_NONE, length 0)

# Add record marking (last=1, length=36)
header = struct.pack('>I', 0x80000024)

# Send
sock.sendall(header + call)

# Receive
reply_header = sock.recv(4)
last, length = struct.unpack('>I', reply_header)[0] >> 31, \
               struct.unpack('>I', reply_header)[0] & 0x7FFFFFFF
reply_data = sock.recv(length)

print(f"Reply: last={last}, length={length}")
print(f"Data: {reply_data.hex()}")
```

## Future Tests

### Phase 2: MOUNT Protocol
- [ ] MOUNT NULL procedure
- [ ] MOUNT MNT procedure (get file handle)
- [ ] MOUNT UMNT procedure (unmount)
- [ ] MOUNT error handling

### Phase 3: NFSv3 Core
- [ ] NFS NULL procedure
- [ ] GETATTR (file attributes)
- [ ] LOOKUP (name to file handle)
- [ ] READ (file data)
- [ ] WRITE (file data)

### Phase 4: NFSv3 Extended
- [ ] CREATE, MKDIR, REMOVE, RMDIR
- [ ] READDIR, READDIRPLUS
- [ ] SYMLINK, READLINK
- [ ] COMMIT, FSSTAT, FSINFO

### Integration Tests
- [ ] Multi-operation compound tests
- [ ] Concurrent client handling
- [ ] Error recovery scenarios
- [ ] Large file handling
- [ ] Permission checks

### Compliance Tests
- [ ] RFC 1813 test suite
- [ ] Interoperability with Linux NFS client
- [ ] Interoperability with macOS NFS client
- [ ] Interoperability with Windows NFS client

### Performance Tests
- [ ] Throughput benchmarks
- [ ] Latency measurements
- [ ] Concurrent connection handling
- [ ] Large directory listing
- [ ] File cache effectiveness

## Writing New Tests

### Test Template

```python
#!/usr/bin/env python3
"""
Test: <Operation Name>
Purpose: <What this test verifies>
"""

import socket
import struct

def test_<operation>():
    # 1. Connect to server
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.connect(('localhost', 4000))

    # 2. Build request message
    # ...

    # 3. Add record marking
    # ...

    # 4. Send request
    # ...

    # 5. Receive and validate response
    # ...

    # 6. Assert expectations
    assert reply_xid == request_xid
    assert status == EXPECTED_STATUS

    sock.close()
    print("✅ Test passed!")

if __name__ == '__main__':
    test_<operation>()
```

### Best Practices

1. **Descriptive Names**: `test_mount_mnt_valid_path.py`
2. **Clear Output**: Print what's being tested and results
3. **Hex Dumps**: Show message bytes for debugging
4. **Error Messages**: Clear failure descriptions
5. **Cleanup**: Close sockets, delete temporary files
6. **Documentation**: Explain protocol details in comments

## References

### RFCs
- [RFC 5531](https://www.rfc-editor.org/rfc/rfc5531): RPC Protocol v2
- [RFC 4506](https://www.rfc-editor.org/rfc/rfc4506): XDR Standard
- [RFC 1813](https://www.rfc-editor.org/rfc/rfc1813): NFS v3 Protocol

### Related Documentation
- [ARCHITECTURE.md](../ARCHITECTURE.md): System architecture
- [XDR Specifications](../xdr/v3/): Protocol definitions

### Tools
- [xdrgen](https://crates.io/crates/xdrgen): XDR code generator
- [xdr-codec](https://crates.io/crates/xdr-codec): XDR runtime
- [tcpdump](https://www.tcpdump.org/): Network capture
- [Wireshark](https://www.wireshark.org/): Protocol analyzer

---

**Last Updated**: 2025-12-02
**Test Status**: Phase 1 Complete (RPC NULL) ✅
