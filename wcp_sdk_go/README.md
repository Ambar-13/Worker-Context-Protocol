# wcp-go

Worker Context Protocol Go SDK. Vendor-neutral.

```bash
go get github.com/wcp-spec/wcp-go
```

## Worker

```go
package main

import (
    "context"
    wcp "github.com/wcp-spec/wcp-go"
)

func main() {
    ctx := context.Background()
    w, err := wcp.NewWorker(ctx, wcp.WorkerClassAutonomousRobot, "ws://localhost:8000/wcp/ws")
    if err != nil { panic(err) }
    defer w.Close()
    _, err = w.PublishCapabilities(ctx, map[string]interface{}{
        "schema_version": "wcp/0.2",
        "worker_id": w.Identity.DID,
        // ... rest of descriptor
    })
    if err != nil { panic(err) }
}
```

## License

Apache 2.0
