from picamera2 import Picamera2
import time

picam2 = Picamera2() # initialize
picam2.start()

time.sleep(2) # wait for sensor by 2 seconds to adjust exposure and white balance

picam2.capture_file("photo.jpg") # click and save the image
picam2.stop()
