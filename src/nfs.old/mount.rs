// MOUNT Protocol Handler (Program 100005, Version 3)
//
// The MOUNT protocol is used to obtain initial file handles for NFS operations.
// Main procedures:
// - NULL (0): Ping test
// - MNT (1): Mount a directory and return file handle
// - UMNT (3): Unmount a directory

use anyhow::{Result, anyhow};
use bytes::{Bytes, BytesMut};
use tracing::debug;

use crate::rpc::rpc_call_msg;

pub fn handle_mount_call(call: &rpc_call_msg<Bytes>) -> Result<BytesMut> {
    match call.proc {
        0 => handle_null(call),
        1 => handle_mnt(call),
        3 => handle_umnt(call),
        _ => Err(anyhow!("Unsupported MOUNT procedure: {}", call.proc)),
    }
}

fn handle_null(_call: &rpc_call_msg<Bytes>) -> Result<BytesMut> {
    debug!("MOUNT: NULL procedure");
    // TODO: Return success reply
    unimplemented!("MOUNT NULL not yet implemented")
}

fn handle_mnt(_call: &rpc_call_msg<Bytes>) -> Result<BytesMut> {
    debug!("MOUNT: MNT procedure");
    // TODO: Parse directory path, create file handle, return mountres3
    unimplemented!("MOUNT MNT not yet implemented")
}

fn handle_umnt(_call: &rpc_call_msg<Bytes>) -> Result<BytesMut> {
    debug!("MOUNT: UMNT procedure");
    // TODO: Remove mount entry
    unimplemented!("MOUNT UMNT not yet implemented")
}
