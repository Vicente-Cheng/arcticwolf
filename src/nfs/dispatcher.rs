// NFS Procedure Dispatcher
//
// Routes incoming NFS RPC calls to the appropriate procedure handler

use anyhow::{anyhow, Result};
use bytes::BytesMut;
use tracing::{debug, warn};

use crate::fsal::Filesystem;
use crate::protocol::v3::rpc::rpc_call_msg;

use super::{access, fsinfo, fsstat, getattr, lookup, null, read};

/// Dispatch NFS procedure call to appropriate handler
///
/// # Arguments
/// * `call` - Parsed RPC call message
/// * `args_data` - Procedure arguments data
/// * `filesystem` - Filesystem instance
///
/// # Returns
/// Serialized RPC reply message
pub fn dispatch(
    call: &rpc_call_msg,
    args_data: &[u8],
    filesystem: &dyn Filesystem,
) -> Result<BytesMut> {
    let procedure = call.proc_;
    let xid = call.xid;

    debug!(
        "NFS dispatcher: procedure={}, xid={}, version={}",
        procedure, xid, call.vers
    );

    // Verify NFS version
    if call.vers != 3 {
        warn!("Unsupported NFS version: {}", call.vers);
        return Err(anyhow!("NFS version {} not supported", call.vers));
    }

    // Dispatch based on procedure number
    match procedure {
        0 => {
            // NULL - test procedure
            null::handle_null(xid)
        }
        1 => {
            // GETATTR - get file attributes
            getattr::handle_getattr(xid, args_data, filesystem)
        }
        3 => {
            // LOOKUP - lookup filename
            lookup::handle_lookup(xid, args_data, filesystem)
        }
        4 => {
            // ACCESS - check file access permissions
            access::handle_access(xid, args_data, filesystem)
        }
        6 => {
            // READ - read from file
            read::handle_read(xid, args_data, filesystem)
        }
        18 => {
            // FSSTAT - get filesystem statistics
            fsstat::handle_fsstat(xid, args_data, filesystem)
        }
        19 => {
            // FSINFO - get filesystem information
            fsinfo::handle_fsinfo(xid, args_data, filesystem)
        }
        7 => {
            // WRITE - write to file
            warn!("NFS WRITE not yet implemented");
            Err(anyhow!("WRITE not implemented"))
        }
        8 => {
            // CREATE - create file
            warn!("NFS CREATE not yet implemented");
            Err(anyhow!("CREATE not implemented"))
        }
        9 => {
            // MKDIR - create directory
            warn!("NFS MKDIR not yet implemented");
            Err(anyhow!("MKDIR not implemented"))
        }
        _ => {
            warn!("Unknown NFS procedure: {}", procedure);
            Err(anyhow!("Unknown procedure: {}", procedure))
        }
    }
}
