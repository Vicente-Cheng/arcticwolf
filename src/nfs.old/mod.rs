// NFS module - unified handling of MOUNT and NFSv3 protocols
//
// This module provides:
// - Program 100005 (MOUNT protocol) for obtaining file handles
// - Program 100003 (NFS protocol) for file operations

pub mod dispatcher;
pub mod mount;
pub mod v3;

// Include generated XDR types from nfs.x
#[allow(dead_code, non_camel_case_types, non_snake_case, unused_variables)]
include!(concat!(env!("OUT_DIR"), "/nfs_generated.rs"));

pub use xdr::*;
