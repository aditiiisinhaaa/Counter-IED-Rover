from picamera2 import Picamera2, Preview
import time

picam2 = Picamera2()

# Configure for live preview
preview_config = picam2.create_preview_configuration()
picam2.configure(preview_config)

# Start the preview window (use Preview.DRM if running without a desktop environment)
picam2.start_preview(Preview.QTGL)
picam2.start()

# Keep the live feed open (press Ctrl+C in terminal to stop)
try:
    while True:
        time.sleep(1)
except KeyboardInterrupt:
    picam2.stop_preview()
    picam2.stop()
