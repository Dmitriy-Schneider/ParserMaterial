from flask import Flask, render_template, jsonify, request
import sqlite3
import json
import os
from dotenv import load_dotenv
import config
from database_schema import get_connection
from ai_search import get_ai_search

# Load environment variables
load_dotenv()

app = Flask(__name__)

# Initialize AI search
ai_search = get_ai_search()


@app.route('/')
def index():
    """Render the main page"""
    return render_template('index.html')


@app.route('/api/steels', methods=['GET'])
def get_steels():
    """Get steel grades with optional filtering and AI fallback"""
    # Check if database exists
    if not os.path.exists(config.DB_FILE):
        return jsonify({'error': 'Database not found. Please run parser.py first.'}), 500

    # Get filter parameters
    grade_filter = request.args.get('grade', '').strip()
    exact_search = request.args.get('exact', 'false').lower() == 'true'
    base_filter = request.args.get('base', '').strip()

    # AI Search enabled ONLY for explicit request from Telegram Bot
    # Web Exact Search (🔍) searches ONLY in database (exact match, no AI fallback)
    use_ai = request.args.get('ai', 'false').lower() == 'true'
    # tech_filter removed - no longer used
    
    # Element filters
    element_filters = {}
    elements = ['c', 'cr', 'mo', 'v', 'w', 'co', 'ni', 'mn', 'si', 's', 'p', 'cu', 'nb', 'n']
    
    for element in elements:
        min_val = request.args.get(f'{element}_min', '').strip()
        max_val = request.args.get(f'{element}_max', '').strip()
        if min_val or max_val:
            element_filters[element] = {
                'min': min_val if min_val else None,
                'max': max_val if max_val else None
            }
    
    # Build query
    query = "SELECT * FROM steel_grades WHERE 1=1"
    params = []
    
    if grade_filter:
        if exact_search:
            query += " AND grade = ?"
            params.append(grade_filter)
        else:
            query += " AND grade LIKE ?"
            params.append(f'%{grade_filter}%')
    
    if base_filter:
        query += " AND base = ?"
        params.append(base_filter)
    
    # tech_filter removed - no longer used
    
    # Apply element filters with proper range handling
    for element, values in element_filters.items():
        if values['min'] or values['max']:
            # Create a subquery that handles ranges properly
            range_conditions = []
            range_params = []
            
            if values['min']:
                min_val = float(values['min'])
                # Check if the stored value (which might be a range like "3.75-4.50") 
                # has any part >= min_val
                range_conditions.append(f"""
                    ({element} IS NOT NULL AND {element} != '' AND {element} != '0.00' AND
                     (CAST({element} AS REAL) >= ? OR 
                      {element} LIKE '%-%' AND CAST(SUBSTR({element}, 1, INSTR({element}, '-') - 1) AS REAL) >= ? OR
                      {element} LIKE '%-%' AND CAST(SUBSTR({element}, INSTR({element}, '-') + 1) AS REAL) >= ?))
                """)
                range_params.extend([min_val, min_val, min_val])
            
            if values['max']:
                max_val = float(values['max'])
                # Check if the stored value has any part <= max_val
                range_conditions.append(f"""
                    ({element} IS NOT NULL AND {element} != '' AND {element} != '0.00' AND
                     (CAST({element} AS REAL) <= ? OR 
                      {element} LIKE '%-%' AND CAST(SUBSTR({element}, 1, INSTR({element}, '-') - 1) AS REAL) <= ? OR
                      {element} LIKE '%-%' AND CAST(SUBSTR({element}, INSTR({element}, '-') + 1) AS REAL) <= ?))
                """)
                range_params.extend([max_val, max_val, max_val])
            
            if range_conditions:
                query += f" AND ({' AND '.join(range_conditions)})"
                params.extend(range_params)
    
    query += " ORDER BY grade"  # Remove LIMIT to show all results
    
    conn = get_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute(query, params)
        columns = [description[0] for description in cursor.description]
        rows = cursor.fetchall()

        results = []
        for row in rows:
            results.append(dict(zip(columns, row)))

        # If no results and AI is enabled, try AI search
        if len(results) == 0 and grade_filter and use_ai and ai_search.enabled:
            ai_result = ai_search.search_steel(grade_filter)
            if ai_result:
                # Format AI result to match database schema
                ai_result['id'] = 'AI'
                # Keep the link field from AI result (don't override)
                if 'link' not in ai_result:
                    ai_result['link'] = None
                results = [ai_result]

        return jsonify(results)
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        conn.close()


@app.route('/api/steels/ai-search', methods=['GET', 'POST'])
def ai_search_endpoint():
    """Direct AI search endpoint for steel grades"""
    if not ai_search.enabled:
        return jsonify({
            'error': 'AI search is not enabled. Please set OPENAI_API_KEY in .env file'
        }), 503

    # Get grade name from query parameter or JSON body
    if request.method == 'GET':
        grade_name = request.args.get('grade', '').strip()
    else:
        data = request.get_json() or {}
        grade_name = data.get('grade', '').strip()

    if not grade_name:
        return jsonify({'error': 'Grade name is required'}), 400

    try:
        result = ai_search.search_steel(grade_name)

        if result:
            return jsonify({
                'success': True,
                'grade': grade_name,
                'data': result,
                'source': 'ai',
                'cached': result.get('cached', False)
            })
        else:
            return jsonify({
                'success': False,
                'grade': grade_name,
                'message': 'Steel grade not found by AI',
                'source': 'ai'
            }), 404

    except Exception as e:
        return jsonify({
            'error': f'AI search failed: {str(e)}'
        }), 500


@app.route('/api/steels/add', methods=['POST'])
def add_steel():
    """Add AI search result to main database"""
    data = request.get_json() or {}

    if not data.get('grade'):
        return jsonify({'error': 'Grade is required'}), 400

    conn = get_connection()
    cursor = conn.cursor()

    try:
        # Check if already exists
        cursor.execute("SELECT id FROM steel_grades WHERE grade = ?", (data['grade'],))
        if cursor.fetchone():
            return jsonify({'error': 'Grade already exists in database'}), 409

        # Insert new record
        cursor.execute("""
            INSERT INTO steel_grades (
                grade, base, c, cr, mo, v, w, co, ni, mn, si, s, p, cu, nb, n,
                tech, standard, manufacturer, analogues, link
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            data.get('grade'),
            data.get('base', 'Fe'),
            data.get('c'),
            data.get('cr'),
            data.get('mo'),
            data.get('v'),
            data.get('w'),
            data.get('co'),
            data.get('ni'),
            data.get('mn'),
            data.get('si'),
            data.get('s'),
            data.get('p'),
            data.get('cu'),
            data.get('nb'),
            data.get('n'),
            data.get('application') or data.get('tech'),
            data.get('standard'),
            data.get('manufacturer'),
            data.get('analogues'),
            data.get('link') or data.get('source_url') or data.get('pdf_url')
        ))

        conn.commit()

        return jsonify({
            'success': True,
            'message': f'Grade {data["grade"]} added to database',
            'id': cursor.lastrowid
        })

    except Exception as e:
        conn.rollback()
        return jsonify({'error': str(e)}), 500
    finally:
        conn.close()


@app.route('/api/steels/delete', methods=['POST'])
def delete_steel():
    """Delete steel grade from database"""
    data = request.get_json() or {}

    if not data.get('grade'):
        return jsonify({'error': 'Grade is required'}), 400

    conn = get_connection()
    cursor = conn.cursor()

    try:
        # Check if exists
        cursor.execute("SELECT id FROM steel_grades WHERE grade = ?", (data['grade'],))
        row = cursor.fetchone()

        if not row:
            return jsonify({'error': 'Grade not found in database'}), 404

        # Delete
        cursor.execute("DELETE FROM steel_grades WHERE grade = ?", (data['grade'],))
        conn.commit()

        return jsonify({
            'success': True,
            'message': f'Grade {data["grade"]} deleted from database'
        })

    except Exception as e:
        conn.rollback()
        return jsonify({'error': str(e)}), 500
    finally:
        conn.close()


@app.route('/api/stats', methods=['GET'])
def get_stats():
    """Get statistics about the database"""
    if not os.path.exists(config.DB_FILE):
        return jsonify({'error': 'Database not found. Please run parser.py first.'}), 500

    conn = get_connection()
    cursor = conn.cursor()

    try:
        cursor.execute("SELECT COUNT(*) FROM steel_grades")
        total = cursor.fetchone()[0]

        # Get unique values for dropdowns
        cursor.execute("SELECT DISTINCT base FROM steel_grades WHERE base IS NOT NULL")
        bases = [row[0] for row in cursor.fetchall()]

        # Check AI cache stats
        ai_cached = 0
        try:
            cursor.execute("SELECT COUNT(*) FROM ai_searches")
            ai_cached = cursor.fetchone()[0]
        except:
            pass

        # techs removed - no longer used

        return jsonify({
            'total': total,
            'bases': bases,
            'ai_enabled': ai_search.enabled,
            'ai_cached_searches': ai_cached
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        conn.close()


if __name__ == '__main__':
    import os
    port = int(os.environ.get('FLASK_PORT', 5000))
    app.run(host='0.0.0.0', debug=True, port=port)

