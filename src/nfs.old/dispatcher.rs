// RPC dispatcher for NFS-related programs
//
// Routes RPC calls based on program number to appropriate handlers:
// - 100005 -> MOUNT protocol
// - 100003 -> NFS protocol

use anyhow::{Result, anyhow};
use bytes::{Bytes, BytesMut};
use tracing::debug;

use crate::rpc::rpc_call_msg;
use super::{MOUNT_PROGRAM, NFS_PROGRAM};

pub fn dispatch_nfs_call(call: &rpc_call_msg<Bytes>) -> Result<BytesMut> {
    debug!("Dispatching call for program {}, procedure {}", call.prog, call.proc);

    match call.prog {
        MOUNT_PROGRAM => {
            debug!("Routing to MOUNT handler");
            super::mount::handle_mount_call(call)
        }
        NFS_PROGRAM => {
            debug!("Routing to NFS handler");
            super::v3::handle_nfs_call(call)
        }
        _ => {
            Err(anyhow!("Unsupported program number: {}", call.prog))
        }
    }
}
