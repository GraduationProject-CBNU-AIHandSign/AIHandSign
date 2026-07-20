import cv2
import mediapipe as mp
import numpy as np
import json
import tensorflow as tf
from tensorflow.keras import layers, models
from collections import deque
from PIL import ImageFont, ImageDraw, Image

def positional_encoding(length, depth):
    positions = tf.range(length, dtype=tf.float32)[:, tf.newaxis]
    dims = tf.range(depth, dtype=tf.float32)[tf.newaxis, :]
    angles = positions / tf.pow(10000.0, (2 * (dims // 2)) / tf.cast(depth, tf.float32))
    angles = tf.concat([tf.sin(angles[:, 0::2]), tf.cos(angles[:, 1::2])], axis=-1)
    return angles[tf.newaxis, :, :]

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

def build_transformer_model(input_shape=(30, 274), num_classes=3000,
                             embed_dim=128, num_heads=4, ff_dim=256,
                             num_blocks=3, dropout=0.1):
    inputs = layers.Input(shape=input_shape)
    x = layers.Dense(embed_dim)(inputs)
    pos_enc = positional_encoding(input_shape[0], embed_dim)
    x = x + pos_enc
    for _ in range(num_blocks):
        x = TransformerBlock(embed_dim, num_heads, ff_dim, dropout)(x)
    x = layers.GlobalAveragePooling1D()(x)
    x = layers.Dropout(dropout)(x)
    x = layers.Dense(256, activation='relu')(x)
    x = layers.Dropout(dropout)(x)
    outputs = layers.Dense(num_classes, activation='softmax')(x)
    return models.Model(inputs, outputs)

print("모델 로딩 중...")
model = build_transformer_model()
model.load_weights('C:/sign-language-api/model_weights.weights.h5')
X_mean = np.load('C:/sign-language-api/X_mean.npy')
X_std = np.load('C:/sign-language-api/X_std.npy')
with open('C:/sign-language-api/label_map.json', 'r', encoding='utf-8') as f:
    label_map = json.load(f)
print("모델 로딩 완료!")

mp_hands = mp.solutions.hands
mp_face = mp.solutions.face_mesh
mp_pose = mp.solutions.pose

hands = mp_hands.Hands(max_num_hands=2, min_detection_confidence=0.5)
face = mp_face.FaceMesh(max_num_faces=1, min_detection_confidence=0.5)
pose = mp_pose.Pose(min_detection_confidence=0.5)

buffer = deque(maxlen=30)
current_word = ""
confidence = 0.0

def extract_keypoints(results_hands, results_face, results_pose, frame_w=1920, frame_h=1080):
    lh = np.zeros(42)
    rh = np.zeros(42)
    face_kp = np.zeros(140)
    pose_kp = np.zeros(50)

    if results_hands.multi_hand_landmarks:
        for hand_landmarks, handedness in zip(
            results_hands.multi_hand_landmarks,
            results_hands.multi_handedness
        ):
            coords = []
            for lm in hand_landmarks.landmark:
                coords.extend([lm.x * frame_w, lm.y * frame_h])
            if handedness.classification[0].label == 'Left':
                lh = np.array(coords[:42])
            else:
                rh = np.array(coords[:42])

    if results_face.multi_face_landmarks:
        coords = []
        for lm in results_face.multi_face_landmarks[0].landmark[:70]:
            coords.extend([lm.x * frame_w, lm.y * frame_h])
        face_kp = np.array(coords[:140])

    if results_pose.pose_landmarks:
        coords = []
        for lm in list(results_pose.pose_landmarks.landmark)[:25]:
            coords.extend([lm.x * frame_w, lm.y * frame_h])
        pose_kp = np.array(coords[:50])

    return np.concatenate([lh, rh, face_kp, pose_kp])

def predict_word(keypoints_sequence):
    x = (keypoints_sequence - X_mean[0]) / (X_std[0] + 1e-8)
    x = x[np.newaxis, ...]
    probs = model.predict(x, verbose=0)[0]
    top_idx = probs.argsort()[-3:][::-1]
    results = [(label_map[str(i + 1)], float(probs[i])) for i in top_idx]
    return results

def draw_korean(frame, text, pos, size=40, color=(0, 220, 120)):
    img_pil = Image.fromarray(frame)
    draw = ImageDraw.Draw(img_pil)
    try:
        font = ImageFont.truetype("C:/Windows/Fonts/malgun.ttf", size)
    except:
        font = ImageFont.load_default()
    draw.text(pos, text, font=font, fill=color)
    return np.array(img_pil)

cap = cv2.VideoCapture(0)
print("웹캠 시작! 'q' 키로 종료")

while cap.isOpened():
    ret, frame = cap.read()
    if not ret:
        break

    frame = cv2.flip(frame, 1)
    rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

    res_hands = hands.process(rgb)
    res_face = face.process(rgb)
    res_pose = pose.process(rgb)

    # 키포인트 시각화
    if res_hands.multi_hand_landmarks:
        for hand_landmarks in res_hands.multi_hand_landmarks:
            mp.solutions.drawing_utils.draw_landmarks(
                frame, hand_landmarks, mp_hands.HAND_CONNECTIONS,
                mp.solutions.drawing_styles.get_default_hand_landmarks_style(),
                mp.solutions.drawing_styles.get_default_hand_connections_style()
            )

    if res_pose.pose_landmarks:
        mp.solutions.drawing_utils.draw_landmarks(
            frame, res_pose.pose_landmarks, mp_pose.POSE_CONNECTIONS,
            landmark_drawing_spec=mp.solutions.drawing_utils.DrawingSpec(
                color=(0, 255, 255), thickness=2, circle_radius=2),
            connection_drawing_spec=mp.solutions.drawing_utils.DrawingSpec(
                color=(0, 180, 180), thickness=1)
        )

    if res_face.multi_face_landmarks:
        for face_landmarks in res_face.multi_face_landmarks:
            mp.solutions.drawing_utils.draw_landmarks(
                frame, face_landmarks,
                mp_face.FACEMESH_CONTOURS,
                landmark_drawing_spec=mp.solutions.drawing_utils.DrawingSpec(
                    color=(255, 255, 255), thickness=1, circle_radius=1),
                connection_drawing_spec=mp.solutions.drawing_utils.DrawingSpec(
                    color=(200, 200, 200), thickness=1)
            )

    h, w = frame.shape[:2]
    kp = extract_keypoints(res_hands, res_face, res_pose, frame_w=w, frame_h=h)
    buffer.append(kp)

    if len(buffer) == 30:
        seq = np.array(buffer)
        # 손이 감지될 때만 예측
        if res_hands.multi_hand_landmarks:
            results = predict_word(seq)
            current_word = results[0][0]
            confidence = results[0][1]
            top3 = results
        else:
            current_word = ""
            confidence = 0.0
            top3 = []

    cv2.rectangle(frame, (0, 0), (w, 120), (30, 30, 30), -1)

    if confidence >= 0.5:
        color = (0, 220, 120)
        status = "인식됨"
    else:
        color = (100, 100, 100)
        status = "인식 중..."

    frame = draw_korean(frame, current_word, (20, 5), size=45, color=color)
    frame = draw_korean(frame, f"{status} ({confidence:.0%})", (20, 55), size=22, color=color)

    if 'top3' in dir() and top3:
        for i, (word, conf) in enumerate(top3):
            frame = draw_korean(frame, f"{i+1}. {word} ({conf:.0%})", (20, 80 + i*20), size=16, color=(180,180,180))

    bar_w = int((len(buffer) / 30) * (w - 40))
    cv2.rectangle(frame, (20, h - 20), (20 + bar_w, h - 8), (0, 180, 100), -1)
    cv2.putText(frame, f"{len(buffer)}/30", (w - 70, h - 8),
                cv2.FONT_HERSHEY_SIMPLEX, 0.5, (200, 200, 200), 1)

    cv2.imshow('AI hand sign', frame)

    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()