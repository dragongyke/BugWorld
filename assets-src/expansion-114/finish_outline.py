"""Round the outer edge of expansion templates without altering paint region IDs."""
import cv2
import numpy as np
from PIL import Image


def finish_outline(lines: Image.Image, mask: Image.Image) -> Image.Image:
    rgba = np.array(lines.convert("RGBA"))
    paint = np.asarray(mask.convert("RGB"))[:, :, 0] > 0
    dark = (rgba[:, :, :3].max(axis=2) < 160) & (rgba[:, :, 3] > 0)
    rgba[dark, :3] = (73, 57, 47)
    ink = (rgba[:, :, 3] >= 120) & (rgba[:, :, :3].max(axis=2) < 160)
    silhouette = (paint | ink).astype(np.uint8)
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (7, 7))
    silhouette = cv2.morphologyEx(silhouette, cv2.MORPH_CLOSE, kernel)
    contours, _ = cv2.findContours(silhouette, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    filled = np.zeros_like(silhouette)
    # Keep independent details such as fine antennae in the original ink layer.
    contours = [contour for contour in contours if cv2.contourArea(contour) >= 180]
    cv2.drawContours(filled, contours, -1, 1, thickness=cv2.FILLED)
    rounded = (cv2.GaussianBlur(filled.astype(np.float32), (0, 0), 2.2) >= .49).astype(np.uint8)
    inside = cv2.distanceTransform(rounded, cv2.DIST_L2, cv2.DIST_MASK_PRECISE)
    outside = cv2.distanceTransform(1 - rounded, cv2.DIST_L2, cv2.DIST_MASK_PRECISE)
    edge_distance = np.abs(inside - outside) - .5
    # Replace the previous outer ink near the edge while keeping inner anatomy.
    rgba[:, :, 3] = np.rint(
        rgba[:, :, 3] * np.clip((edge_distance - 3.2) / 2.0, 0, 1)
    ).astype(np.uint8)
    alpha = np.rint(np.clip(4.6 - edge_distance, 0, 1) * 255).astype(np.uint8)
    outline = Image.new("RGBA", lines.size, (40, 30, 25))
    outline.putalpha(Image.fromarray(alpha))
    return Image.alpha_composite(Image.fromarray(rgba), outline)
