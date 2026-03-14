# Getting Started

This guide walks you through setting up and running VideoCaptureToPDF for the first time.

## Prerequisites

- **Windows 10/11**, **macOS**, or **Linux**
- An internet connection (for the initial setup)

No need to install Python manually — the setup tool handles that for you.

## Step 1: Install uv

uv is a fast Python package manager that will install Python and all dependencies for you.

**Windows** (open PowerShell):

```powershell
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```

**macOS / Linux** (open a terminal):

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

After installing, close and reopen your terminal so the `uv` command is available.

To verify it worked, run:

```
uv --version
```

You should see a version number printed.

## Step 2: Download the Project

If you have Git installed:

```
git clone <repository-url>
cd VideoCaptureToPDF
```

Otherwise, download the project as a ZIP file, extract it, and open a terminal in the extracted folder.

## Step 3: Install Dependencies

From the project folder, run:

```
uv sync
```

This will automatically:

1. Download and install Python 3.13 (if not already installed)
2. Create a virtual environment
3. Install all required packages (OpenCV, img2pdf, etc.)

## Step 4: Run the Application

Place your video file (MP4) somewhere accessible — for example, in the `src/input/` folder.

Then run:

```
uv run src/video2pdf.py --video "path/to/your/video.mp4"
```

**Example** using the included test video:

```
uv run src/video2pdf.py --video "./src/input/Test Video 1.mp4"
```

## What Happens Next

1. The application processes the video and extracts unique slides as PNG screenshots
2. Screenshots are saved to the `output/` folder (named after your video)
3. The application pauses and asks you to review the screenshots
4. Open the output folder, delete any duplicates or unwanted images
5. Return to the terminal and type `y` then press Enter to generate the PDF
6. Your PDF will appear in the `output/` folder

## Troubleshooting

| Problem | Solution |
|---|---|
| `uv: command not found` | Close and reopen your terminal after installing uv |
| `Error opening video file` | Double-check the path to your video file. Use quotes around paths with spaces. |
| Too many duplicate slides | Try increasing `MIN_PERCENTAGE` in `video2pdf.py` (e.g., from `0.1` to `0.5`) |
| Missing slides | Try decreasing `FGBG_HISTORY` or `MAX_PERCENTAGE` in `video2pdf.py` |
