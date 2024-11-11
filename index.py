import os
import tempfile
import yt_dlp
import streamlit as st
from moviepy.editor import VideoFileClip
from moviepy.editor import AudioFileClip

# Create a directory to save downloaded files
def create_download_directory():
    download_dir = os.path.join(os.getcwd(), "downloads")
    if not os.path.exists(download_dir):
        os.makedirs(download_dir)
    return download_dir

# Merge video and audio streams
def merge_video_audio(video_path, audio_path, output_path):
    try:
        video = VideoFileClip(video_path)
        audio = AudioFileClip(audio_path)
        video = video.set_audio(audio)
        video.write_videofile(output_path, codec="libx264", audio_codec="aac")
        return True
    except Exception as e:
        print(f"Error merging video and audio: {str(e)}")
        return False

# Get available formats for video download
def get_available_formats(formats):
    quality_formats = {}  
    best_audio = None

    for f in formats:
        if (f.get('acodec') != 'none' and not f.get('vcodec')) or f['vcodec'] == 'none':
            if not best_audio or f.get('filesize', 0) > best_audio.get('filesize', 0):
                best_audio = f

    for f in formats:
        if not f.get('height') or not f.get('vcodec') or f['vcodec'] == 'none':
            continue

        height = f.get('height', 0)
        filesize = f.get('filesize', 0) or 0  # Ensure filesize is 0 if None
        ext = f.get('ext', 'mp4')

        if height > 0:
            quality_string = f"{height}p ({ext})"
            if quality_string not in quality_formats or (filesize > quality_formats[quality_string].get('filesize', 0)):
                quality_formats[quality_string] = {
                    'height': height,
                    'format_id': f['format_id'],
                    'quality': quality_string,
                    'video_ext': ext,
                    'filesize': filesize,
                    'audio_format_id': best_audio['format_id'] if best_audio else None
                }

    unique_formats = list(quality_formats.values())
    return sorted(unique_formats, key=lambda x: x['height'], reverse=True)

# Download video with selected format
def download_video(url, format_data):
    download_dir = create_download_directory()
    temp_dir = tempfile.mkdtemp()

    video_opts = {
        'format': format_data['format_id'],
        'outtmpl': os.path.join(temp_dir, 'video.%(ext)s'),
        'progress_hooks': [progress_hook],
    }

    audio_opts = {
        'format': format_data['audio_format_id'],
        'outtmpl': os.path.join(temp_dir, 'audio.%(ext)s'),
        'progress_hooks': [progress_hook],
    }

    try:
        with yt_dlp.YoutubeDL(video_opts) as ydl:
            video_info = ydl.extract_info(url, download=True)
            video_path = ydl.prepare_filename(video_info)

        with yt_dlp.YoutubeDL(audio_opts) as ydl:
            audio_info = ydl.extract_info(url, download=True)
            audio_path = ydl.prepare_filename(audio_info)

        output_filename = f"{video_info['title']}.mp4"
        output_path = os.path.join(download_dir, output_filename)
        st.text("Merging video and audio... Please Wait")
        if merge_video_audio(video_path, audio_path, output_path):
            try:
                os.remove(video_path)
                os.remove(audio_path)
                os.rmdir(temp_dir)
            except Exception as e:
                st.warning(f"Error cleaning up temporary files: {str(e)}")

            return output_path
        else:
            st.error("Failed to merge video and audio.")
            return None
    finally:
        try:
            os.remove(video_path)
            os.remove(audio_path)
            os.rmdir(temp_dir)
        except Exception as e:
            st.warning(f"Error cleaning up temporary files: {str(e)}")

# Progress hook to track download status
def progress_hook(d):
    if d['status'] == 'downloading':
        st.progress(d['downloaded_bytes'] / d['total_bytes'])

# Main function to handle Streamlit interface and video download
def main():
    st.title("YouTube Video Downloader")

    url = st.text_input("Enter YouTube Video URL:")
    if url:
        try:
            with yt_dlp.YoutubeDL() as ydl:
                video_info = ydl.extract_info(url, download=False)
                formats = get_available_formats(video_info['formats'])

                selected_format = st.selectbox("Select Video Format", [f"{f['quality']} - {f['filesize']} bytes" for f in formats])

                if selected_format:
                    format_data = formats[formats.index(next(f for f in formats if f['quality'] == selected_format.split(' - ')[0]))]
                    if st.button("Download"):
                        video_path = download_video(url, format_data)
                        if video_path:
                            with open(video_path, "rb") as file:
                                st.download_button(
                                    label="Download Video 📥",
                                    data=file,
                                    file_name=os.path.basename(video_path),
                                    mime="video/mp4"
                                )
        except Exception as e:
            st.error(f"Error: {str(e)}")

if __name__ == "__main__":
    main()
