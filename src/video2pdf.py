import argparse
import glob
import os
import shutil
import time

import cv2
import img2pdf
import imutils

OUTPUT_SLIDES_DIR = f"./output"

FRAME_RATE = 3  # number of frames per second to process from the video. few the frames, faster the processing
WARMPUP = 10  # initial frames to skip
FGBG_HISTORY = FRAME_RATE * 15  # number of frames to use to build the background model
FGBG_THRESHOLD = 25  # threshold value for the background subtraction
FGBG_SHADOW = False  # whether or not to detect shadows
MIN_PERCENTAGE = 0.1  # minimum percentage of the frame that must be foreground to be considered a motion
MAX_PERCENTAGE = 3  # maximum percentage of the frame that must be foreground to be considered a motion


def intialize_output_dir(video_path):
    """Creates the output directory and copies the video to the output directory"""
    output_dir = os.path.join(
        f"{OUTPUT_SLIDES_DIR}/", os.path.splitext(os.path.basename(video_path))[0]
    )
    if os.path.exists(output_dir):
        shutil.rmtree(output_dir)
    os.makedirs(output_dir)
    # shutil.copy(video_path, output_dir)
    return output_dir


def get_frames(video_path: str):
    """Extracts frames from a video and returns a list of frames"""
    vcap = cv2.VideoCapture(video_path)

    if not vcap.isOpened():
        raise Exception("Error opening video file {}".format(video_path))

    total_frames = int(vcap.get(cv2.CAP_PROP_FRAME_COUNT))
    frame_time = 0
    frame_count = 0
    while vcap.isOpened():
        # grab a fram from the video
        vcap.set(
            cv2.CAP_PROP_POS_MSEC, frame_time * 1000
        )  # move frame pointer to the frame_time
        frame_time += 1 / FRAME_RATE
        (grabbed, frame) = vcap.read()

        if not grabbed:
            break
        frame_count += 1
        if frame_count < WARMPUP:
            continue
        else:
            yield frame_count, frame_time, frame


def detect_unique_screenshots(video_path, output_folder_screenshot) -> None:
    # intialize FGBG a background subtractor
    fgbg = cv2.createBackgroundSubtractorMOG2(
        history=FGBG_HISTORY, varThreshold=FGBG_THRESHOLD, detectShadows=FGBG_SHADOW
    )

    captured = False
    start_time = time.time()
    (W, H) = (None, None)

    screenshots_count = 0
    for frame_count, frame_time, frame in get_frames(video_path):
        original_frame = frame.copy()
        frame = imutils.resize(frame, width=600)
        mask = fgbg.apply(frame)  # apply the background subtractor to the frame

        # if the width and height are empty, grab them
        if W is None or H is None:
            (H, W) = frame.shape[:2]

        # compute the percentage of the frame that is foreground
        p_diff = (cv2.countNonZero(mask) / float(W * H)) * 100

        # if the p_diff is less than N% then there is no motion in the frame and we need to capture the screenshot
        if p_diff < MIN_PERCENTAGE and not captured and frame_count > WARMPUP:
            # capture the screenshot
            filename = f"{screenshots_count:03}_{round(frame_time/60, 2)}.png"
            path = os.path.join(output_folder_screenshot, filename)
            cv2.imwrite(path, original_frame)
            # give user some feedback
            print(f"Screenshot captured: {filename}")

            screenshots_count += 1
            captured = True
        elif captured and p_diff > MAX_PERCENTAGE:
            captured = False
    print(f"Total screenshots: {screenshots_count}")
    print(f"Time taken: {time.time() - start_time}")


def convert_screenshots_to_pdf(output_folder_screenshot) -> None:
    """Converts screenshots to pdf"""
    # Get the file name without the extension
    file_name = os.path.splitext(os.path.basename(output_folder_screenshot))[0]

    output_folder_pdf = f"{OUTPUT_SLIDES_DIR}/{file_name}" + ".pdf"

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
