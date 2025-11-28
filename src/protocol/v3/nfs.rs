// NFS Protocol Middleware
//
// Wraps xdrgen-generated NFS types and provides serialization helpers

use anyhow::Result;
use bytes::BytesMut;
use std::io::Cursor;
use xdr_codec::{Pack, Unpack};

// Include xdrgen-generated NFS types
#[allow(dead_code, non_camel_case_types, non_snake_case, non_upper_case_globals, clippy::all)]
mod generated {
    include!(concat!(env!("OUT_DIR"), "/nfs_generated.rs"));
}

// Re-export generated types
pub use generated::*;

/// Wrapper for NFS messages providing serialization helpers
pub struct NfsMessage;

impl NfsMessage {
    /// Deserialize GETATTR request
    pub fn deserialize_getattr3args(data: &[u8]) -> Result<GETATTR3args> {
        let mut cursor = Cursor::new(data);
        let (args, _bytes_read) = GETATTR3args::unpack(&mut cursor)?;
        Ok(args)
    }

    /// Serialize GETATTR response
    pub fn serialize_getattr3res(res: &GETATTR3res) -> Result<BytesMut> {
        let mut buf = Vec::new();
        res.pack(&mut buf)?;
        Ok(BytesMut::from(&buf[..]))
    }

    /// Deserialize LOOKUP request
    pub fn deserialize_lookup3args(data: &[u8]) -> Result<LOOKUP3args> {
        let mut cursor = Cursor::new(data);
        let (args, _bytes_read) = LOOKUP3args::unpack(&mut cursor)?;
        Ok(args)
    }

    /// Serialize LOOKUP response
    pub fn serialize_lookup3res(res: &LOOKUP3res) -> Result<BytesMut> {
        let mut buf = Vec::new();
        res.pack(&mut buf)?;
        Ok(BytesMut::from(&buf[..]))
    }

    /// Create a successful GETATTR response
    pub fn create_getattr_ok(attrs: fattr3) -> GETATTR3res {
        GETATTR3res::NFS3_OK(GETATTR3resok {
            obj_attributes: attrs,
        })
    }

    /// Create an NFS error response (use the default variant)
    pub fn create_getattr_error() -> GETATTR3res {
        GETATTR3res::default
    }
}
