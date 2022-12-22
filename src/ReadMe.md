# Python Application to Extract Stills from a Video to a PDF

## Description

The project coverts MP4 video presentation into a PDF Document.  The PNG files generated an be also used in a presentation.

## Setup

```python
pip install -r requirments.txt
```

## Steps to Run Code

From Command prompt where the video2pdf.py resides

```cmd
python .\video2pdf.py --video "<video path>"
```

## Example

```cmd
python .\video2pdf.py --video "./input/Test Video 1.mp4"
```

## More

The default parameters works for a typical video presentation. But if the video presentation has lots of animations, the default parametrs won't give a good results, you may notice duplicate/missing slides. Don't worry, you can make it work for any video presentation, even the ones with animations, you just need to fine tune and figure out the right set of parametrs, The 3 most important parameters that I would recommend to get play around is "MIN_PERCENT", "MAX_PERCENT", "FGBG_HISTORY". The description of these variables can be found in code comments.

### Acknowledgment

The code was based on the development of Kaushik Jeyarman and his video on youtube demo: <https://www.youtube.com/watch?v=Q0BIPYLoSBs>
