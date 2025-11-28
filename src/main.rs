use anyhow::Result;
use tracing_subscriber;

mod protocol;
mod rpc;

#[tokio::main]
async fn main() -> Result<()> {
    // Initialize tracing
    tracing_subscriber::fmt::init();

    println!("Arctic Wolf NFS Server");
    println!("======================");
    println!("Architecture:");
    println!("- XDR: xdrgen + xdr-codec (supports string, union, arrays)");
    println!("- Protocol: v3 (RPC, MOUNT, NFS)");
    println!("- Middleware: Type-safe serialization/deserialization");
    println!();
    println!("Starting RPC server on 0.0.0.0:4000");
    println!("Phase 1: RPC NULL procedure");
    println!();

    // Create and run RPC server
    let server = rpc::server::RpcServer::new("0.0.0.0:4000".to_string());
    server.run().await?;

    Ok(())
}
