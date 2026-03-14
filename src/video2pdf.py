import argparse
import glob
import os
import shutil
import time

import cv2
import img2pdf
import imutils

OUTPUT_SLIDES_DIR = "./output"

FRAME_RATE = 6
WARMUP = 5
FGBG_HISTORY = FRAME_RATE * 15
FGBG_THRESHOLD = 25
FGBG_SHADOW = False
MIN_PERCENTAGE = 0.5
MAX_PERCENTAGE = 1.5


def intialize_output_dir(video_path):
    """Creates the output directory and copies the video to the output directory"""
    output_dir = os.path.join(
        OUTPUT_SLIDES_DIR, os.path.splitext(os.path.basename(video_path))[0]
    )
    if os.path.exists(output_dir):
        shutil.rmtree(output_dir)
    os.makedirs(output_dir)
    # shutil.copy(video_path, output_dir)
    return output_dir


def get_frames(video_path: str):
    """Extracts frames sequentially, yielding 3 frames per second"""
    vcap = cv2.VideoCapture(video_path)

    if not vcap.isOpened():
        raise Exception("Error opening video file {}".format(video_path))

    fps = vcap.get(cv2.CAP_PROP_FPS)
    frames_to_skip = int(
        fps / FRAME_RATE
    )  # Calculate how many frames to skip to get desired FRAME_RATE

    frame_count = 0
    yield_count = 0

    while vcap.isOpened():
        grabbed, frame = vcap.read()
        if not grabbed:
            break

        frame_count += 1

        # Only process the frame if it matches our desired frame rate interval
        if frame_count % frames_to_skip == 0:
            yield_count += 1
            frame_time = frame_count / fps

            if yield_count < WARMUP:
                continue
            else:
                yield yield_count, frame_time, frame


def detect_unique_screenshots(video_path, output_folder_screenshot) -> None:
    """Detect stable, unique screenshots from the video."""
    fgbg = cv2.createBackgroundSubtractorMOG2(
        history=FGBG_HISTORY,
        varThreshold=FGBG_THRESHOLD,
        detectShadows=FGBG_SHADOW,
    )

    start_time = time.time()
    (W, H) = (None, None)

    screenshots_count = 0
    stable_frames = 0
    required_stable_frames = 3
    min_capture_gap_seconds = 2.0
    last_capture_time = -999.0
    last_saved_gray = None

    for frame_count, frame_time, frame in get_frames(video_path):
        original_frame = frame.copy()
        resized_frame = imutils.resize(frame, width=600)
        gray_small = cv2.cvtColor(resized_frame, cv2.COLOR_BGR2GRAY)

        mask = fgbg.apply(resized_frame)

        if W is None or H is None:
            (H, W) = resized_frame.shape[:2]

        p_diff = (cv2.countNonZero(mask) / float(W * H)) * 100

        # Debug while tuning:
        # print(f"frame={frame_count} time={frame_time:.2f}s p_diff={p_diff:.3f}")

        # Count consecutive stable frames
        if p_diff < MIN_PERCENTAGE:
            stable_frames += 1
        else:
            stable_frames = 0

        # Need several stable frames in a row
        if stable_frames < required_stable_frames:
            continue

        # Prevent rapid back-to-back captures
        if (frame_time - last_capture_time) < min_capture_gap_seconds:
            continue

        # Suppress near-duplicates by comparing against last saved frame
        is_duplicate = False
        if last_saved_gray is not None:
            frame_delta = cv2.absdiff(gray_small, last_saved_gray)
            mean_delta = frame_delta.mean()

            # Lower value means the frames are more similar.
            # Tune this value if needed.
            if mean_delta < 2.0:
                is_duplicate = True

        if is_duplicate:
            continue

        filename = f"{screenshots_count:03}_{round(frame_time / 60, 2)}.png"
        path = os.path.join(output_folder_screenshot, filename)
        cv2.imwrite(path, original_frame)
        print(f"Screenshot captured: {filename}")

        screenshots_count += 1
        last_capture_time = frame_time
        last_saved_gray = gray_small.copy()
        stable_frames = 0

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
