// Browser camera capture via getUserMedia. Capturing a frame does NOT imply
// any image understanding -- there is no OCR or fault detection here, only
// permission, preview, capture, retake, and cancel.
import { useCallback, useEffect, useRef, useState } from "react";

export type CameraState = "UNSUPPORTED" | "IDLE" | "REQUESTING" | "READY" | "DENIED" | "PREVIEW" | "ERROR";

export const CAMERA_ANALYSIS_UNAVAILABLE_COPY = "Image analysis isn't available in this prototype yet.";
const CAMERA_DENIED_COPY = "Camera access was denied. You can still type your question.";
const CAMERA_ERROR_COPY = "Camera could not be started. You can still type your question.";

function cameraSupported(): boolean {
  return typeof navigator !== "undefined" && Boolean(navigator.mediaDevices?.getUserMedia);
}

export interface CameraController {
  state: CameraState;
  errorMessage: string | null;
  imageDataUrl: string | null;
  videoRef: React.RefObject<HTMLVideoElement | null>;
  requestAccess: () => Promise<void>;
  capture: () => void;
  retake: () => void;
  cancel: () => void;
}

export function useCamera(): CameraController {
  const videoRef = useRef<HTMLVideoElement | null>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const [state, setState] = useState<CameraState>(() => (cameraSupported() ? "IDLE" : "UNSUPPORTED"));
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [imageDataUrl, setImageDataUrl] = useState<string | null>(null);

  const stopStream = useCallback(() => {
    streamRef.current?.getTracks().forEach((track) => track.stop());
    streamRef.current = null;
  }, []);

  useEffect(() => () => stopStream(), [stopStream]);

  const requestAccess = useCallback(async () => {
    if (!cameraSupported()) {
      setState("UNSUPPORTED");
      return;
    }
    setState("REQUESTING");
    setErrorMessage(null);
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ video: { facingMode: "environment" } });
      streamRef.current = stream;
      if (videoRef.current) videoRef.current.srcObject = stream;
      setState("READY");
    } catch {
      setErrorMessage(CAMERA_DENIED_COPY);
      setState("DENIED");
    }
  }, []);

  const capture = useCallback(() => {
    const video = videoRef.current;
    if (!video) {
      setErrorMessage(CAMERA_ERROR_COPY);
      setState("ERROR");
      return;
    }
    const canvas = document.createElement("canvas");
    canvas.width = video.videoWidth || 640;
    canvas.height = video.videoHeight || 480;
    const ctx = canvas.getContext("2d");
    ctx?.drawImage(video, 0, 0, canvas.width, canvas.height);
    setImageDataUrl(canvas.toDataURL("image/png"));
    setState("PREVIEW");
  }, []);

  const retake = useCallback(() => {
    setImageDataUrl(null);
    setState("READY");
  }, []);

  const cancel = useCallback(() => {
    stopStream();
    setImageDataUrl(null);
    setErrorMessage(null);
    setState(cameraSupported() ? "IDLE" : "UNSUPPORTED");
  }, [stopStream]);

  return { state, errorMessage, imageDataUrl, videoRef, requestAccess, capture, retake, cancel };
}
