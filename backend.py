from flask import Flask, request, jsonify, send_file, send_from_directory
from flask_cors import CORS
import requests
import re
import os
import json
from urllib.parse import urljoin, unquote
import tempfile
import threading
import time

app = Flask(__name__, static_folder='.')
CORS(app)

USER_AGENT = (
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
    'AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
)

# Store video info and download progress
video_cache = {}
download_progress = {}

def extract_with_playwright(page_url):
    """
    Uses Playwright to load the page and intercept media URLs from network requests.
    """
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        return None, "Playwright not installed. Install with: pip install playwright && playwright install"

    media_urls = []
    error_message = None

    # Try to resolve redirects quickly with a simple requests call first
    try:
        resp = requests.get(page_url, headers={'User-Agent': USER_AGENT}, timeout=10, allow_redirects=True)
        final_url = resp.url or page_url
        print(f"[DEBUG] Resolved final URL: {final_url}")
    except Exception:
        final_url = page_url

    with sync_playwright() as p:
        print("[DEBUG] Launching browser...")
        browser = p.chromium.launch(headless=True)  # Changed to headless for server
        
        context = browser.new_context(
            user_agent=USER_AGENT,
            viewport={'width': 1920, 'height': 1080},
            locale='en-US',
        )
        page = context.new_page()

        def handle_response(response):
            try:
                rurl = response.url
                
                # Filter out known ad domains immediately
                ad_patterns = [
                    'trafficjunky', 'adtng', 'doubleclick', 'googlesyndication',
                    'adserver', 'ads.', 'adcdn', 'exoclick', 'juicyads',
                    'adnium', 'contentabc', 'propellerads', 'popads',
                    'vcmdiawe.com', 'galleryn'
                ]
                
                if any(ad in rurl.lower() for ad in ad_patterns):
                    return

                # Look for actual video CDN domains
                video_cdn_patterns = [
                    'phncdn.com', 'pornhub.com', 'phcdn', 'cv.phncdn.com',
                    'di.phncdn.com', 'ev.phncdn.com'
                ]
                
                # Check for video files
                if re.search(r'\.(mp4|m3u8|m4s)(?:\?|$)', rurl, re.IGNORECASE):
                    is_video_cdn = any(cdn in rurl.lower() for cdn in video_cdn_patterns)
                    
                    if is_video_cdn:
                        media_urls.append(rurl)
                        print(f"[DEBUG] ✓ Found VIDEO URL (network): {rurl[:100]}")
                    else:
                        media_urls.append(rurl)
                        print(f"[DEBUG] ? Found media URL (unknown CDN): {rurl[:100]}")
                
                # Check XHR/Fetch responses for video URLs in JSON
                req = response.request
                rtype = getattr(req, 'resource_type', None) or getattr(req, 'resourceType', None)
                if rtype and str(rtype).lower() in ('xhr', 'fetch'):
                    try:
                        text = response.text()
                        for m in re.findall(r'https?://[^\s"\'<>]+phncdn\.com[^\s"\'<>]+\.mp4[^\s"\'<>]*', text, re.IGNORECASE):
                            m = m.replace('\\/', '/')
                            media_urls.append(m)
                            print(f"[DEBUG] ✓ Found VIDEO URL (xhr/json): {m[:100]}")
                    except Exception:
                        pass
                        
            except Exception as e:
                print(f"[DEBUG] Error processing response: {e}")

        page.on('response', handle_response)

        try:
            print(f"[DEBUG] Navigating to {final_url}...")
            page.goto(final_url, timeout=60000, wait_until='domcontentloaded')
            print("[DEBUG] Page DOM loaded")

            # Try to click play button to trigger video loading
            try:
                page.wait_for_selector('video, .video-wrapper, #player', timeout=5000)
                
                play_selectors = [
                    '.mgp_playButton',
                    'button[aria-label="Play"]',
                    '.play-icon',
                    'button.play',
                    '.vjs-big-play-button'
                ]
                
                for selector in play_selectors:
                    try:
                        if page.locator(selector).count() > 0:
                            page.locator(selector).first.click()
                            break
                    except:
                        continue
                        
            except Exception as e:
                print(f"[DEBUG] Could not interact with video player: {e}")

            # Wait for video to start loading
            page.wait_for_timeout(10000)

            # Extract from page scripts
            try:
                script_extraction = """() => {
                    const urls = new Set();
                    
                    if (typeof flashvars !== 'undefined') {
                        if (flashvars.mediaDefinitions) {
                            flashvars.mediaDefinitions.forEach(def => {
                                if (def.videoUrl) urls.add(def.videoUrl);
                            });
                        }
                        
                        Object.keys(flashvars).forEach(key => {
                            if (key.startsWith('quality_') && flashvars[key]) {
                                urls.add(flashvars[key]);
                            }
                        });
                    }
                    
                    document.querySelectorAll('script').forEach(script => {
                        const text = script.textContent;
                        const qualityRegex = /"quality_(\d+)p"\s*:\s*"([^"]+)"/g;
                        let match;
                        while ((match = qualityRegex.exec(text)) !== null) {
                            if (match[2] && match[2].includes('phncdn')) {
                                urls.add(match[2]);
                            }
                        }
                    });
                    
                    return Array.from(urls);
                }"""
                
                script_urls = page.evaluate(script_extraction)
                if script_urls:
                    media_urls.extend(script_urls)
                    print(f"[DEBUG] ✓ Found {len(script_urls)} URLs from page scripts")
                        
            except Exception as e:
                print(f"[DEBUG] Script extraction error: {e}")

            # Extract metadata for thumbnail and title
            try:
                metadata = page.evaluate("""() => {
                    const title = document.querySelector('h1.title, .video-title, meta[property="og:title"]')?.textContent || 
                                  document.querySelector('meta[property="og:title"]')?.getAttribute('content') || 
                                  'Video';
                    const thumbnail = document.querySelector('meta[property="og:image"]')?.getAttribute('content') || 
                                      document.querySelector('video')?.getAttribute('poster') || '';
                    return { title, thumbnail };
                }""")
                
                browser.close()
                return media_urls, None, metadata
                
            except Exception as e:
                print(f"[DEBUG] Metadata extraction error: {e}")
                browser.close()
                return media_urls, None, {'title': 'Video', 'thumbnail': ''}
                
        except Exception as e:
            error_message = str(e)
            browser.close()
            return media_urls, error_message, None

def probe_urls(urls):
    """Probe URLs to get file size and quality information."""
    headers = {
        'User-Agent': USER_AGENT,
        'Referer': 'https://www.pornhub.com/',
        'Range': 'bytes=0-0'
    }
    
    results = []
    seen_urls = set()
    
    for url in urls:
        if url in seen_urls:
            continue
        seen_urls.add(url)
        
        # Detect if HLS stream
        is_hls = bool(re.search(r'\.m3u8(?:\?|$)', url, re.IGNORECASE))
        
        # Extract quality from URL
        quality_match = re.search(r'(\d{3,4})[pP]', url)
        quality = quality_match.group(1) + 'p' if quality_match else 'Unknown'
        
        if is_hls:
            results.append({
                'url': url,
                'quality': quality,
                'size': 0,
                'size_readable': 'Stream',
                'is_hls': True,
                'is_valid': True
            })
            continue
        
        # Probe regular MP4
        try:
            resp = requests.head(url, headers=headers, timeout=10, allow_redirects=True)
            content_range = resp.headers.get('Content-Range', '')
            content_length = resp.headers.get('Content-Length', '0')
            
            if content_range:
                match = re.search(r'/(\d+)', content_range)
                size = int(match.group(1)) if match else int(content_length)
            else:
                size = int(content_length)
            
            size_mb = size / (1024 * 1024)
            is_valid = size > 1024 * 1024  # At least 1MB
            
            results.append({
                'url': url,
                'quality': quality,
                'size': size,
                'size_readable': f"{size_mb:.1f} MB",
                'is_hls': False,
                'is_valid': is_valid
            })
            
        except Exception as e:
            print(f"[DEBUG] Failed to probe {url[:80]}: {e}")
            continue
    
    # Sort by quality (descending)
    def quality_sort_key(item):
        q = item['quality']
        match = re.search(r'(\d+)', q)
        return int(match.group(1)) if match else 0
    
    results.sort(key=quality_sort_key, reverse=True)
    return results

@app.route('/api/fetch-video', methods=['POST'])
def fetch_video():
    """Endpoint to fetch video information."""
    data = request.json
    url = data.get('url', '').strip()
    
    if not url:
        return jsonify({'error': 'No URL provided'}), 400
    
    print(f"[API] Fetching video info for: {url}")
    
    # Extract video URLs using Playwright
    media_urls, error, metadata = extract_with_playwright(url)
    
    if error:
        return jsonify({'error': error}), 500
    
    if not media_urls:
        return jsonify({'error': 'No video URLs found'}), 404
    
    print(f"[API] Found {len(media_urls)} URLs, probing...")
    
    # Probe URLs for size and quality
    probed = probe_urls(media_urls)
    valid_videos = [p for p in probed if p['is_valid']]
    
    if not valid_videos:
        return jsonify({'error': 'No valid video URLs found'}), 404
    
    # Store in cache
    video_id = str(hash(url))
    video_cache[video_id] = {
        'title': metadata.get('title', 'Video') if metadata else 'Video',
        'thumbnail': metadata.get('thumbnail', '') if metadata else '',
        'qualities': valid_videos
    }
    
    print(f"[API] Successfully extracted {len(valid_videos)} valid qualities")
    
    return jsonify({
        'video_id': video_id,
        'title': video_cache[video_id]['title'],
        'thumbnail': video_cache[video_id]['thumbnail'],
        'qualities': [{
            'quality': q['quality'],
            'size': q['size_readable'],
            'type': 'HLS' if q['is_hls'] else 'MP4',
            'is_hls': q['is_hls'],
            'index': i
        } for i, q in enumerate(valid_videos)]
    })

@app.route('/api/download/<video_id>/<int:quality_index>', methods=['GET'])
def download_video(video_id, quality_index):
    """Endpoint to download a specific quality."""
    if video_id not in video_cache:
        return jsonify({'error': 'Video not found'}), 404
    
    video_info = video_cache[video_id]
    
    if quality_index >= len(video_info['qualities']):
        return jsonify({'error': 'Invalid quality index'}), 400
    
    quality_data = video_info['qualities'][quality_index]
    url = quality_data['url']
    
    print(f"[API] Downloading: {quality_data['quality']} from {url[:80]}")
    
    # For HLS streams, return error (would need ffmpeg/yt-dlp)
    if quality_data['is_hls']:
        return jsonify({
            'error': 'HLS streams require ffmpeg or yt-dlp. Please copy the URL and use a download tool.',
            'url': url
        }), 400
    
    # Download regular MP4
    headers = {
        'User-Agent': USER_AGENT,
        'Referer': 'https://www.pornhub.com/',
    }
    
    try:
        # Stream the file
        response = requests.get(url, headers=headers, stream=True, timeout=30)
        response.raise_for_status()
        
        # Create temporary file
        filename = f"video_{quality_data['quality']}.mp4"
        
        # Stream response back to client
        def generate():
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:
                    yield chunk
        
        return app.response_class(
            generate(),
            mimetype='video/mp4',
            headers={
                'Content-Disposition': f'attachment; filename="{filename}"',
                'Content-Type': 'video/mp4'
            }
        )
        
    except Exception as e:
        print(f"[API] Download error: {e}")
        return jsonify({'error': f'Download failed: {str(e)}'}), 500

@app.route('/')
def index():
    """Serve the frontend."""
    try:
        return send_from_directory('.', 'video-downloader.html')
    except:
        return send_file('video-downloader.html')

if __name__ == '__main__':
    import socket
    
    # Check if running in production (Heroku/Railway/Render)
    port = int(os.environ.get('PORT', 5000))
    is_production = os.environ.get('RAILWAY_ENVIRONMENT') or os.environ.get('RENDER') or os.environ.get('DYNO')
    
    if is_production:
        print("="*60)
        print("Video Downloader API Server - PRODUCTION MODE")
        print("="*60)
        print(f"Server starting on port {port}")
        print("="*60)
        app.run(host='0.0.0.0', port=port)
    else:
        # Get local IP address for development
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            s.connect(('8.8.8.8', 80))
            local_ip = s.getsockname()[0]
        except:
            local_ip = '127.0.0.1'
        finally:
            s.close()
        
        print("="*60)
        print("Video Downloader API Server - DEVELOPMENT MODE")
        print("="*60)
        print(f"Server starting...")
        print(f"\n📍 Access from this computer:")
        print(f"   http://localhost:{port}")
        print(f"\n📱 Access from mobile/other devices on same WiFi:")
        print(f"   http://{local_ip}:{port}")
        print(f"\nMake sure Playwright is installed: pip install playwright")
        print(f"Then run: playwright install chromium")
        print("="*60)
        app.run(debug=True, host='0.0.0.0', port=port)
