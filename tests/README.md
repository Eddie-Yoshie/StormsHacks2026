# Testing

## Windows
### Initializing Webcam as RTSP Stream
There are three changes you will need to make:
* `{path_to_windows_ffmpeg.exe}`: self explanatory, make sure it is formatted for Linux and not Windows
* `{webcam_hardware_name}`: call `/mnt/c/Users/mtfp64/Documents/ffmpeg-8.1.1-essentials_build/bin/ffmpeg.exe -list_devices true -f dshow -i dummy` in WSL2, find the name of your webcam and mic.
* `{audio_hardware_name}`: same as above, identify mic and throw it in there
* `{wsl_IP}`: call `hostname -I` and use the first IP in the list.

Place them in the following command, in their respective positions:

```bash
{path_to_windows_ffmpeg.exe} \
  -rtbufsize 500M \
  -f dshow -i video="{webcam_hardware_name}":audio="{audio_name}" \
  -c:v libx264 -preset ultrafast -tune zerolatency -pix_fmt yuv420p \
  -rtsp_transport tcp \
  -f rtsp rtsp://{wsl_IP}:8554/webcam
```

### Example
You will end up with a command that looks like this:

```bash
/mnt/c/Users/mtfp64/Documents/ffmpeg-8.1.1-essentials_build/bin/ffmpeg.exe \
  -rtbufsize 500M \
  -f dshow -i video="HP 5MP Camera":audio="Microphone Array (Intel® Smart Sound Technology for Digital Microphones)" \
  -c:v libx264 -preset ultrafast -tune zerolatency -pix_fmt yuv420p \
  -rtsp_transport tcp \
  -f rtsp rtsp://172.25.36.229:8554/webcam
```

## Linux
Initializing your webcam as a RTSP stream is very simple, ensure you have FFMPEG (on Ubuntu/Debian run `sudo apt install ffmpeg`) installed and run:
```bash
ffmpeg -f v4l2 -i /dev/video0 -c:v libx264 -preset ultrafast -rtbufsize 500M -f rtsp -rtsp_transport tcp rtsp://localhost:8554/webcam
```