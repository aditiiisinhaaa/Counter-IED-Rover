from picamzero import Camera

cam = Camera()
cam.take_photo("photo.jpg")
cam.record_video("video.mp4", duration=5)