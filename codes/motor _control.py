from flask import Flask, request, jsonify, render_template_string, Response
from gpiozero import PWMOutputDevice, DigitalOutputDevice
from picamera2 import Picamera2
from libcamera import controls
import threading, time, io

class BTSMotor:
    def __init__(self, rpwm, lpwm, en, freq=1000):
        self.r = PWMOutputDevice(rpwm, frequency=freq)
        self.l = PWMOutputDevice(lpwm, frequency=freq)
        self.en = DigitalOutputDevice(en, initial_value=True)

    def drive(self, speed):
        speed = max(-1.0, min(1.0, speed))
        if speed >= 0:
            self.l.value = 0
            self.r.value = speed
        else:
            self.r.value = 0
            self.l.value = -speed

    def stop(self):
        self.r.value = 0
        self.l.value = 0

# left side = 2 drivers sharing these pins, right side = 2 drivers sharing these
left = BTSMotor(18, 19, 23)
right = BTSMotor(12, 13, 24)
last_cmd = time.time()

def watchdog():
    while True:
        if time.time() - last_cmd > 0.4:
            left.stop()
            right.stop()
        time.sleep(0.1)

threading.Thread(target=watchdog, daemon=True).start()

# camera (Camera Module 3)
picam2 = Picamera2()
picam2.configure(picam2.create_video_configuration(main={"size": (640, 480)}))
picam2.start()
try:
    picam2.set_controls({"AfMode": controls.AfModeEnum.Continuous})
except Exception:
    pass
cam_lock = threading.Lock()

def gen_frames():
    while True:
        buf = io.BytesIO()
        with cam_lock:
            picam2.capture_file(buf, format="jpeg")
        yield (b"--frame\r\nContent-Type: image/jpeg\r\n\r\n"
               + buf.getvalue() + b"\r\n")
        time.sleep(0.05)

app = Flask(__name__)

PAGE = """
<!doctype html>
<html>
<head>
<meta name="viewport" content="width=device-width, initial-scale=1, user-scalable=no">
<title>Rover Control</title>
<style>
body { font-family: sans-serif; background:#111; color:#eee; text-align:center; user-select:none; touch-action:none; }
img { width:100%; max-width:480px; border-radius:10px; background:#000; }
.pad { display:grid; grid-template-columns:repeat(3,90px); gap:10px; justify-content:center; margin:20px auto; }
button { height:90px; font-size:18px; border:none; border-radius:14px; background:#2d6cdf; color:#fff; touch-action:none; }
button:active { background:#1b4aa8; }
#stop { background:#d33; }
input[type=range] { width:80%; max-width:400px; }
</style>
</head>
<body>
<h2>Rover Control</h2>
<img src="/video" alt="camera">
<div>Speed: <span id="sv">100</span>%</div>
<input type="range" id="speed" min="0" max="100" value="100">
<div class="pad">
<div></div><button data-l="1" data-r="1">FWD</button><div></div>
<button data-l="-1" data-r="1">LEFT</button>
<button id="stop" data-l="0" data-r="0">STOP</button>
<button data-l="1" data-r="-1">RIGHT</button>
<div></div><button data-l="-1" data-r="-1">BACK</button><div></div>
</div>
<p>Hold a button to move. Release to stop.</p>
<script>
var slider = document.getElementById('speed');
var sv = document.getElementById('sv');
slider.oninput = function() { sv.textContent = slider.value; };
var timer = null;
function send(l, r) {
  var s = slider.value / 100;
  fetch('/drive', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({l: l * s, r: r * s})
  }).catch(function() {});
}
function stop() {
  if (timer) { clearInterval(timer); timer = null; }
  send(0, 0);
}
function start(l, r) {
  stop();
  send(l, r);
  timer = setInterval(function() { send(l, r); }, 150);
}
document.querySelectorAll('button').forEach(function(b) {
  var l = +b.dataset.l;
  var r = +b.dataset.r;
  b.addEventListener('pointerdown', function(e) { e.preventDefault(); start(l, r); });
  b.addEventListener('pointerup', stop);
  b.addEventListener('pointerleave', stop);
  b.addEventListener('pointercancel', stop);
});
document.addEventListener('contextmenu', function(e) { e.preventDefault(); });
</script>
</body>
</html>
"""

@app.route("/")
def index():
    return render_template_string(PAGE)

@app.route("/video")
def video():
    return Response(gen_frames(),
                    mimetype="multipart/x-mixed-replace; boundary=frame")

@app.route("/drive", methods=["POST"])
def drive():
    global last_cmd
    d = request.get_json(force=True)
    left.drive(float(d.get("l", 0)))
    right.drive(float(d.get("r", 0)))
    last_cmd = time.time()
    return jsonify(ok=True)

if __name__ == "__main__":
    try:
        app.run(host="0.0.0.0", port=5000, threaded=True)
    finally:
        left.stop()
        right.stop()
        picam2.stop()