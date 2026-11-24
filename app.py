import os
import subprocess
import uuid
import threading
import sys
import json
import time
import socket
import urllib.request
import webbrowser
from flask import Flask, render_template, request, jsonify
from pathlib import Path
from werkzeug.utils import secure_filename

if getattr(sys, 'frozen', False):
    BASE_DIR     = os.path.dirname(sys.executable)
    TEMPLATE_DIR = os.path.join(sys._MEIPASS, 'templates')
else:
    BASE_DIR     = os.path.dirname(os.path.abspath(__file__))
    TEMPLATE_DIR = os.path.join(BASE_DIR, 'templates')

UPLOAD_FOLDER = os.path.join(BASE_DIR, 'uploads')
OUTPUT_FOLDER = os.path.join(BASE_DIR, 'output')

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(OUTPUT_FOLDER, exist_ok=True)

# Pasta de saída selecionada pelo usuário (sobrescreve OUTPUT_FOLDER)
custom_output = {'folder': None}

app = Flask(__name__, template_folder=TEMPLATE_DIR)

BUILD_VERSION = "1.3 · 05/05/2026"

jobs      = {}
jobs_lock = threading.Lock()
semaphore = threading.Semaphore(2)

ALLOWED = {'.mp4', '.mov', '.avi', '.mkv', '.wmv', '.flv', '.webm', '.m4v'}

# ───────── Servidor único + desligamento automático ─────────
APP_NOME     = "DadosOFF"
PORT         = 5555
_NO_WINDOW   = 0x08000000                 # CREATE_NO_WINDOW (não pisca console no modo windowed)
_ultimo_ping = time.time() + 120          # carência inicial de 120 s (tempo do navegador abrir)


def _ocupado():
    # NUNCA desligar com fila/processamento em andamento
    with jobs_lock:
        return any(j.get('status') in ('queued', 'processing') for j in jobs.values())


def _vigia():
    while True:
        time.sleep(5)
        if _ocupado():
            continue
        if time.time() - _ultimo_ping > 90:   # Chrome segura aba em 2º plano a 1 ping/min
            os._exit(0)


def _instancia_viva():
    # Já existe um DadosOFF rodando nesta porta?
    try:
        with urllib.request.urlopen(f'http://127.0.0.1:{PORT}/__ping', timeout=1.5) as r:
            return json.loads(r.read().decode()).get('app') == APP_NOME
    except Exception:
        return False


def _porta_ocupada():
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.settimeout(1)
    try:
        return s.connect_ex(('127.0.0.1', PORT)) == 0
    finally:
        s.close()


def _matar_porta():
    # Processo antigo/travado segurando a porta → mata antes de subir o novo
    try:
        out = subprocess.run(
            ['powershell', '-NoProfile', '-Command',
             f"Get-NetTCPConnection -LocalPort {PORT} -State Listen -ErrorAction SilentlyContinue "
             f"| Select-Object -ExpandProperty OwningProcess"],
            capture_output=True, text=True, timeout=10, creationflags=_NO_WINDOW
        )
        for pid in set(out.stdout.split()):
            if pid.isdigit() and int(pid) != os.getpid():
                subprocess.run(['taskkill', '/F', '/PID', pid],
                               capture_output=True, creationflags=_NO_WINDOW)
        time.sleep(1.5)
    except Exception:
        pass


@app.get('/__ping')
def __ping():
    global _ultimo_ping
    _ultimo_ping = time.time()
    return jsonify({'app': APP_NOME})


@app.post('/__bye')
def __bye():
    # F5 também dispara pagehide → não mata na hora, só encurta a espera p/ ~10 s
    global _ultimo_ping
    _ultimo_ping = min(_ultimo_ping, time.time() - 80)
    return ''

PRIVACY_FIELDS = {
    'title':               'Título',
    'artist':              'Artista',
    'author':              'Autor',
    'album':               'Álbum',
    'comment':             'Comentário',
    'description':         'Descrição',
    'copyright':           'Copyright',
    'creation_time':       'Data de criação',
    'modification_time':   'Data de modificação',
    'date':                'Data',
    'year':                'Ano',
    'encoder':             'Software de edição',
    'encoded_by':          'Codificado por',
    'software':            'Software',
    'location':            'Localização GPS',
    'com.apple.quicktime.location.iso6709': 'GPS (Apple)',
    'com.apple.quicktime.location.accuracy.horizontal': 'GPS precisão',
    'make':                'Fabricante câmera',
    'model':               'Modelo câmera',
    'device':              'Dispositivo',
    'producer':            'Produtor',
    'director':            'Diretor',
}


def get_ffmpeg():
    bundled = os.path.join(BASE_DIR, 'ffmpeg', 'ffmpeg.exe')
    return bundled if os.path.exists(bundled) else 'ffmpeg'


def get_ffprobe():
    bundled = os.path.join(BASE_DIR, 'ffmpeg', 'ffprobe.exe')
    return bundled if os.path.exists(bundled) else 'ffprobe'


_nvenc_cache = None

def nvenc_available():
    global _nvenc_cache
    if _nvenc_cache is not None:
        return _nvenc_cache
    try:
        import tempfile
        tmp = tempfile.mktemp(suffix='.mp4')
        result = subprocess.run(
            [get_ffmpeg(), '-f', 'lavfi', '-i', 'testsrc=size=256x256:rate=25:duration=1',
             '-pix_fmt', 'yuv420p', '-c:v', 'h264_nvenc', '-rc', 'constqp', '-qp', '23',
             '-y', tmp],
            capture_output=True, timeout=15
        )
        _nvenc_cache = result.returncode == 0
        try:
            os.remove(tmp)
        except Exception:
            pass
    except Exception:
        _nvenc_cache = False
    return _nvenc_cache


def extract_metadata(file_path):
    try:
        result = subprocess.run(
            [get_ffprobe(), '-v', 'quiet', '-print_format', 'json',
             '-show_format', '-show_streams', file_path],
            capture_output=True, text=True, timeout=30
        )
        data = json.loads(result.stdout)
        tags = {}
        tags.update(data.get('format', {}).get('tags', {}))
        for stream in data.get('streams', []):
            tags.update(stream.get('tags', {}))
        return {
            k: v for k, v in tags.items()
            if k.lower() in PRIVACY_FIELDS and v and str(v).strip()
        }
    except Exception:
        return {}


def build_cmd_clean(ffmpeg, input_path, output_path):
    return [
        ffmpeg,
        '-i', input_path,
        '-map_metadata', '-1',
        '-map_chapters', '-1',
        '-fflags', '+bitexact',
        '-flags:v', '+bitexact',
        '-flags:a', '+bitexact',
        '-c:v', 'copy',
        '-c:a', 'copy',
        '-y', output_path,
    ]


COMPRESS_PRESETS = {
    'alta':   {'cq': '23', 'crf': '23', 'label': 'Alta qualidade'},
    'media':  {'cq': '28', 'crf': '28', 'label': 'Balanceada'},
    'maxima': {'cq': '35', 'crf': '35', 'label': 'Máxima compressão'},
}


def build_cmd_reencode(ffmpeg, input_path, output_path, use_nvenc, cq='18', crf='18'):
    base = [ffmpeg, '-i', input_path, '-map_metadata', '-1', '-map_chapters', '-1', '-fflags', '+bitexact']
    if use_nvenc:
        video = ['-pix_fmt', 'yuv420p', '-c:v', 'h264_nvenc', '-rc', 'constqp', '-qp', cq, '-preset', 'p4']
    else:
        video = ['-pix_fmt', 'yuv420p', '-c:v', 'libx264', '-crf', crf, '-preset', 'medium']
    audio = ['-c:a', 'aac', '-b:a', '192k']
    return base + video + audio + ['-y', output_path]


def run_cmd(cmd, fallback_cmd=None, timeout=7200):
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    if result.returncode != 0 and fallback_cmd:
        result = subprocess.run(fallback_cmd, capture_output=True, text=True, timeout=timeout)
    return result


def process_video(job_id, input_path, output_path, mode, quality='media'):
    with semaphore:
        input_size = os.path.getsize(input_path)
        with jobs_lock:
            jobs[job_id]['status']     = 'processing'
            jobs[job_id]['input_size'] = input_size

        ffmpeg     = get_ffmpeg()
        use_nvenc  = False
        preset     = COMPRESS_PRESETS.get(quality, COMPRESS_PRESETS['media'])

        try:
            if mode == 'clean':
                cmd = build_cmd_clean(ffmpeg, input_path, output_path)
                result = run_cmd(cmd)
            else:
                use_nvenc = nvenc_available()
                with jobs_lock:
                    jobs[job_id]['gpu'] = use_nvenc
                cq, crf = preset['cq'], preset['crf']
                cmd     = build_cmd_reencode(ffmpeg, input_path, output_path, use_nvenc, cq, crf)
                fallback = build_cmd_reencode(ffmpeg, input_path, output_path, False, cq, crf) if use_nvenc else None
                result  = run_cmd(cmd, fallback)
                if fallback and result.returncode == 0:
                    with jobs_lock:
                        jobs[job_id]['gpu'] = False

            with jobs_lock:
                if result.returncode == 0:
                    out_size = os.path.getsize(output_path)
                    savings  = round((1 - out_size / input_size) * 100) if input_size else 0
                    jobs[job_id]['status']      = 'done'
                    jobs[job_id]['output_name'] = os.path.basename(output_path)
                    jobs[job_id]['output_size'] = out_size
                    jobs[job_id]['savings']     = savings
                else:
                    jobs[job_id]['status'] = 'error'
                    jobs[job_id]['error']  = 'Erro no processamento'

        except subprocess.TimeoutExpired:
            with jobs_lock:
                jobs[job_id]['status'] = 'error'
                jobs[job_id]['error']  = 'Tempo limite excedido'
        except Exception as e:
            with jobs_lock:
                jobs[job_id]['status'] = 'error'
                jobs[job_id]['error']  = str(e)
        finally:
            try:
                os.remove(input_path)
            except Exception:
                pass


@app.route('/')
def index():
    return render_template('index.html', version=BUILD_VERSION)


@app.route('/upload', methods=['POST'])
def upload():
    mode    = request.form.get('mode', 'clean')
    quality = request.form.get('quality', 'media')
    results = []

    for file in request.files.getlist('videos'):
        if not file.filename:
            continue
        ext = Path(file.filename).suffix.lower()
        if ext not in ALLOWED:
            continue

        job_id      = str(uuid.uuid4())
        safe        = secure_filename(file.filename)
        input_path  = os.path.join(UPLOAD_FOLDER, f'{job_id}{ext}')
        out_dir     = custom_output['folder'] or OUTPUT_FOLDER
        os.makedirs(out_dir, exist_ok=True)
        output_path = os.path.join(out_dir, safe)

        file.save(input_path)
        meta_before = extract_metadata(input_path)

        with jobs_lock:
            jobs[job_id] = {
                'filename':        file.filename,
                'output_name':     safe,
                'status':          'queued',
                'mode':            mode,
                'gpu':             None,
                'error':           None,
                'metadata_before': meta_before,
            }

        t = threading.Thread(
            target=process_video,
            args=(job_id, input_path, output_path, mode, quality),
            daemon=True
        )
        t.start()
        results.append({'job_id': job_id, 'filename': file.filename})

    return jsonify({'jobs': results})


@app.route('/status/<job_id>')
def get_status(job_id):
    with jobs_lock:
        job = jobs.get(job_id)
    if not job:
        return jsonify({'status': 'not_found'}), 404
    return jsonify(job)


@app.route('/set_folder', methods=['POST'])
def set_folder():
    data   = request.get_json()
    folder = (data.get('folder') or '').strip()
    if not folder:
        return jsonify({'ok': False, 'error': 'Caminho vazio'})
    if not os.path.isabs(folder):
        return jsonify({'ok': False, 'error': 'Caminho inválido'})
    os.makedirs(folder, exist_ok=True)
    custom_output['folder'] = folder
    return jsonify({'ok': True, 'folder': folder})


@app.route('/current_folder')
def current_folder():
    return jsonify({'folder': custom_output['folder'] or OUTPUT_FOLDER})


@app.route('/open_output')
def open_output():
    folder = custom_output['folder'] or OUTPUT_FOLDER
    os.startfile(folder)
    return jsonify({'ok': True})


if __name__ == '__main__':
    # Uma instância só: se já tem DadosOFF vivo, só abre o navegador e sai
    if _instancia_viva():
        webbrowser.open(f'http://localhost:{PORT}')
        sys.exit(0)
    # Porta presa por processo antigo/travado → mata antes de subir
    if _porta_ocupada():
        _matar_porta()
    threading.Thread(target=_vigia, daemon=True).start()
    threading.Timer(1.2, lambda: webbrowser.open(f'http://localhost:{PORT}')).start()
    app.run(host='127.0.0.1', port=PORT, debug=False, use_reloader=False)
