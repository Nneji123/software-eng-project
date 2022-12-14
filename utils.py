import sys
from pathlib import Path

import os

import bcrypt
import cv2
import numpy as np
import onnxruntime as ort
from PIL import Image

_sess_options = ort.SessionOptions()
_sess_options.intra_op_num_threads = os.cpu_count()
MODEL_SESS = ort.InferenceSession(
    "model.onnx", _sess_options, providers=["CPUExecutionProvider"]
)
# import sys
# os.chdir(sys._MEIPASS)
# os.system('included\\model.onnx')
# os.system('included\\logo.ico')



def preprocess_image(image: Image) -> np.ndarray:
    image = np.array(image)
    image = cv2.cvtColor(image, cv2.COLOR_RGB2BGR)

    h, w, c = np.shape(image)
    if min(h, w) > 720:
        if h > w:
            h, w = int(720 * h / w), 720
        else:
            h, w = 720, int(720 * w / h)
    image = cv2.resize(image, (w, h), interpolation=cv2.INTER_AREA)
    h, w = (h // 8) * 8, (w // 8) * 8
    image = image[:h, :w, :]
    image = image.astype(np.float32) / 127.5 - 1
    return np.expand_dims(image, axis=0)


def inference(image: np.ndarray) -> Image:
    image = preprocess_image(image)
    results = MODEL_SESS.run(None, {"input_photo:0": image})
    output = (np.squeeze(results[0]) + 1.0) * 127.5
    output = np.clip(output, 0, 255).astype(np.uint8)
    cv2.imwrite("static/output.png", output)
    return "Output Saved!"

salt = bcrypt.gensalt()

def hash_password(password: str) -> str:
    if password is not None:
        try:
            hashed = bcrypt.hashpw(str(password).encode("utf-8"), salt)
            return hashed.decode("utf-8")
        except Exception as e:
            print(e)
    else:
        return "Invalid Password entered"

def check_password_hashed(password: str) -> str:
    if password is not None:
        try:
            if bcrypt.checkpw(password, salt):
                return True
            else: 
                return False
        except Exception as e:
            print(e)