from fastapi import APIRouter, WebSocket, WebSocketDisconnect
import numpy as np
import json
import os
import io
import tensorflow as tf
from tensorflow.keras import layers, models
from google.cloud import storage

router = APIRouter(tags=["predict"])

# 로컬 캐시 경로
TMP_MODEL_PATH = 'C:/sign-language-api/transformer_DFU_batch32.h5' if os.name == 'nt' else '/tmp/transformer_DFU_batch32.h5'
TMP_MEAN_PATH  = 'C:/sign-language-api/X_mean_DFU_batch32.npy' if os.name == 'nt' else '/tmp/X_mean_DFU_batch32.npy'
TMP_STD_PATH   = 'C:/sign-language-api/X_std_DFU_batch32.npy' if os.name == 'nt' else '/tmp/X_std_DFU_batch32.npy'
TMP_LABEL_PATH = 'C:/sign-language-api/label_map.json' if os.name == 'nt' else '/tmp/label_map.json'

# GCS 설정
gcs_client = storage.Client()
bucket = gcs_client.bucket('sign-language-data-2026')

def load_npy_from_gcs(blob_name):
    buf = io.BytesIO(bucket.blob(blob_name).download_as_bytes())
    return np.load(buf)

# TransformerBlock 정의
class TransformerBlock(layers.Layer):
    def __init__(self, embed_dim, num_heads, ff_dim, dropout=0.1):
        super().__init__()
        self.att = layers.MultiHeadAttention(num_heads=num_heads, key_dim=embed_dim // num_heads)
        self.ffn = models.Sequential([
            layers.Dense(ff_dim, activation='relu'),
            layers.Dense(embed_dim)
        ])
        self.norm1 = layers.LayerNormalization(epsilon=1e-6)
        self.norm2 = layers.LayerNormalization(epsilon=1e-6)
        self.drop1 = layers.Dropout(dropout)
        self.drop2 = layers.Dropout(dropout)

    def call(self, x, training=False):
        attn = self.att(x, x)
        x = self.norm1(x + self.drop1(attn, training=training))
        ffn = self.ffn(x)
        x = self.norm2(x + self.drop2(ffn, training=training))
        return x

def positional_encoding(length, depth):
    positions = tf.range(length, dtype=tf.float32)[:, tf.newaxis]
    dims = tf.range(depth, dtype=tf.float32)[tf.newaxis, :]
    angles = positions / tf.pow(10000.0, (2 * (dims // 2)) / tf.cast(depth, tf.float32))
    angles = tf.concat([tf.sin(angles[:, 0::2]), tf.cos(angles[:, 1::2])], axis=-1)
    return angles[tf.newaxis, :, :]

def build_model():
    inputs = layers.Input(shape=(30, 274))
    x = layers.Dense(128)(inputs)
    x = x + positional_encoding(30, 128)
    for _ in range(3):
        x = TransformerBlock(128, 4, 256, 0.1)(x)
    x = layers.GlobalAveragePooling1D()(x)
    x = layers.Dropout(0.1)(x)
    x = layers.Dense(256, activation='relu')(x)
    x = layers.Dropout(0.1)(x)
    outputs = layers.Dense(3000, activation='softmax')(x)
    return models.Model(inputs, outputs)

# 모델 로드 (서버 시작 시 1회)
print("AI 모델 로딩 중...")
ai_model = build_model()

# 모델 가중치
if os.path.exists(TMP_MODEL_PATH):
    print("모델 로컬에서 로드!")
    ai_model.load_weights(TMP_MODEL_PATH)
else:
    print("모델 GCS에서 다운로드...")
    bucket.blob('models/transformer_DFU_batch32.h5').download_to_filename(TMP_MODEL_PATH)
    ai_model.load_weights(TMP_MODEL_PATH)

# X_mean
if os.path.exists(TMP_MEAN_PATH):
    print("X_mean 로컬에서 로드!")
    X_mean = np.load(TMP_MEAN_PATH)
else:
    print("X_mean GCS에서 다운로드...")
    X_mean = load_npy_from_gcs('models/X_mean_DFU_batch32.npy')
    np.save(TMP_MEAN_PATH, X_mean)

# X_std
if os.path.exists(TMP_STD_PATH):
    print("X_std 로컬에서 로드!")
    X_std = np.load(TMP_STD_PATH)
else:
    print("X_std GCS에서 다운로드...")
    X_std = load_npy_from_gcs('models/X_std_DFU_batch32.npy')
    np.save(TMP_STD_PATH, X_std)

# label_map
if os.path.exists(TMP_LABEL_PATH):
    print("label_map 로컬에서 로드!")
    with open(TMP_LABEL_PATH, 'r', encoding='utf-8') as f:
        label_map = json.load(f)
else:
    print("label_map GCS에서 다운로드...")
    label_map = json.loads(bucket.blob('processed/label_map.json').download_as_text())
    with open(TMP_LABEL_PATH, 'w', encoding='utf-8') as f:
        json.dump(label_map, f, ensure_ascii=False)

print("AI 모델 로딩 완료! (Top-1 91.3%)")

def predict_word(keypoints_sequence):
    kp = keypoints_sequence.copy()

    # 왼손 구간 (0~41): 전부 0이면 X_mean으로 대체
    for frame_idx in range(30):
        if np.all(kp[frame_idx, 0:42] == 0.0):
            kp[frame_idx, 0:42] = X_mean[0, 0, 0:42]

    # 오른손 구간 (42~83): 전부 0이면 X_mean으로 대체
    for frame_idx in range(30):
        if np.all(kp[frame_idx, 42:84] == 0.0):
            kp[frame_idx, 42:84] = X_mean[0, 0, 42:84]

    # 얼굴 구간 (84~223): 전부 0일 때만 X_mean으로 대체
    for frame_idx in range(30):
        if np.all(kp[frame_idx, 84:224] == 0.0):
            kp[frame_idx, 84:224] = X_mean[0, 0, 84:224]

    print(f"[입력값] x범위: {kp[:, 0::2].min():.1f} ~ {kp[:, 0::2].max():.1f}")
    print(f"[입력값] y범위: {kp[:, 1::2].min():.1f} ~ {kp[:, 1::2].max():.1f}")

    x = (kp - X_mean[0]) / (X_std[0] + 1e-8)
    x = x[np.newaxis, ...]
    probs = ai_model.predict(x, verbose=0)[0]
    top_idx = probs.argsort()[-3:][::-1]

    results = [(label_map[str(i + 1)], float(probs[i])) for i in top_idx]
    print(f"[예측 결과] {[(w, round(c, 3)) for w, c in results]}")
    return results

# WebSocket 엔드포인트
@router.websocket("/ws/predict")
async def websocket_predict(websocket: WebSocket):
    await websocket.accept(subprotocol='ngrok-skip-browser-warning')
    try:
        while True:
            data = await websocket.receive_json()
            keypoints = np.array(data["keypoints"])  # (30, 274)

            print(f"[받은 데이터] shape: {keypoints.shape}")

            results = predict_word(keypoints)
            word, confidence = results[0]

            if confidence < 0.5:
                await websocket.send_json({
                    "word": "인식 불가",
                    "confidence": 0.0,
                    "top3": []
                })
            else:
                await websocket.send_json({
                    "word": word,
                    "confidence": confidence,
                    "top3": [{"word": w, "confidence": c} for w, c in results]
                })
    except WebSocketDisconnect:
        print("클라이언트 연결 종료")
    except Exception as e:
        print(f"[에러 발생] {type(e).__name__}: {e}")
        await websocket.close()