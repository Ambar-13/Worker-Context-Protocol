//! Minimal JSON-RPC 2.0 client over WebSocket.

use std::sync::atomic::{AtomicU64, Ordering};
use std::sync::Arc;

use futures_util::{SinkExt, StreamExt};
use serde_json::{json, Value};
use thiserror::Error;
use tokio::sync::oneshot;
use tokio_tungstenite::{connect_async, tungstenite::Message};

#[derive(Debug, Error)]
pub enum RpcError {
    #[error("connection error: {0}")]
    Connect(String),
    #[error("send failure")]
    SendFailure,
    #[error("rpc error code={code}: {message}")]
    RpcError { code: i64, message: String },
    #[error("internal: {0}")]
    Internal(String),
}

type Pending = Arc<tokio::sync::Mutex<std::collections::HashMap<u64, oneshot::Sender<Result<Value, RpcError>>>>>;

pub struct RpcClient {
    next_id: AtomicU64,
    pending: Pending,
    sender: tokio::sync::mpsc::UnboundedSender<Message>,
}

impl RpcClient {
    pub async fn connect(url: &str) -> Result<Self, RpcError> {
        let (ws, _) = connect_async(url)
            .await
            .map_err(|e| RpcError::Connect(e.to_string()))?;
        let (mut write, mut read) = ws.split();

        let (tx_out, mut rx_out) = tokio::sync::mpsc::unbounded_channel::<Message>();
        let pending: Pending = Arc::new(tokio::sync::Mutex::new(Default::default()));
        let pending_for_reader = pending.clone();

        // Reader task: dispatch responses to oneshots.
        tokio::spawn(async move {
            while let Some(msg) = read.next().await {
                let Ok(msg) = msg else { break };
                if let Message::Text(s) = msg {
                    if let Ok(v) = serde_json::from_str::<Value>(&s) {
                        if let Some(id) = v.get("id").and_then(|x| x.as_u64()) {
                            let mut guard = pending_for_reader.lock().await;
                            if let Some(tx) = guard.remove(&id) {
                                if v.get("error").is_some() {
                                    let err = v.get("error").unwrap();
                                    let code = err.get("code").and_then(|x| x.as_i64()).unwrap_or(-32603);
                                    let message = err
                                        .get("message")
                                        .and_then(|x| x.as_str())
                                        .unwrap_or("")
                                        .to_string();
                                    let _ = tx.send(Err(RpcError::RpcError { code, message }));
                                } else {
                                    let result = v.get("result").cloned().unwrap_or(Value::Null);
                                    let _ = tx.send(Ok(result));
                                }
                            }
                        }
                    }
                }
            }
        });

        // Writer task.
        tokio::spawn(async move {
            while let Some(msg) = rx_out.recv().await {
                if write.send(msg).await.is_err() {
                    break;
                }
            }
        });

        Ok(RpcClient {
            next_id: AtomicU64::new(1),
            pending,
            sender: tx_out,
        })
    }

    pub async fn call(&self, method: &str, params: Value) -> Result<Value, RpcError> {
        let id = self.next_id.fetch_add(1, Ordering::Relaxed);
        let (tx, rx) = oneshot::channel();
        self.pending.lock().await.insert(id, tx);
        let envelope = json!({"jsonrpc": "2.0", "id": id, "method": method, "params": params});
        self.sender
            .send(Message::Text(envelope.to_string()))
            .map_err(|_| RpcError::SendFailure)?;
        rx.await
            .map_err(|e| RpcError::Internal(e.to_string()))?
    }
}
