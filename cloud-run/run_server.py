"""
Cloud Run HTTP server wrapper cho crawler
Cloud Run gửi HTTP request để trigger crawler job
"""
import os
import subprocess
from flask import Flask, request, jsonify

app = Flask(__name__)

@app.route('/', methods=['POST', 'GET'])
def run_crawler():
    """Trigger crawler khi nhận HTTP request từ Cloud Run"""
    raw_bucket = os.getenv('RAW_BUCKET', request.args.get('raw_bucket'))
    if not raw_bucket:
        return jsonify({'error': 'Missing RAW_BUCKET env or raw_bucket param'}), 400
    
    run_date = os.getenv('RUN_DATE', request.args.get('run_date', ''))
    source = os.getenv('SOURCE', request.args.get('source', 'mogi'))
    max_pages = int(os.getenv('MAX_PAGES', request.args.get('max_pages', '400')))
    
    # Chạy crawler
    cmd = [
        'python', 'extract.py',
        '--raw_bucket', raw_bucket,
        '--source', source,
        '--max_pages', str(max_pages)
    ]
    if run_date:
        cmd.extend(['--run_date', run_date])
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=3600)
        return jsonify({
            'status': 'completed' if result.returncode == 0 else 'failed',
            'returncode': result.returncode,
            'stdout': result.stdout[-1000:],  # last 1000 chars
            'stderr': result.stderr[-1000:]
        }), 200 if result.returncode == 0 else 500
    except subprocess.TimeoutExpired:
        return jsonify({'error': 'Crawler timeout after 1 hour'}), 500
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/health', methods=['GET'])
def health():
    """Health check endpoint"""
    return jsonify({'status': 'healthy'}), 200

if __name__ == '__main__':
    port = int(os.getenv('PORT', 8080))
    app.run(host='0.0.0.0', port=port, debug=False)

