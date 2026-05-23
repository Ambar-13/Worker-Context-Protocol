# wcp-sdk (Rust)

Worker Context Protocol Rust SDK. Vendor-neutral.

```bash
cargo add wcp-sdk
```

## Worker (builder pattern)

```rust
use wcp_sdk::{Worker, WorkerClass};

#[tokio::main]
async fn main() -> Result<(), Box<dyn std::error::Error>> {
    let worker = Worker::builder()
        .name("amr-7")
        .worker_class(WorkerClass::AutonomousRobot)
        .coordinator("ws://localhost:8000/wcp/ws")
        .descriptor_type("transport")
        .build()?;
    worker.run().await?;
    Ok(())
}
```

## License

Apache 2.0
