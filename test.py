import ffmpeg
import os
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

app = FastAPI()


FONT_MAP = {
    "english": "font/Gotham Bold.otf",
    "hindi": "font/devnagri.ttf"
}

PREFIX_MAP = {
    "english": "Tiger Hero",
    "hindi": "टाइगर हीरो"
}


class VideoRequest(BaseModel):
    name: str
    language: str  # english | hindi


def add_bottom_text(
    input_path,
    output_path,
    name,
    language,
    font_size=90,
    left_margin=120,
    bottom_margin=400,
    box_padding=40,
):
    language = language.lower()

    if language not in FONT_MAP:
        raise ValueError("Unsupported language")

    fontfile = FONT_MAP[language]
    prefix = PREFIX_MAP[language]

    final_text = f"{prefix} {name}"

    # Escape FFmpeg text
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
        x=left_margin,
        y=f"h-text_h-{bottom_margin}",
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


def concat_videos(video1, video2, video3, output_path):
    v1 = ffmpeg.input(video1)
    v2 = ffmpeg.input(video2)
    v3 = ffmpeg.input(video3)

    (
        ffmpeg
        .concat(
            v1.video, v1.audio,
            v2.video, v2.audio,
            v3.video, v3.audio,
            v=1, a=1
        )
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
        os.makedirs("output", exist_ok=True)
        os.makedirs("assets", exist_ok=True)

        # Step 1: Add text
        add_bottom_text(
            input_path="input_video/2.mp4",
            output_path="assets/2.mp4",
            name=data.name,
            language=data.language
        )

        # Step 2: Concat videos
        final_output = "output/final_combined_video.mp4"

        concat_videos(
            video1="assets/1.mp4",
            video2="assets/2.mp4",
            video3="assets/3.mp4",
            output_path=final_output
        )

        return {
            "status": "success",
            "language": data.language,
            "name": data.name,
            "output_video": final_output
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)