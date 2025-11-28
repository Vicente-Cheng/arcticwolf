// NFSv3 Protocol Handler (Program 100003, Version 3)
//
// Main NFSv3 procedures:
// - NULL (0): Ping test
// - GETATTR (1): Get file attributes
// - LOOKUP (3): Look up filename in directory
// - READ (6): Read from file
// - WRITE (7): Write to file
// - CREATE (8): Create a file
// - MKDIR (9): Create a directory
// - READDIR (16): Read directory entries

use anyhow::{Result, anyhow};
use bytes::{Bytes, BytesMut};
use tracing::debug;

use crate::rpc::rpc_call_msg;

pub fn handle_nfs_call(call: &rpc_call_msg<Bytes>) -> Result<BytesMut> {
    match call.proc {
        0 => handle_null(call),
        1 => handle_getattr(call),
        3 => handle_lookup(call),
        _ => Err(anyhow!("Unsupported NFS procedure: {}", call.proc)),
    }
}

fn handle_null(_call: &rpc_call_msg<Bytes>) -> Result<BytesMut> {
    debug!("NFS: NULL procedure");
    // TODO: Return success reply
    unimplemented!("NFS NULL not yet implemented")
}

fn handle_getattr(_call: &rpc_call_msg<Bytes>) -> Result<BytesMut> {
    debug!("NFS: GETATTR procedure");
    // TODO: Parse file handle, get attributes, return getattr3res
    unimplemented!("NFS GETATTR not yet implemented")
}

fn handle_lookup(_call: &rpc_call_msg<Bytes>) -> Result<BytesMut> {
    debug!("NFS: LOOKUP procedure");
    // TODO: Parse directory handle and filename, lookup, return file handle
    unimplemented!("NFS LOOKUP not yet implemented")
}
