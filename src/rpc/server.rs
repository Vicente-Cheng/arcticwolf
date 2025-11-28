// RPC TCP Server with Record Marking
//
// Implements Sun RPC over TCP with record marking protocol (RFC 5531)

use anyhow::{Result, anyhow};
use bytes::{BytesMut, BufMut, Buf};
use tokio::io::{AsyncReadExt, AsyncWriteExt};
use tokio::net::{TcpListener, TcpStream};
use tracing::{info, debug, error, warn};

use crate::protocol::v3::rpc::{RpcMessage, rpc_call_msg};

/// RPC server handling TCP connections with record marking
pub struct RpcServer {
    addr: String,
}

impl RpcServer {
    pub fn new(addr: String) -> Self {
        Self { addr }
    }

    pub async fn run(&self) -> Result<()> {
        let listener = TcpListener::bind(&self.addr).await?;
        info!("RPC server listening on {}", self.addr);

        loop {
            let (socket, peer_addr) = listener.accept().await?;
            info!("New connection from {}", peer_addr);

            tokio::spawn(async move {
                if let Err(e) = handle_connection(socket).await {
                    error!("Connection error from {}: {}", peer_addr, e);
                }
            });
        }
    }
}

/// Handle a single TCP connection
async fn handle_connection(mut socket: TcpStream) -> Result<()> {
    let mut buffer = BytesMut::with_capacity(8192);

    loop {
        // Read record marking fragment header (4 bytes)
        let mut header = [0u8; 4];
        if socket.read_exact(&mut header).await.is_err() {
            debug!("Connection closed by peer");
            break;
        }

        // Parse record marking header
        // Bit 31: last fragment (1 = last, 0 = more fragments)
        // Bits 0-30: fragment length
        let header_u32 = u32::from_be_bytes(header);
        let is_last = (header_u32 & 0x80000000) != 0;
        let fragment_len = (header_u32 & 0x7FFFFFFF) as usize;

        debug!(
            "Record marking: last={}, length={}",
            is_last, fragment_len
        );

        // Read fragment data
        let mut fragment = vec![0u8; fragment_len];
        socket.read_exact(&mut fragment).await?;
        buffer.put_slice(&fragment);

        // If this is the last fragment, process the complete RPC message
        if is_last {
            debug!("Complete RPC message received ({} bytes)", buffer.len());

            match handle_rpc_message(&buffer).await {
                Ok(response) => {
                    // Send response with record marking
                    let response_len = response.len() as u32;
                    let record_header = response_len | 0x80000000; // Set last fragment bit

                    socket.write_u32(record_header).await?;
                    socket.write_all(&response).await?;
                    socket.flush().await?;

                    debug!("Sent response ({} bytes)", response.len());
                }
                Err(e) => {
                    error!("Failed to handle RPC message: {}", e);
                    // TODO: Send error response
                }
            }

            // Clear buffer for next message
            buffer.clear();
        }
    }

    Ok(())
}

/// Handle a complete RPC message
async fn handle_rpc_message(data: &[u8]) -> Result<BytesMut> {
    // Deserialize RPC call
    let call = RpcMessage::deserialize_call(data)?;

    debug!(
        "RPC call: xid={}, prog={}, vers={}, proc={}",
        call.xid, call.prog, call.vers, call.proc_
    );

    // Route to appropriate handler based on procedure number
    match call.proc_ {
        0 => handle_null_procedure(&call),
        _ => {
            warn!("Unsupported procedure: {}", call.proc_);
            Err(anyhow!("Unsupported procedure: {}", call.proc_))
        }
    }
}

/// Handle RPC NULL procedure (0)
fn handle_null_procedure(call: &rpc_call_msg) -> Result<BytesMut> {
    debug!("Handling NULL procedure for xid={}", call.xid);

    // Create success reply using protocol middleware
    let reply = RpcMessage::create_null_reply(call.xid);

    // Serialize reply
    RpcMessage::serialize_reply(&reply)
}
