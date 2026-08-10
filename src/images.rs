//! Image handling: stored images are re-encoded to WebP files under `uploads/`,
//! served statically at `/uploads/…`. Records that reference a stored image get
//! their file deleted when the record is removed or the image is replaced.

use std::path::Path;

use base64::Engine;
use image::ImageFormat;
use uuid::Uuid;

use crate::error::{AppError, AppResult};

pub const UPLOADS_DIR: &str = "uploads";

/// Turn an incoming image into a stored WebP and return its public URL.
/// - a `data:` URL is decoded, re-encoded to WebP, and written to `uploads/`;
/// - anything else (already a URL) is returned unchanged.
pub async fn store_maybe(base_url: &str, src: &str) -> AppResult<String> {
    if !src.starts_with("data:") {
        return Ok(src.to_string());
    }

    let comma = src
        .find(',')
        .ok_or_else(|| AppError::BadRequest("invalid data URL".into()))?;
    let bytes = base64::engine::general_purpose::STANDARD
        .decode(src[comma + 1..].as_bytes())
        .map_err(|_| AppError::BadRequest("invalid image base64".into()))?;

    // Decode + encode is CPU-bound → run off the async runtime.
    let webp = tokio::task::spawn_blocking(move || encode_webp(&bytes))
        .await
        .map_err(|e| AppError::Internal(format!("image task failed: {e}")))??;

    let filename = format!("{}.webp", Uuid::new_v4());
    tokio::fs::create_dir_all(UPLOADS_DIR)
        .await
        .map_err(|e| AppError::Internal(format!("create uploads dir: {e}")))?;
    tokio::fs::write(Path::new(UPLOADS_DIR).join(&filename), webp)
        .await
        .map_err(|e| AppError::Internal(format!("write image: {e}")))?;

    Ok(format!("{}/uploads/{}", base_url.trim_end_matches('/'), filename))
}

fn encode_webp(bytes: &[u8]) -> AppResult<Vec<u8>> {
    let img = image::load_from_memory(bytes).map_err(|e| {
        AppError::BadRequest(format!("image decode failed ({} bytes): {e}", bytes.len()))
    })?;
    let mut out = std::io::Cursor::new(Vec::new());
    img.write_to(&mut out, ImageFormat::WebP)
        .map_err(|e| AppError::Internal(format!("webp encode: {e}")))?;
    Ok(out.into_inner())
}

/// Delete a locally-stored image file (only for our own `/uploads/…` URLs).
/// External URLs and data URLs are ignored. Best-effort — errors are swallowed.
pub async fn delete_file(url: &str) {
    if let Some(idx) = url.find("/uploads/") {
        let name = &url[idx + "/uploads/".len()..];
        // Guard against path traversal / nested paths.
        if !name.is_empty() && !name.contains('/') && !name.contains("..") {
            let _ = tokio::fs::remove_file(Path::new(UPLOADS_DIR).join(name)).await;
        }
    }
}
