"""
Face Recognition Utilities using DeepFace.
Improved for better matching behavior, debug support, and caching.
"""

import logging
import os
import pickle
import warnings
from functools import lru_cache

import cv2
import numpy as np

try:
    from deepface import DeepFace
    _DEEPFACE_AVAILABLE = True
except Exception:
    DeepFace = None
    _DEEPFACE_AVAILABLE = False

logger = logging.getLogger(__name__)


FACE_MODEL = "Facenet"
DETECTOR_BACKEND = "mtcnn"
MIN_CONFIDENCE_SCORE = 0.45
MAX_RESPONSE_TIME = 3.0


def _validate_image_quality(image_path):
    if not os.path.exists(image_path):
        return False, "Image file does not exist"

    file_size = os.path.getsize(image_path) / 1024
    if file_size < 10:
        return False, "Image is very small (< 10KB). Please upload a higher quality image."

    try:
        img = cv2.imread(image_path)
        if img is None:
            return False, "Could not read image. Please ensure it's a valid image format."

        height, width = img.shape[:2]
        if height < 80 or width < 80:
            return False, f"Image is too small ({width}x{height}). Minimum recommended: 80x80 pixels."

        return True, None
    except Exception as e:
        return False, f"Image validation failed: {str(e)}"


@lru_cache(maxsize=256)
def _cached_represent(image_path):
    return DeepFace.represent(
        img_path=image_path,
        model_name=FACE_MODEL,
        detector_backend=DETECTOR_BACKEND,
        enforce_detection=False,
    )


def extract_embedding(image_path):
    if not _DEEPFACE_AVAILABLE:
        warnings.warn("DeepFace is not available. Cannot extract embeddings.")
        return None

    is_valid, error_msg = _validate_image_quality(image_path)
    if not is_valid:
        warnings.warn(f"Image validation failed: {error_msg}")
        return None

    abs_path = os.path.abspath(image_path)

    try:
        result = _cached_represent(abs_path)
        if not result:
            logger.warning("DeepFace returned no embedding result for image: %s", abs_path)
            return None

        if isinstance(result, dict):
            result = [result]

        if isinstance(result, list) and len(result) > 1:
            logger.warning(
                "Multiple faces detected (%d). Using first face embedding for image: %s",
                len(result),
                abs_path,
            )

        embedding_data = result[0].get("embedding") if result and isinstance(result[0], dict) else None
        if embedding_data is None:
            logger.warning("DeepFace result did not contain embedding data for image: %s", abs_path)
            return None

        embedding = np.asarray(embedding_data, dtype="float32")
        return embedding
    except Exception as e:
        logger.warning("Embedding extraction failed for image %s: %s", abs_path, str(e))
        return None


def compare_faces(embedding1, embedding2):
    from scipy.spatial.distance import cosine

    try:
        if isinstance(embedding1, (bytes, memoryview)):
            embedding1 = deserialize_embedding(embedding1)
        if isinstance(embedding2, (bytes, memoryview)):
            embedding2 = deserialize_embedding(embedding2)

        if embedding1 is None or embedding2 is None:
            return 0.0

        embedding1 = np.asarray(embedding1, dtype="float32")
        embedding2 = np.asarray(embedding2, dtype="float32")

        if embedding1.size == 0 or embedding2.size == 0:
            return 0.0

        norm1 = np.linalg.norm(embedding1)
        norm2 = np.linalg.norm(embedding2)
        if norm1 == 0 or norm2 == 0:
            return 0.0

        score = 1.0 - cosine(embedding1, embedding2)
        if np.isnan(score):
            return 0.0

        return float(score)
    except Exception as e:
        logger.warning("Face comparison failed: %s", str(e))
        return 0.0


def get_confidence_level(similarity_score):
    if similarity_score >= 0.75:
        return {
            "level": "HIGH",
            "percentage": int(similarity_score * 100),
            "description": "Very likely the same person",
        }
    elif similarity_score >= 0.55:
        return {
            "level": "MEDIUM",
            "percentage": int(similarity_score * 100),
            "description": "Possible match, please verify",
        }
    elif similarity_score >= 0.45:
        return {
            "level": "LOW",
            "percentage": int(similarity_score * 100),
            "description": "Weak match, review manually",
        }
    else:
        return {
            "level": "LOW",
            "percentage": int(similarity_score * 100),
            "description": "Very weak match, likely not the same person",
        }


def serialize_embedding(embedding):
    if embedding is None:
        return None
    if isinstance(embedding, np.ndarray):
        return pickle.dumps(embedding)
    return pickle.dumps(np.array(embedding))


def deserialize_embedding(binary):
    if binary is None:
        return None
    if isinstance(binary, memoryview):
        binary = binary.tobytes()
    return pickle.loads(binary)
