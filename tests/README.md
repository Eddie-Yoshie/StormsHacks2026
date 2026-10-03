# testing

## to init your webcam, and to find the respective RTSP URL:
you will end up w a command that looks like this:

```
/mnt/c/Users/mtfp64/Documents/ffmpeg-8.1.1-essentials_build/bin/ffmpeg.exe \
  -rtbufsize 500M \
  -f dshow -i video="HP 5MP Camera" \
  -c:v libx264 -preset ultrafast -tune zerolatency -pix_fmt yuv420p \
  -rtsp_transport tcp \
  -f rtsp rtsp://172.25.36.229:8554/webcam
```

there are three changes you will need to make:
* `{path_to_windows_ffmpeg.exe}`: self explanatory. make sure it is formatted for linux and not windows
* `{webcam_hardware_name}`: call `/mnt/c/Users/mtfp64/Documents/ffmpeg-8.1.1-essentials_build/bin/ffmpeg.exe -list_devices true -f dshow -i dummy` in wsl, find the name of your webcam
* `{wsl_IP}`: call `hostname -I` and use the first IP in the list.

place them in the following command in their respective positions:

```
{path_to_windows_ffmpeg.exe} \
  -rtbufsize 500M \
  -f dshow -i video="{webcam_hardware_name}" \
  -c:v libx264 -preset ultrafast -tune zerolatency -pix_fmt yuv420p \
  -rtsp_transport tcp \
  -f rtsp rtsp://{wsl_IP}:8554/webcam
```

and you will get an rtsp stream that looks like that last lil section above