from flask import Flask, render_template, jsonify, request
import sqlite3
import json
import os
import config
from database_schema import get_connection

app = Flask(__name__)


@app.route('/')
def index():
    """Render the main page"""
    return render_template('index.html')


@app.route('/api/steels', methods=['GET'])
def get_steels():
    """Get steel grades with optional filtering"""
    # Check if database exists
    if not os.path.exists(config.DB_FILE):
        return jsonify({'error': 'Database not found. Please run parser.py first.'}), 500
    
    # Get filter parameters
    grade_filter = request.args.get('grade', '').strip()
    exact_search = request.args.get('exact', 'false').lower() == 'true'
    base_filter = request.args.get('base', '').strip()
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
        
        return jsonify(results)
    except Exception as e:
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
        
        # techs removed - no longer used
        
        return jsonify({
            'total': total,
            'bases': bases
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        conn.close()


if __name__ == '__main__':
    import os
    port = int(os.environ.get('FLASK_PORT', 5000))
    app.run(host='0.0.0.0', debug=True, port=port)

