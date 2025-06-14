import os
import tempfile
import yt_dlp
from flask import Blueprint, request, jsonify, send_file
from flask_cors import cross_origin
import threading
import time

youtube_bp = Blueprint('youtube', __name__)

# Dicionário para armazenar status dos downloads
download_status = {}

def download_video(url, format_id, download_id, output_dir):
    """Função para baixar vídeo em thread separada"""
    try:
        download_status[download_id] = {'status': 'downloading', 'progress': 0}
        
        def progress_hook(d):
            if d['status'] == 'downloading':
                if 'total_bytes' in d and d['total_bytes']:
                    progress = (d['downloaded_bytes'] / d['total_bytes']) * 100
                    download_status[download_id]['progress'] = round(progress, 1)
                elif '_percent_str' in d:
                    # Extrair porcentagem do string
                    percent_str = d['_percent_str'].strip().replace('%', '')
                    try:
                        progress = float(percent_str)
                        download_status[download_id]['progress'] = round(progress, 1)
                    except:
                        pass
            elif d['status'] == 'finished':
                download_status[download_id] = {
                    'status': 'completed', 
                    'progress': 100,
                    'filename': d['filename']
                }
        
        ydl_opts = {
            'format': format_id,
            'outtmpl': os.path.join(output_dir, '%(title)s.%(ext)s'),
            'progress_hooks': [progress_hook],
            'no_warnings': True,
        }
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])
            
    except Exception as e:
        download_status[download_id] = {
            'status': 'error', 
            'error': str(e)
        }

@youtube_bp.route('/info', methods=['POST'])
@cross_origin()
def get_video_info():
    """Obter informações do vídeo"""
    try:
        data = request.get_json()
        url = data.get('url')
        
        if not url:
            return jsonify({'error': 'URL é obrigatória'}), 400
        
        ydl_opts = {
            'quiet': True,
            'no_warnings': True,
        }
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            
            # Filtrar formatos para MP4 apenas
            formats = []
            for f in info.get('formats', []):
                if f.get('ext') == 'mp4' and f.get('vcodec') != 'none':
                    formats.append({
                        'format_id': f['format_id'],
                        'ext': f['ext'],
                        'resolution': f.get('resolution', 'N/A'),
                        'filesize': f.get('filesize'),
                        'filesize_approx': f.get('filesize_approx'),
                        'quality': f.get('height', 0)
                    })
            
            # Ordenar por qualidade
            formats.sort(key=lambda x: x['quality'], reverse=True)
            
            return jsonify({
                'title': info.get('title'),
                'duration': info.get('duration'),
                'thumbnail': info.get('thumbnail'),
                'formats': formats[:10]  # Limitar a 10 formatos
            })
            
    except Exception as e:
        return jsonify({'error': f'Erro ao obter informações: {str(e)}'}), 500

@youtube_bp.route('/download', methods=['POST'])
@cross_origin()
def start_download():
    """Iniciar download do vídeo"""
    try:
        data = request.get_json()
        url = data.get('url')
        format_id = data.get('format_id', 'best[ext=mp4]')
        
        if not url:
            return jsonify({'error': 'URL é obrigatória'}), 400
        
        # Gerar ID único para o download
        download_id = str(int(time.time() * 1000))
        
        # Criar diretório temporário
        output_dir = tempfile.mkdtemp()
        
        # Iniciar download em thread separada
        thread = threading.Thread(
            target=download_video, 
            args=(url, format_id, download_id, output_dir)
        )
        thread.start()
        
        return jsonify({
            'download_id': download_id,
            'status': 'started'
        })
        
    except Exception as e:
        return jsonify({'error': f'Erro ao iniciar download: {str(e)}'}), 500

@youtube_bp.route('/status/<download_id>', methods=['GET'])
@cross_origin()
def get_download_status(download_id):
    """Verificar status do download"""
    status = download_status.get(download_id, {'status': 'not_found'})
    return jsonify(status)

@youtube_bp.route('/download/<download_id>', methods=['GET'])
@cross_origin()
def download_file(download_id):
    """Baixar arquivo completado"""
    status = download_status.get(download_id)
    
    if not status or status.get('status') != 'completed':
        return jsonify({'error': 'Download não encontrado ou não completado'}), 404
    
    filename = status.get('filename')
    if not filename or not os.path.exists(filename):
        return jsonify({'error': 'Arquivo não encontrado'}), 404
    
    return send_file(
        filename,
        as_attachment=True,
        download_name=os.path.basename(filename)
    )

