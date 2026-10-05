import { Camera as CameraIcon, RotateCcw, X } from "lucide-react";
import { CAMERA_ANALYSIS_UNAVAILABLE_COPY, useCamera } from "../camera/useCamera";

/** Camera capture only -- capturing a frame never implies image understanding. */
export function ScanVehicle() {
  const { state, errorMessage, imageDataUrl, videoRef, requestAccess, capture, retake, cancel } = useCamera();

  if (state === "UNSUPPORTED") {
    return <p className="muted small">Camera isn't available on this device.</p>;
  }

  return (
    <div className="scan-vehicle">
      {state === "IDLE" ? (
        <button type="button" className="btn btn--ghost" onClick={() => void requestAccess()}>
          <CameraIcon size={18} aria-hidden="true" /> Scan vehicle
        </button>
      ) : null}

      {state === "REQUESTING" ? (
        <p role="status" className="muted small">
          Starting camera…
        </p>
      ) : null}

      {state === "DENIED" && errorMessage ? (
        <p role="alert" className="muted small">
          {errorMessage}
        </p>
      ) : null}

      {state === "READY" ? (
        <div className="scan-vehicle__preview">
          <video ref={videoRef} autoPlay playsInline muted aria-label="Camera preview" />
          <div className="action-list">
            <button type="button" className="btn btn--primary" onClick={capture}>
              Capture
            </button>
            <button type="button" className="btn btn--ghost" onClick={cancel}>
              <X size={16} aria-hidden="true" /> Cancel
            </button>
          </div>
        </div>
      ) : null}

      {state === "PREVIEW" ? (
        <div className="scan-vehicle__preview">
          {imageDataUrl ? <img src={imageDataUrl} alt="Captured vehicle photo" /> : null}
          <p className="muted small">{CAMERA_ANALYSIS_UNAVAILABLE_COPY}</p>
          <div className="action-list">
            <button type="button" className="btn btn--secondary" onClick={retake}>
              <RotateCcw size={16} aria-hidden="true" /> Retake
            </button>
            <button type="button" className="btn btn--ghost" onClick={cancel}>
              <X size={16} aria-hidden="true" /> Cancel
            </button>
          </div>
        </div>
      ) : null}

      {state === "ERROR" && errorMessage ? (
        <p role="alert" className="muted small">
          {errorMessage}
        </p>
      ) : null}
    </div>
  );
}
