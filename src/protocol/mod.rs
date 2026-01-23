// Protocol middleware layer
//
// This module provides a clean abstraction over XDR-generated types,
// handling serialization/deserialization and version differences.

pub mod v3;

// Re-export commonly used types
#[allow(unused_imports)]
pub use v3::{MountMessage, NfsMessage, PortmapMessage, RpcMessage};
