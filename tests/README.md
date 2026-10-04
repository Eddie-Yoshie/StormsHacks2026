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

### Docker Desktop (no WSL distro)
With the stack running under Docker Desktop (see the root README), publish from a Windows ffmpeg straight to
`localhost`. List devices with `ffmpeg -list_devices true -f dshow -i dummy`, then:

```powershell
ffmpeg -rtbufsize 500M -f dshow -video_size 1280x720 -framerate 30 `
  -i "video=HD Webcam eMeet C960:audio=Microphone (HD Webcam eMeet C960)" `
  -c:v libx264 -preset veryfast -tune zerolatency -profile:v baseline -pix_fmt yuv420p -g 30 `
  -b:v 2500k -maxrate 2500k -bufsize 5000k -c:a libopus -b:a 64k -ar 48000 `
  -rtsp_transport tcp -f rtsp rtsp://localhost:8554/webcam-src
```

Then add the camera in the dashboard with RTSP URL `rtsp://localhost:8554/webcam-src` and a **different** name
(e.g. `webcam`). Registering a camera under the same name as the path you publish to replaces your stream with
a pull from itself, and ffmpeg dies with "Broken pipe". Keep the bitrate cap: uncapped 1080p loses packets
through Docker Desktop's port forwarding and shows up as green smears.

## Linux
Initializing your webcam as a RTSP stream is very simple, ensure you have FFMPEG (on Ubuntu/Debian run `sudo apt install ffmpeg`) installed and run:
```bash
ffmpeg -f v4l2 -i /dev/video0 -f alsa -i default -c:v libx264 -preset ultrafast -pix_fmt yuv420p -rtbufsize 500M -f rtsp -rtsp_transport tcp rtsp://localhost:8554/webcam
```