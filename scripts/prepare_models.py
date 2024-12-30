import os
import subprocess
from pathlib import Path
import requests
from tqdm import tqdm

MODELS = {
    'codellama-7b': {
        'url': 'https://huggingface.co/codellama/CodeLlama-7b-Instruct-hf/resolve/main/model.safetensors',
        'output': 'models/codellama-7b-quantized.tflite'
    },
    'stable-llm': {
        'url': 'https://huggingface.co/stabilityai/stable-code-3b/resolve/main/model.safetensors',
        'output': 'models/stable-llm-2b.tflite'
    }
}

def download_file(url: str, output: str):
    """Download file with progress bar"""
    response = requests.get(url, stream=True)
    total_size = int(response.headers.get('content-length', 0))
    
    os.makedirs(os.path.dirname(output), exist_ok=True)
    
    with open(output, 'wb') as f, tqdm(
        desc=os.path.basename(output),
        total=total_size,
        unit='iB',
        unit_scale=True
    ) as pbar:
        for data in response.iter_content(chunk_size=1024):
            size = f.write(data)
            pbar.update(size)

def quantize_model(input_path: str, output_path: str):
    """Quantize model for EdgeTPU"""
    try:
        subprocess.run([
            'edgetpu_compiler',
            '--input_model', input_path,
            '--output_model', output_path,
            '--quantization_steps', '256'
        ], check=True)
    except subprocess.CalledProcessError as e:
        print(f"Error quantizing model: {e}")
        raise

def main():
    print("Preparing models for deployment...")
    
    for model_name, model_info in MODELS.items():
        print(f"\nProcessing {model_name}...")
        
        # Download model if not exists
        if not os.path.exists(model_info['output']):
            temp_path = f"models/temp_{model_name}.safetensors"
            download_file(model_info['url'], temp_path)
            
            # Convert and quantize
            print(f"Quantizing {model_name}...")
            quantize_model(temp_path, model_info['output'])
            
            # Cleanup
            os.remove(temp_path)
            
        print(f"{model_name} ready!")

if __name__ == '__main__':
    main() 