from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import os
import time
import re
import logging
from collections import Counter
import json
from datetime import datetime

logging.basicConfig(
    level=logging.INFO, 
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('app.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

def safe_import(module_name, fallback_message=None):
    """Safely import modules with error handling"""
    try:
        return __import__(module_name)
    except ImportError as e:
        logger.warning(f"Failed to import {module_name}: {e}")
        if fallback_message:
            logger.info(fallback_message)
        return None

nltk = safe_import('nltk', "Text processing will use basic fallbacks without NLTK")

if nltk:
    try:
        nltk.data.find('tokenizers/punkt')
        nltk.data.find('corpora/stopwords')
    except LookupError:
        try:
            nltk.download('punkt', quiet=True)
            nltk.download('stopwords', quiet=True)
            logger.info("Downloaded NLTK data successfully")
        except Exception as e:
            logger.warning(f"Failed to download NLTK data: {e}")

# Initialize Flask app
app = Flask(__name__)

CORS(app, 
     origins=["http://localhost:3000", "http://127.0.0.1:3000", "http://localhost:8080", 
              "http://127.0.0.1:5500", "http://localhost:5500", "http://127.0.0.1:8080",
              "http://localhost:5000", "http://127.0.0.1:5000"],
     methods=['GET', 'POST', 'OPTIONS'],
     allow_headers=['Content-Type'])

# Configuration
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', os.urandom(24).hex())

def extract_keywords(text, num_keywords=10):
    """Extract key words from text with fallback"""
    try:
        if not nltk:
            # Simple fallback without NLTK
            words = re.findall(r'\b[a-zA-Z]{4,}\b', text.lower())
            word_freq = Counter(words)
            # Filter out common words manually
            common_words = {'this', 'that', 'with', 'have', 'will', 'from', 'they', 'been', 'were', 'said', 'each', 'which', 'their', 'time', 'more', 'very', 'what', 'know', 'just', 'first', 'into', 'over', 'think', 'also', 'your', 'work', 'life', 'only', 'can', 'still', 'should', 'after', 'being', 'now', 'made', 'before', 'here', 'through', 'when', 'where', 'much', 'some', 'these', 'many', 'would', 'there'}
            filtered_words = {word: freq for word, freq in word_freq.items() if word not in common_words}
            return [word for word, freq in Counter(filtered_words).most_common(num_keywords)]
        
        from nltk.corpus import stopwords
        from nltk.tokenize import word_tokenize
        
        stop_words = set(stopwords.words('english'))
        words = [w.lower() for w in word_tokenize(text) if w.isalnum() and w.lower() not in stop_words and len(w) > 3]
        word_freq = Counter(words)
        return [word for word, freq in word_freq.most_common(num_keywords)]
        
    except Exception as e:
        logger.warning(f"Keyword extraction failed: {e}")
        return []

def basic_sentence_split(text):
    """Basic sentence splitting without NLTK"""
    # Simple sentence splitting on periods, exclamation marks, and question marks
    sentences = re.split(r'[.!?]+', text)
    return [s.strip() for s in sentences if s.strip()]

def advanced_summarize(text, max_sentences=3, algorithm='frequency'):
    """Enhanced summarization with multiple algorithms and fallbacks"""
    if not text or not text.strip():
        return "No content to summarize.", []
    
    try:
        # Ensure text is a string and clean it
        text = str(text)
        text = re.sub(r'\s+', ' ', text).strip()
        
        # If text is too short, just return it
        if len(text.split()) < 5:
            return text, extract_keywords(text)
        
        # Get sentences
        if nltk:
            from nltk.tokenize import sent_tokenize
            sentences = sent_tokenize(text)
        else:
            sentences = basic_sentence_split(text)
        
        if len(sentences) <= 1:
            return (text[:200] + "..." if len(text) > 200 else text), extract_keywords(text)
        
        # Extract keywords first
        keywords = extract_keywords(text)
        
        if algorithm == 'frequency':
            # Frequency-based summarization
            if nltk:
                from nltk.tokenize import word_tokenize
                from nltk import FreqDist
                words = [w for w in word_tokenize(text.lower()) if w.isalnum()]
            else:
                words = re.findall(r'\b[a-zA-Z]+\b', text.lower())
            
            if not words:
                return (text[:200] + "..." if len(text) > 200 else text), keywords
            
            if nltk:
                freq = FreqDist(words)
            else:
                freq = Counter(words)
            
            # Score sentences
            sentence_scores = []
            for sentence in sentences:
                if nltk:
                    sentence_words = [w.lower() for w in word_tokenize(sentence) if w.isalnum()]
                else:
                    sentence_words = re.findall(r'\b[a-zA-Z]+\b', sentence.lower())
                
                score = sum(freq.get(w, 0) for w in sentence_words)
                sentence_scores.append((sentence, score))
            
            ranked_sentences = sorted(sentence_scores, key=lambda x: x[1], reverse=True)
            
        elif algorithm == 'position':
            # Position-based summarization
            def position_score(idx, total):
                if idx == 0 or idx == total - 1:  # First or last
                    return 3
                elif idx < total * 0.3:  # Early sentences
                    return 2
                else:
                    return 1
            
            ranked_sentences = [(sent, position_score(i, len(sentences))) for i, sent in enumerate(sentences)]
            ranked_sentences = sorted(ranked_sentences, key=lambda x: x[1], reverse=True)
        
        else:  # hybrid approach
            # Combine frequency and position scoring
            if nltk:
                from nltk.tokenize import word_tokenize
                from nltk import FreqDist
                words = [w for w in word_tokenize(text.lower()) if w.isalnum()]
                freq = FreqDist(words) if words else {}
            else:
                words = re.findall(r'\b[a-zA-Z]+\b', text.lower())
                freq = Counter(words) if words else {}
            
            def hybrid_score(sent, idx, total):
                if nltk:
                    sentence_words = [w.lower() for w in word_tokenize(sent) if w.isalnum()]
                else:
                    sentence_words = re.findall(r'\b[a-zA-Z]+\b', sent.lower())
                
                freq_score = sum(freq.get(w, 0) for w in sentence_words)
                pos_score = 3 if idx == 0 or idx == total - 1 else (2 if idx < total * 0.3 else 1)
                return freq_score + pos_score
            
            ranked_sentences = [(sent, hybrid_score(sent, i, len(sentences))) for i, sent in enumerate(sentences)]
            ranked_sentences = sorted(ranked_sentences, key=lambda x: x[1], reverse=True)
        
        # Get top sentences while preserving order
        top_sentences = [sent for sent, score in ranked_sentences[:max_sentences]]
        important_sentences = []
        for sentence in sentences:
            if sentence in top_sentences:
                important_sentences.append(sentence)
                
        summary = ' '.join(important_sentences)
        return (summary if summary.strip() else text[:200] + "..." if len(text) > 200 else text), keywords
        
    except Exception as e:
        logger.error(f"Error in summarization: {e}")
        # Fallback: return first few sentences
        sentences = text.split('.')
        fallback_summary = '.'.join(sentences[:max_sentences]) + '.'
        return fallback_summary, extract_keywords(text)

@app.route('/')
def serve_frontend():
    """Serve the HTML file"""
    try:
        return send_from_directory('.', 'index.html')
    except FileNotFoundError:
        return jsonify({'error': 'Frontend not found. Please ensure index.html is in the same directory.'}), 404

@app.route('/api/status', methods=['GET'])
def get_status():
    """Return API status and capabilities"""
    capabilities = {
        'text_summarization': True,
        'keyword_extraction': True,
        'nltk_support': nltk is not None
    }
    
    return jsonify({
        'status': 'online',
        'version': '3.0',
        'supported_formats': ['text'],
        'capabilities': capabilities,
        'features': ['text_summarization', 'keyword_extraction'],
        'timestamp': datetime.now().isoformat()
    })

@app.route('/api/summarize', methods=['POST', 'OPTIONS'])
def summarize():
    start_time = time.time()
    logger.info("Received summarize request")

    if request.method == 'OPTIONS':
        response = jsonify({'status': 'ok'})
        response.headers.add('Access-Control-Allow-Origin', request.headers.get('Origin', '*'))
        response.headers.add('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        response.headers.add('Access-Control-Allow-Headers', 'Content-Type')
        return response

    try:
        algorithm = request.form.get('algorithm', 'frequency')
        max_sentences = int(request.form.get('max_sentences', 3))
        
        # Validate parameters
        if algorithm not in ['frequency', 'position', 'hybrid']:
            algorithm = 'frequency'
        if max_sentences < 1 or max_sentences > 10:
            max_sentences = 3

        text = None
        
        # Check for text input
        if 'text' in request.form:
            text = request.form['text']
        elif request.is_json:
            data = request.get_json()
            text = data.get('text')
            algorithm = data.get('algorithm', 'frequency')
            max_sentences = int(data.get('max_sentences', 3))

        if text is None:
            return jsonify({'error': 'No text provided'}), 400

        text = text.strip()
        if not text:
            return jsonify({'error': 'Empty text provided'}), 400
        
        if len(text) > 100000:  # 100KB text limit
            return jsonify({'error': 'Text too long. Please limit to 100,000 characters.'}), 400
        
        logger.info(f"Text input received: {len(text)} characters")
        summary, keywords = advanced_summarize(text, max_sentences, algorithm)
        processing_time = int((time.time() - start_time) * 1000)
        original_length = len(text.split())
        summary_length = len(summary.split())
        compression_ratio = int((1 - (summary_length / original_length)) * 100) if original_length > 0 else 0

        response_data = {
            'summary': summary if summary.strip() else "No summary generated.",
            'keywords': keywords,
            'processing_time': processing_time,
            'compression_ratio': compression_ratio,
            'original_length': original_length,
            'summary_length': summary_length,
            'algorithm_used': algorithm
        }

        response = jsonify(response_data)
        response.headers.add('Access-Control-Allow-Origin', request.headers.get('Origin', '*'))
        return response

    except Exception as e:
        logger.error(f"Unexpected error in summarize endpoint: {e}")
        error_response = jsonify({'error': f'Server error: {str(e)}'})
        error_response.headers.add('Access-Control-Allow-Origin', request.headers.get('Origin', '*'))
        return error_response, 500

@app.route('/api/sample', methods=['GET'])
def get_sample_text():
    """Return sample text for demonstration"""
    samples = [
        {
            'title': 'Artificial Intelligence Revolution',
            'text': "Artificial intelligence (AI) is revolutionizing the way we work, live, and interact with technology. From machine learning algorithms that can predict consumer behavior to natural language processing systems that can understand and respond to human speech, AI is transforming industries across the globe. In healthcare, AI is being used to diagnose diseases more accurately and develop personalized treatment plans. In finance, AI algorithms are detecting fraud and making investment decisions. In transportation, autonomous vehicles powered by AI are becoming a reality. As AI continues to evolve, it promises to bring even more innovative solutions to complex problems, making our lives more efficient and productive."
        },
        {
            'title': 'Climate Change Challenge',
            'text': "Climate change represents one of the most pressing challenges of our time, with far-reaching implications for ecosystems, human societies, and the global economy. Rising global temperatures, caused primarily by greenhouse gas emissions from human activities, are leading to more frequent and severe weather events, including hurricanes, droughts, and floods. The melting of polar ice caps and glaciers is contributing to rising sea levels, threatening coastal communities worldwide. To address this crisis, governments, businesses, and individuals must work together to reduce carbon emissions, transition to renewable energy sources, and implement sustainable practices. The Paris Agreement represents a significant step forward in global climate action, but much more needs to be done to limit global warming and protect our planet for future generations."
        },
        {
            'title': 'Future of Remote Work',
            'text': "The COVID-19 pandemic has fundamentally transformed the way we think about work, accelerating the adoption of remote work practices across industries. Companies that once required physical presence have discovered that many tasks can be performed effectively from home, leading to increased flexibility and work-life balance for employees. This shift has also opened up new opportunities for businesses to access global talent pools and reduce overhead costs associated with maintaining large office spaces. However, remote work also presents challenges, including the need for robust digital infrastructure, effective communication tools, and strategies to maintain team cohesion and company culture. As we move forward, hybrid work models that combine remote and in-office work are likely to become the new standard, requiring organizations to adapt their management practices and invest in technology that supports distributed teams."
        }
    ]
    
    sample = samples[int(time.time()) % len(samples)]  # Rotate samples based on time
    response = jsonify(sample)
    return response

@app.route('/api/export', methods=['POST'])
def export_summary():
    """Export summary in various formats"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No data provided'}), 400
        
        summary = data.get('summary', '')
        keywords = data.get('keywords', [])
        stats = data.get('stats', {})
        format_type = data.get('format', 'txt')
        
        if format_type not in ['txt', 'md', 'json']:
            return jsonify({'error': 'Invalid format. Supported: txt, md, json'}), 400
        
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        if format_type == 'json':
            export_data = {
                'summary': summary,
                'keywords': keywords,
                'statistics': stats,
                'exported_at': timestamp,
                'version': '3.0'
            }
            content = json.dumps(export_data, indent=2)
            mimetype = 'application/json'
            
        elif format_type == 'md':
            content = f"""# Summary Report
Generated on: {timestamp}

## Summary
{summary}

## Keywords
{', '.join(keywords) if keywords else 'No keywords extracted'}

## Statistics
- Original Length: {stats.get('original_length', 'N/A')} words
- Summary Length: {stats.get('summary_length', 'N/A')} words
- Compression Ratio: {stats.get('compression_ratio', 'N/A')}%
- Processing Time: {stats.get('processing_time', 'N/A')}ms

---
*Generated by Summify Text-Only v3.0*
"""
            mimetype = 'text/markdown'
            
        else:  # txt format
            content = f"""SUMMARY REPORT
Generated on: {timestamp}

SUMMARY:
{summary}

KEYWORDS:
{', '.join(keywords) if keywords else 'No keywords extracted'}

STATISTICS:
Original Length: {stats.get('original_length', 'N/A')} words
Summary Length: {stats.get('summary_length', 'N/A')} words
Compression Ratio: {stats.get('compression_ratio', 'N/A')}%
Processing Time: {stats.get('processing_time', 'N/A')}ms

Generated by Summify Text-Only v3.0
"""
            mimetype = 'text/plain'
        
        response = jsonify({
            'content': content,
            'mimetype': mimetype,
            'filename': f'summary_{int(time.time())}.{format_type}'
        })
        return response
        
    except Exception as e:
        logger.error(f"Export error: {e}")
        response = jsonify({'error': f'Export failed: {str(e)}'})
        return response, 500

@app.errorhandler(500)
def internal_error(e):
    """Handle internal server errors"""
    logger.error(f"Internal server error: {e}")
    response = jsonify({'error': 'Internal server error. Please try again later.'})
    return response, 500

if __name__ == '__main__':
    logger.info("Starting Summify Text-Only Server v3.0...")
    # Remove all print statements for cleaner console output
    try:
        app.run(debug=True, port=5000, host='0.0.0.0')
    except Exception as e:
        logger.error(f"Server startup failed: {e}")
    print(f"Frontend URL: http://127.0.0.1:5500")
    print(f"Status endpoint: http://localhost:5000/api/status")
    print("=" * 50)
    
    if not nltk:
        logger.warning("NLTK not available - using basic text processing fallbacks")
        logger.info("Install NLTK for enhanced text processing: pip install nltk")
        print("⚠️  NLTK not installed - using basic text processing")
    else:
        logger.info("NLTK available - using advanced text processing")
        print("✅ NLTK available - advanced text processing enabled")
    
    print("\n🚀 Starting Flask server...")
    print("📝 Open your HTML file in a browser to use the app")
    print("🔧 If you see CORS errors, make sure both files are in the same directory")
    print("\n" + "=" * 50)
    
    try:
        app.run(debug=True, port=5000, host='0.0.0.0')
    except Exception as e:
        print(f"❌ Failed to start server: {e}")
        print("💡 Try running: python app.py")
        logger.error(f"Server startup failed: {e}")
