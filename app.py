from flask import Flask, request, send_file, render_template, jsonify
import json
import tempfile
import os
from werkzeug.utils import secure_filename

# Import your existing engine
from sticker_engine import generate_pdf_job

app = Flask(__name__)

@app.route('/')
def index():
    # Serves the frontend interface
    return render_template('index.html')

@app.route('/generate', methods=['POST'])
def generate():
    try:
        # 1. Parse Form Data
        settings_str = request.form.get('settings')
        cfg = json.loads(settings_str)

        # Cast all incoming settings to strict numbers
        for name in cfg:
            cfg[name]['qty'] = int(cfg[name].get('qty', 1))
            cfg[name]['diameterCm'] = float(cfg[name].get('diameterCm', 0))
            cfg[name]['widthCm'] = float(cfg[name].get('widthCm', 0))
            cfg[name]['heightCm'] = float(cfg[name].get('heightCm', 0))

        paper = request.form.get('paper', '12x18')
        custom_w_cm = request.form.get('custom_w_cm')
        custom_h_cm = request.form.get('custom_h_cm')
        
        fill_enabled = request.form.get('fill_enabled') == 'true'
        fill_source = request.form.get('fill_source', 'last')
        fill_selected_name = request.form.get('fill_selected_name', '')
        registration_marks = request.form.get('registration_marks') == 'true'

        custom_w_cm = float(custom_w_cm) if custom_w_cm and custom_w_cm not in ['null', 'undefined'] else None
        custom_h_cm = float(custom_h_cm) if custom_h_cm and custom_h_cm not in ['null', 'undefined'] else None

        # 2. Handle Uploaded Images
        uploaded_files = request.files.getlist('images')
        tmpdir = tempfile.mkdtemp()
        input_images = []

        for img in uploaded_files:
            if img.filename:
                # Save the file to disk using a safe name
                safe_filename = secure_filename(img.filename)
                path = os.path.join(tmpdir, safe_filename)
                img.save(path)
                
                # CRITICAL FIX: Pass the ORIGINAL filename to the engine 
                # so it matches the keys in the settings dictionary sent from the frontend
                input_images.append((img.filename, path))

        if not input_images:
            return jsonify({"error": "No valid images uploaded"}), 400

        # 3. Generate PDF
        pdf_path = generate_pdf_job(
            input_images=input_images,
            per_image_settings=cfg,
            paper=paper,
            custom_w_cm=custom_w_cm,
            custom_h_cm=custom_h_cm,
            fill_enabled=fill_enabled,
            fill_source=fill_source,
            fill_selected_name=fill_selected_name,
            registration_marks=registration_marks
        )

        # 4. Return the file
        return send_file(
            pdf_path,
            mimetype='application/pdf',
            as_attachment=True,
            download_name='memento_world_sticker.pdf'
        )

    except Exception as e:
        print(f"!!! SERVER ERROR: {str(e)}") 
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    # Run the app locally on port 8000
    app.run(debug=True, port=8000)