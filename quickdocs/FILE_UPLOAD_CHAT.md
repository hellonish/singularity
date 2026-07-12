Then keep it simpler: **the frontend owns the temporary “uploading” UI state**, while the backend remains the source of truth.

## Flow

```text
User selects file
→ frontend sets uploadStatus = "uploading"
→ send button disabled
→ file uploads
→ backend confirms success
→ frontend sets uploadStatus = "uploaded"
→ send button enabled
```

## Frontend example

```typescript
const [uploadStatus, setUploadStatus] =
  useState<"idle" | "uploading" | "uploaded" | "failed">("idle");

const canSend = uploadStatus !== "uploading";

async function uploadFile(file: File) {
  setUploadStatus("uploading");

  try {
    const result = await fileApi.upload(file);

    setAttachedFile({
      id: result.file_id,
      name: file.name,
    });

    setUploadStatus("uploaded");
  } catch {
    setUploadStatus("failed");
  }
}
```

```tsx
<button disabled={!canSend || !message.trim()}>
  Send
</button>
```

## Important distinction

Enable the send button after:

```text
upload complete
```

or after:

```text
processing/indexing complete
```

These are different.

For file-based Q&A, you will usually want:

```text
uploading → uploaded → processing → ready
```

Then:

```typescript
const canSend =
  attachedFiles.every(file => file.status === "ready");
```

The backend should still reject a message if the file is not ready, because users can bypass frontend checks or have stale browser state.

```python
if file.status != "ready":
    raise HTTPException(
        status_code=409,
        detail={"code": "FILE_NOT_READY"},
    )
```

So the clean setup is:

```text
Frontend disables the button for UX
Backend validates file state for correctness
No API request waits open
```
