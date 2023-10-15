from flask import Flask, request, jsonify, send_file
from flask_cors import CORS, cross_origin
import dotenv
import os
import tempfile
import subprocess
import uuid
import hashlib
import shutil
from statistics import harmonic_mean

dotenv.load_dotenv()

AUBIO_PATH = os.environ.get('AUBIO_PATH')
aubiotrack = os.path.join(AUBIO_PATH, 'aubiotrack')
aubioonset = os.path.join(AUBIO_PATH, 'aubioonset')

FFMPEG = os.environ.get('FFMPEG_BIN')

app = Flask(__name__)
cors = CORS(app)
app.config['CORS_HEADERS'] = 'Content-Type'

# Placeholder variable to store uploaded file metadata
uploaded_file_metadata = {}

def calculate_bpm(music_file: str) -> float:
    result = subprocess.run([aubiotrack, '-i', music_file], stdout=subprocess.PIPE)
    beats = [float(x) for x in result.stdout.decode('utf-8').splitlines()]
    timing = []
    p = 0
    for b in beats:
        timing.append(b - p)
        p = b
    m = harmonic_mean(timing)
    bpm = round(60 / m)
    return bpm

def calculate_first_beat(music_file: str):
    result = subprocess.run([aubioonset, '-i', music_file], stdout=subprocess.PIPE)
    beats = result.stdout.decode('utf-8').splitlines()
    return float(beats[0])

def ffmpeg_to_wav(music_file: str, output: str):
    print('FFMPGE Out', output)
    subprocess.run([FFMPEG, '-i', music_file, output])

@app.route('/upload', methods=['POST'])
@cross_origin()
def upload():
    file_field = 'music_file'
    print(request.files)
    if file_field not in request.files:
        return jsonify({'error': 'No file uploaded'}), 400

    file = request.files[file_field]
    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400
    
    #file_md5 = hashlib.md5(file.stream.read()).hexdigest()
    file_md5 = '1'
    
    temp_dir = tempfile.mkdtemp()

    tmp_file_name = os.path.join(temp_dir, str(uuid.uuid4()))
    file.save(tmp_file_name)
    # tmp_file = open(tmp_file_name, 'wb')
    # tmp_file.write(file.stream.read())
    print('Uploaded tmp', tmp_file_name)

    new_tmp_name = os.path.join(temp_dir, str(uuid.uuid4()) + '.wav')
    ffmpeg_to_wav(tmp_file_name, new_tmp_name)
    bpm = calculate_bpm(new_tmp_name)
    first_beat = calculate_first_beat(new_tmp_name)

    #tmp_file.close()
    shutil.rmtree(temp_dir)

    print('BPM', bpm)
    print('First beat', first_beat)

    uploaded_file_metadata[file_md5] = (bpm, first_beat)

    return jsonify({'message': 'File uploaded successfully', 'id': file_md5, 'bpm': bpm, 'offset': first_beat}), 200

@app.route('/metadata', methods=['GET'])
@cross_origin()
def metadata():
    hash = request.args.get('id')
    if hash in uploaded_file_metadata:
        bpm, offset = uploaded_file_metadata[hash]
        return jsonify({'bpm': bpm, 'offset': offset}), 200

    return jsonify({'message': 'Not Found'}), 404

@app.get('/')
def index():
    return send_file('me.html')

@app.get('/wooden_fish.mp3')
@cross_origin()
def beat():
    return send_file('wooden_fish.mp3')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=3001)