import argparse
import glob
import os
import shutil
import time

import cv2
import img2pdf
import imutils
from skimage.metrics import structural_similarity as ssim

OUTPUT_SLIDES_DIR = "./output"

FRAME_RATE = 3
WARMUP = 3
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


def get_frames(video_path: str):
    """Extracts frames at FRAME_RATE fps."""
    vcap = cv2.VideoCapture(video_path)

    if not vcap.isOpened():
        raise Exception("Error opening video file {}".format(video_path))

    fps = vcap.get(cv2.CAP_PROP_FPS)
    frames_to_skip = int(fps / FRAME_RATE)

    frame_count = 0
    yield_count = 0

    while vcap.isOpened():
        grabbed, frame = vcap.read()
        if not grabbed:
            break

        frame_count += 1

        if frame_count % frames_to_skip == 0:
            yield_count += 1
            frame_time = frame_count / fps

            if yield_count < WARMUP:
                continue
            else:
                yield yield_count, frame_time, frame


def detect_unique_screenshots(video_path, output_folder_screenshot) -> None:
    """Detect visually distinct frames using SSIM-based scene-change detection.

    Instead of background subtraction (which assumes a mostly-static scene),
    this compares every sampled frame against the previous frame to find
    scene changes, then deduplicates against the last *saved* frame.
    """
    start_time = time.time()

    screenshots_count = 0
    last_capture_time = -999.0
    prev_gray = None
    last_saved_gray = None

    for frame_count, frame_time, frame in get_frames(video_path):
        original_frame = frame.copy()
        resized = imutils.resize(frame, width=RESIZE_WIDTH)
        gray = cv2.cvtColor(resized, cv2.COLOR_BGR2GRAY)

        # First usable frame — always save it.
        if prev_gray is None:
            prev_gray = gray
            filename = f"{screenshots_count:03}_{round(frame_time / 60, 2)}.png"
            cv2.imwrite(os.path.join(output_folder_screenshot, filename), original_frame)
            print(f"Screenshot captured: {filename}")
            screenshots_count += 1
            last_capture_time = frame_time
            last_saved_gray = gray.copy()
            continue

        # Compare against the *previous* frame to detect scene changes.
        score = ssim(prev_gray, gray)
        prev_gray = gray

        # No significant change — skip.
        if score > SCENE_CHANGE_THRESHOLD:
            continue

        # Enforce minimum time gap.
        if (frame_time - last_capture_time) < MIN_CAPTURE_GAP:
            continue

        # Suppress near-duplicates of the last saved frame.
        if last_saved_gray is not None:
            dup_score = ssim(last_saved_gray, gray)
            if dup_score > DUPLICATE_SSIM:
                continue

        filename = f"{screenshots_count:03}_{round(frame_time / 60, 2)}.png"
        path = os.path.join(output_folder_screenshot, filename)
        cv2.imwrite(path, original_frame)
        print(f"Screenshot captured: {filename}")

        screenshots_count += 1
        last_capture_time = frame_time
        last_saved_gray = gray.copy()

    print(f"Total screenshots: {screenshots_count}")
    print(f"Time taken: {time.time() - start_time}")


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
