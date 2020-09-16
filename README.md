# BBB-Downloader
A simple script to download the presentation from BigBlueButton except the presenter's cursor movement.

## Requirements
You need to install required packages and [FFmpeg](https://ffmpeg.org/download.html).

```shell script
$ pip3 install -r requirements.txt
```

## Usage
```shell script
$ python3 BBB_downloader.py "https://HOST/playback/presentation/2.0/playback.html?meetingId=MEETING_ID"
```
As a result, you get the folder with slides and the video file in the current directory.