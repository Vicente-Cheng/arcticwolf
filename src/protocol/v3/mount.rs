// MOUNT Protocol Middleware
//
// Wraps xdrgen-generated MOUNT types and provides serialization helpers

use anyhow::Result;
use bytes::BytesMut;
use std::io::Cursor;
use xdr_codec::{Pack, Unpack};

// Include xdrgen-generated MOUNT types
#[allow(
    dead_code,
    deprecated,
    non_camel_case_types,
    non_snake_case,
    non_upper_case_globals,
    unused_assignments,
    clippy::all
)]
mod generated {
    include!(concat!(env!("OUT_DIR"), "/mount_generated.rs"));
}

// Re-export generated types
pub use generated::*;

/// Wrapper for MOUNT messages providing serialization helpers
pub struct MountMessage;

impl MountMessage {
    /// Deserialize MOUNT request arguments (dirpath)
    pub fn deserialize_dirpath(data: &[u8]) -> Result<String> {
        let mut cursor = Cursor::new(data);
        let (path_wrapper, _bytes_read) = dirpath::unpack(&mut cursor)?;
        Ok(path_wrapper.0) // Extract String from newtype wrapper
    }

    /// Serialize MOUNT response
    pub fn serialize_mountres3(res: &mountres3) -> Result<BytesMut> {
        let mut buf = Vec::new();
        res.pack(&mut buf)?;
        Ok(BytesMut::from(&buf[..]))
    }

    /// Create a successful mount response
    pub fn create_mount_ok(fhandle_bytes: Vec<u8>) -> mountres3 {
        mountres3::MNT3_OK(mountres3_ok {
            fhandle: fhandle3(fhandle_bytes), // Wrap in newtype
            auth_flavors: vec![0],            // AUTH_NONE
        })
    }

    /// Create a mount error response (use the default variant)
    #[allow(dead_code)]
    pub fn create_mount_error() -> mountres3 {
        mountres3::default
    }
}
