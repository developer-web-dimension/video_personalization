import ffmpeg
import os
import random
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from datetime import datetime

app = FastAPI()

INPUT_DIR_MAP = {
    "boy": "input_boy",
    "girl": "input_girl"
}

OUTPUT_DIR = "output"

FONT_MAP = {
    "english": "font/Gotham Bold.otf",
    "hindi": "font/devnagri.ttf"
}

PREFIX_MAP = {
    "english": f"Tiger Hero",
    "hindi": f"टाइगर हीरो"
}

timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")


class VideoRequest(BaseModel):
    name: str
    language: str 
    gender: str 


def add_bottom_text(
    input_path,
    output_path,
    name,
    language,
    font_size=85,
    left_margin=150,
    bottom_margin=400,
    box_padding=40,
):
    language = language.lower()

    if language not in FONT_MAP:
        raise ValueError("Unsupported language")

    fontfile = FONT_MAP[language]
    prefix = PREFIX_MAP[language]
    final_text = f"{prefix}\n{name}"

    safe_text = (
        final_text.replace("\\", "\\\\")
        .replace(":", "\\:")
        .replace("'", "\\'")
    )

    inp = ffmpeg.input(input_path)

    video = inp.video.filter(
        "drawtext",
        fontfile=fontfile,
        text=safe_text,
        fontsize=font_size,
        fontcolor="black",
        x="(w-text_w)/2",
        y=f"h-text_h-{bottom_margin}",
        text_align="center",
        line_spacing=0,
        box=1,
        boxcolor="ffc000@0.85",
        boxborderw=box_padding,
        shadowx=2,
        shadowy=2,
        shadowcolor="black@0.35"
    )


    (
        ffmpeg
        .output(
            video,
            inp.audio,
            output_path,
            vcodec="libx264",
            acodec="copy",
            pix_fmt="yuv420p",
            movflags="faststart"
        )
        .overwrite_output()
        .run()
    )


def concat_all_videos(folder_path, output_path):
    videos = sorted([
        os.path.join(folder_path, f)
        for f in os.listdir(folder_path)
        if f.endswith(".mp4")
    ])

    if not videos:
        raise ValueError("No videos to concatenate")

    streams = []
    for v in videos:
        inp = ffmpeg.input(v)
        streams.extend([inp.video, inp.audio])

    (
        ffmpeg
        .concat(*streams, v=1, a=1)
        .output(
            output_path,
            vcodec="libx264",
            acodec="aac",
            audio_bitrate="192k",
            ar=44100,
            pix_fmt="yuv420p"
        )
        .overwrite_output()
        .run()
    )


@app.post("/generate-video")
def generate_video(data: VideoRequest):
    try:
        os.makedirs(OUTPUT_DIR, exist_ok=True)

        gender = data.gender.lower()

        if gender not in INPUT_DIR_MAP:
            raise ValueError("Invalid gender. Use 'boy' or 'girl'")

        input_dir = INPUT_DIR_MAP[gender]

        # ✅ Step 1: Pick random video from gender folder
        videos = [
            f for f in os.listdir(input_dir)
            if f.endswith(".mp4")
        ]

        if not videos:
            raise ValueError("No videos found in input folder")

        chosen_video = random.choice(videos)
        video_name = os.path.splitext(chosen_video)[0]

        input_video_path = os.path.join(input_dir, chosen_video)

        # ✅ Step 2: Create folder with video name
        video_folder = video_name
        os.makedirs(video_folder, exist_ok=True)

        # ✅ Step 3: Save processed video INSIDE that folder
        processed_video_path = os.path.join(video_folder, "2.mp4")

        add_bottom_text(
            input_path=input_video_path,
            output_path=processed_video_path,
            name=data.name,
            language=data.language
        )

        # ✅ Step 4: Concat videos inside that folder
        final_output = os.path.join(OUTPUT_DIR, f"{timestamp}_{gender}_final.mp4")

        concat_all_videos(
            folder_path=video_folder,
            output_path=final_output
        )

        return {
            "status": "success",
            "chosen_video": chosen_video,
            "saved_in_folder": video_folder,
            "final_output": final_output
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

