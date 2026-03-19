from flask import Flask, render_template, Response, jsonify, request
from camera import Camera
import threading
import os

app = Flask(__name__)

def shutdown_server():
    import os, signal
    os.kill(os.getpid(), signal.SIGINT)
    return "Server shutting down..."

@app.route('/shutdown', methods=['POST'])
def shutdown():
    shutdown_server()
    return 'Server shutting down...'

# Initialize Camera (Singleton-ish)
camera_system = None

def get_camera():
    global camera_system
    if camera_system is None:
        camera_system = Camera()
    return camera_system

@app.route('/')
def index():
    return render_template('index.html')

def generate_frames():
    cam = get_camera()
    while True:
        frame_bytes = cam.get_frame()
        if frame_bytes:
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')

@app.route('/video_feed')
def video_feed():
    return Response(generate_frames(), mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/status')
def status():
    """Returns the current status (nearest object, instruction) for the frontend voice"""
    cam = get_camera()
    return jsonify(cam.get_current_status())

@app.route('/command', methods=['POST'])
def command():
    """Handle voice commands from frontend"""
    data = request.json
    cmd = data.get('command', '').lower()
    cam = get_camera()
    
    response_text = "Command not recognized"
    
    if 'night' in cmd:
        cam.toggle_night_mode()
        response_text = "Night mode toggled"
    elif 'read' in cmd or 'medicine' in cmd:
        text = cam.read_text_mode()
        response_text = f"Reading: {text}" if text else "No text found"
    elif 'describe' in cmd or 'see' in cmd:
        status = cam.get_current_status()
        details = status.get('detailed_objects', [])
        
        if details:
            # Sort by distance (closest first)
            details.sort(key=lambda x: x['distance'])
            
            # Create a group description
            total_objects = len(details)
            closest = details[0]
            
            spoken_parts = []
            # Limit to top 4 for brevity
            for obj in details[:4]:
                spoken_parts.append(f"a {obj['label']} at {obj['distance']} meters on your {obj['position']}")
            
            if total_objects > 1:
                response_text = f"I see {total_objects} items. The closest is {closest['label']} at {closest['distance']} meters. "
                response_text += "There is also " + ", ".join(spoken_parts[1:]) + "."
            else:
                response_text = f"I see only one object: {closest['label']} at {closest['distance']} meters on your {closest['position']}."
            
            # Add general summary if there are many objects
            if total_objects > 4:
                response_text += " and some other objects further away."
        else:
            # Check if it's just dark or blurry
            instruction = status.get('instruction', '')
            if "Check the cam" in instruction or "Camera is not clear" in instruction:
                response_text = instruction
            else:
                response_text = "The scene appears to be clear. I don't see any specific obstacles right now."
    elif 'sos' in cmd or 'help' in cmd:
        # Placeholder for SOS logic
        print("SOS ACTIVATED. Sending Alert...")
    elif 'sos' in cmd or 'help' in cmd:
        # Placeholder for SOS logic
        print("SOS ACTIVATED. Sending Alert...")
        response_text = "SOS Alert Sent"
    elif 'start' in cmd:
        response_text = "System is already active."
    elif 'stop' in cmd or 'exit' in cmd or 'shut down' in cmd:
        response_text = "Stopping application. Goodbye."
        # Schedule shutdown after a short delay to allow response to be sent
        threading.Timer(1.0, shutdown_server).start()
        
        
    return jsonify({"message": response_text})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True, threaded=True)
