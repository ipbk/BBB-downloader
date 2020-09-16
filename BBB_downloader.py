import math
import os
import subprocess
import sys
from typing import Final, List
from xml.dom.minidom import Element
from xml.etree import ElementTree

import requests


class Slide:
    def __init__(self, time_in: int, time_out: int, src: str) -> None:
        self.__time_in: Final[int] = time_in
        self.__time_out: int = time_out
        self.__src: Final[str] = src

    @property
    def time_in(self) -> int:
        return self.__time_in

    @property
    def time_out(self) -> int:
        return self.__time_out

    @time_out.setter
    def time_out(self, value) -> None:
        self.__time_out = value

    @property
    def src(self) -> str:
        return self.__src


def main() -> None:
    url: Final[str] = sys.argv[1]  # https://HOST/playback/presentation/2.0/playback.html?meetingId=MEETING_ID
    base_url: Final[str] = url.split('/playback/')[0]  # https://HOST
    meeting_id: Final[str] = url.split('?meetingId=')[1]  # MEETING_ID

    print('BBB downloader')
    print(f"Meeting ID: {meeting_id}")
    print('Downloading metadata')

    metadata_url: Final[str] = f"{base_url}/presentation/{meeting_id}/metadata.xml"
    metadata_req: Final[requests.Response] = requests.get(metadata_url)
    metadata_tree: Final[Element] = ElementTree.fromstring(metadata_req.content)

    duration: Final[int] = int(metadata_tree.find('playback/duration').text)  # ms
    meeting_name: Final[str] = '_'.join(metadata_tree.find('meta/meetingName').text.split())

    print(f"Meeting: {meeting_name}, duration: {(duration / 60000):.2f} min")

    slides_url: Final[str] = f"{base_url}/presentation/{meeting_id}/shapes.svg"
    print('Downloading slides info')
    slides_response: Final[requests.Response] = requests.get(slides_url)
    slides_tree: Final[Element] = ElementTree.fromstring(slides_response.content)
    slides: Final[List[Slide]] = []

    for image in slides_tree:
        time_in: int = int(math.ceil(float(image.attrib['in'])))
        time_out: int = int(math.ceil(float(image.attrib['out'])))
        path: str = image.attrib['{http://www.w3.org/1999/xlink}href']
        slides.append(Slide(time_in, time_out, path))

    print('Setting the last slide correct duration')
    slides[-1].time_out = int(math.ceil(duration / 1000))

    current_dir: Final[str] = os.getcwd()
    temporary_dir: Final[str] = f"{current_dir}/{meeting_id}"
    print(f"Creating temporary directory: {temporary_dir}")
    os.mkdir(temporary_dir)

    print('Downloading images')
    for index, slide in enumerate(slides):
        slide_url: str = f"{base_url}/presentation/{meeting_id}/{slide.src}"
        slide_req: requests.Response = requests.get(slide_url)
        with open(f"{temporary_dir}/{index}.png", 'wb') as file:
            file.write(slide_req.content)

    print('Creating mp4 pieces from slides')
    for index, slide in enumerate(slides):
        subprocess.call([
            f"ffmpeg -loop 1 -f image2 -r 1 -i {temporary_dir}/{index}.png -c:v libx264 -vf fps=24 "
            f"-t {slide.time_out - slide.time_in} -pix_fmt yuv420p {temporary_dir}/{index}.mp4"
        ], shell=True)

    list_file: Final[str] = f"{temporary_dir}/videos.txt"
    print('Creating list file to bind files')
    with open(list_file, 'w') as file:
        for i in range(len(slides)):
            file.write(f"file {temporary_dir}/{i}.mp4\n")

    webcams_url: Final[str] = f"{base_url}/presentation/{meeting_id}/video/webcams.webm"  # in my case it's just audio
    print('Downloading webcams file')
    webcams_req: Final[requests.Response] = requests.get(webcams_url)
    webcams_file: Final[str] = f"{temporary_dir}/webcams.webm"
    with open(webcams_file, 'wb') as file:
        for chunk in webcams_req.iter_content(1024):
            file.write(chunk)

    merged_file: Final[str] = f"{temporary_dir}/merged.mp4"
    print('Merging mp4 pieces')
    subprocess.call([
        f"ffmpeg -f concat -safe 0 -i {list_file} -c copy {merged_file}"
    ], shell=True)

    video_file: Final[str] = f"{temporary_dir}/{meeting_name}.mp4"
    print('Adding audio to merged file')
    subprocess.call([
        f"ffmpeg -i {merged_file} -i {webcams_file} "
        f"-c:v copy -c:a aac -map 0:v:0 -map 1:a:0 {video_file}"
    ], shell=True)

    print('Removing unnecessary files')
    for i in range(len(slides)):
        os.remove(f"{temporary_dir}/{i}.mp4")
    os.remove(list_file)
    os.remove(webcams_file)
    os.remove(merged_file)

    target_video: Final[str] = f"{current_dir}/{meeting_name}.mp4"
    target_slides_dir: Final[str] = f"{current_dir}/{meeting_name}_slides"
    os.rename(video_file, target_video)
    os.rename(temporary_dir, target_slides_dir)

    print()
    print(f"Video path: {target_video}")
    print(f"Slides folder path: {target_slides_dir}")


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        pass
