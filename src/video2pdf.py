import argparse
import glob
import os
import shutil
import time

import cv2
import img2pdf
import imutils
import numpy as np
from skimage.metrics import structural_similarity as ssim

OUTPUT_SLIDES_DIR = "./output"

FRAME_RATE = 8
WARMUP = 2
RESIZE_WIDTH = 600

# SSIM below this threshold means "scene changed enough to capture".
# Range 0-1; lower = more captures. 0.45 is a good starting point for
# general-purpose video (not slides).
SCENE_CHANGE_THRESHOLD = 0.45

# Minimum seconds between captures to avoid rapid-fire saves.
MIN_CAPTURE_GAP = 2.0

# When comparing a candidate against the last *saved* frame, suppress
# if SSIM is above this value (i.e. the two frames are nearly identical).
DUPLICATE_SSIM = 0.92


def intialize_output_dir(video_path):
    """Creates the output directory and copies the video to the output directory"""
    output_dir = os.path.join(
        OUTPUT_SLIDES_DIR, os.path.splitext(os.path.basename(video_path))[0]
    )
    if os.path.exists(output_dir):
        shutil.rmtree(output_dir)
    os.makedirs(output_dir)
    return output_dir


def preprocess_for_diff(frame):
    """
    Focus only on the area where meaningful animation happens.
    Removes a lot of empty background that would dilute the signal.
    """
    h, w = frame.shape[:2]

    # Crop away most of the empty top area and some outer margins.
    # Tune these if needed.
    y1 = int(h * 0.28)
    y2 = int(h * 0.95)
    x1 = int(w * 0.03)
    x2 = int(w * 0.97)

    roi = frame[y1:y2, x1:x2]

    roi = imutils.resize(roi, width=700)
    gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
    gray = cv2.GaussianBlur(gray, (5, 5), 0)

    return roi, gray


def get_frames(video_path: str):
    """Extract sampled frames from the video."""
    vcap = cv2.VideoCapture(video_path)

    if not vcap.isOpened():
        raise Exception(f"Error opening video file {video_path}")

    frame_time = 0.0
    frame_count = 0

    while vcap.isOpened():
        vcap.set(cv2.CAP_PROP_POS_MSEC, frame_time * 1000)

        grabbed, frame = vcap.read()
        if not grabbed:
            break

        frame_count += 1

        if frame_count >= WARMUP:
            yield frame_count, frame_time, frame

        frame_time += 1.0 / FRAME_RATE

    vcap.release()


def detect_unique_screenshots(video_path, output_folder_screenshot) -> None:
    """
    Capture frames whenever the visible state changes enough.

    This works better for algorithm animations than background subtraction.
    """
    start_time = time.time()

    screenshots_count = 0
    last_saved_gray = None
    last_capture_time = -999.0

    # Tuning knobs
    min_capture_gap_seconds = 0.35
    pixel_diff_threshold = 18  # per-pixel difference threshold
    min_changed_percent = 0.12  # save when >= this % of ROI changed

    for frame_count, frame_time, frame in get_frames(video_path):
        original_frame = frame.copy()
        _, current_gray = preprocess_for_diff(frame)

        # Always save the first usable frame
        if last_saved_gray is None:
            filename = f"{screenshots_count:03}_{frame_time:.2f}.png"
            path = os.path.join(output_folder_screenshot, filename)
            cv2.imwrite(path, original_frame)
            print(f"Screenshot captured: {filename}")

            screenshots_count += 1
            last_saved_gray = current_gray.copy()
            last_capture_time = frame_time
            continue

        # Cooldown to prevent near-duplicates
        if (frame_time - last_capture_time) < min_capture_gap_seconds:
            continue

        # Absolute difference vs last saved frame
        diff = cv2.absdiff(current_gray, last_saved_gray)

        # Turn subtle changes into a binary mask
        _, thresh = cv2.threshold(diff, pixel_diff_threshold, 255, cv2.THRESH_BINARY)

        # Expand meaningful changed areas a bit
        kernel = np.ones((3, 3), np.uint8)
        thresh = cv2.dilate(thresh, kernel, iterations=2)

        changed_pixels = cv2.countNonZero(thresh)
        total_pixels = thresh.shape[0] * thresh.shape[1]
        changed_percent = (changed_pixels / float(total_pixels)) * 100.0

        # Uncomment to tune thresholds
        # print(
        #     f"frame={frame_count} time={frame_time:.2f}s "
        #     f"changed_percent={changed_percent:.3f}"
        # )

        if changed_percent >= min_changed_percent:
            filename = f"{screenshots_count:03}_{frame_time:.2f}.png"
            path = os.path.join(output_folder_screenshot, filename)
            cv2.imwrite(path, original_frame)
            print(
                f"Screenshot captured: {filename} "
                f"(changed_percent={changed_percent:.3f})"
            )

            screenshots_count += 1
            last_saved_gray = current_gray.copy()
            last_capture_time = frame_time

    print(f"Total screenshots: {screenshots_count}")
    print(f"Time taken: {time.time() - start_time:.2f}")


def convert_screenshots_to_pdf(output_folder_screenshot) -> None:
    """Converts screenshots to pdf"""
    # Get the file name without the extension
    file_name = os.path.splitext(os.path.basename(output_folder_screenshot))[0]

    output_folder_pdf = os.path.join(OUTPUT_SLIDES_DIR, f"{file_name}.pdf")

    images = []
    for file in glob.glob(f"{output_folder_screenshot}/*.png"):
        images.append(file)
    images.sort()
    with open(output_folder_pdf, "wb") as f:
        f.write(img2pdf.convert(images))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--video", required=True, help="Path to the video file")
    args = parser.parse_args()
    print("Video path: ", args.video)

    video_path = args.video
    output_folder_screenshot = intialize_output_dir(video_path)
    detect_unique_screenshots(video_path, output_folder_screenshot)

    print(f"{output_folder_screenshot} folder contains the screenshots")
    print("Please manually delete the screenshots that are not required or duplicates")
    while True:
        choice = input("Do you want to continue? (y/n): ")
        choice = choice.lower().strip()
        if choice in ["y", "n"]:
            break
        else:
            print("Invalid input. Please try again")
    if choice == "y":
        convert_screenshots_to_pdf(output_folder_screenshot)


if __name__ == "__main__":
    main()
