from flask import Flask, request, jsonify, send_file
from minio import Minio
from minio.error import S3Error
import os
import tempfile
import zipfile

app = Flask(__name__)

minio_client = Minio(
        '127.0.0.1:9005',
        access_key=os.getenv('MINIO_ROOT_USER'),
        secret_key=os.getenv('MINIO_ROOT_PASSWORD'),
        secure=False
)

def bucket_exists(bucketName):
    # loading All Bucket
    buckets = minio_client.list_buckets()

    # already exist bucket -> return True
    for bucket in buckets:
        if bucket.name == bucketName:
            return True
    return False

def create_bucket(bucketName):
    #create bucket
    minio_client.make_bucket(bucketName)
    print(f"Bucket '{bucket_name}' created successfully")

def saveFile(bucketName, fileName, file):
    _, temp_file_path = tempfile.mkstemp()
    file.save(temp_file_path)

    minio_client.fput_object(bucketName, fileName, temp_file_path)

    os.remove(temp_file_path)    

@app.route('/upload', methods=['POST'])
def upload_file():
    # file, bucket loading
    file = request.files.get('file')
    bucket_name = request.form.get('bucket')
    file_name = file.filename

    # If not exist bucket -> create bucket
    if(bucket_exists(bucket_name)==False):
        create_bucket(bucket_name)

    if not file:
        return jsonify({"error": "No file provided"}), 400
    if not bucket_name:
        return jsonify({"error": "No bucket provided"}), 400

    try:
        saveFile(bucket_name, file_name, file)
        return jsonify({"message": "File uploaded successfully"}), 200

    except S3Error as e:
        return jsonify({"error": str(e)}), 500

def get_bucket_files(bucketName):
    objects = minio_client.list_objects(bucketName, recursive=True)
    files = [obj.object_name for obj in objects]
    return files

@app.route('/download/<name>', methods=['get'])
def download_dataset(name):
    files = get_bucket_files(name)

    with tempfile.TemporaryDirectory() as temp_dir:
        zip_file_name = name+".zip"
        zip_file_path = os.path.join(temp_dir, zip_file_name)
        with zipfile.ZipFile(zip_file_path, 'w') as zipf:
            for file in files:
                temp_file_path = os.path.join(temp_dir, file)
                minio_client.fget_object(name, file, temp_file_path)
                zipf.write(temp_file_path, file)

        return send_file(zip_file_path, as_attachment=True)
 

if __name__ == '__main__':
    app.run(debug=True, port=5002, host='0.0.0.0')
