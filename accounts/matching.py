"""
Face Matching Algorithm with improved accuracy and confidence scoring.
Implements proper threshold and best-match handling.
"""

import logging
import numpy as np
from scipy.spatial.distance import cosine
from .face_utils import deserialize_embedding, get_confidence_level, compare_faces, extract_embedding

logger = logging.getLogger(__name__)

CONFIDENCE_THRESHOLD = 0.45
HIGH_CONFIDENCE_THRESHOLD = 0.75
MEDIUM_CONFIDENCE_THRESHOLD = 0.55


def find_top_matches(source_embedding, queryset, top_k=5, threshold=None):
    """
    Find top matching faces in a queryset.

    Always returns the top results, even if similarity is low.
    This allows the UI to show possible matches instead of an empty list.
    """
    if threshold is None:
        threshold = CONFIDENCE_THRESHOLD

    if source_embedding is None:
        logger.warning("Source embedding is missing. Returning possible matches with low confidence.")

    results = []

    for obj in queryset:
        if not obj.face_embedding:
            continue

        try:
            target_embedding = deserialize_embedding(obj.face_embedding)
            if target_embedding is None:
                continue

            similarity_score = compare_faces(source_embedding, target_embedding)
            confidence_info = get_confidence_level(similarity_score)

            logger.debug(
                "Comparing: %s | Score: %.4f",
                getattr(obj, 'name', getattr(obj, 'id', 'unknown')),
                similarity_score,
            )

            results.append((similarity_score, obj, confidence_info))
        except Exception as e:
            logger.warning(
                "Error comparing faces for object %s: %s",
                getattr(obj, 'id', 'unknown'),
                str(e),
            )
            continue

    results.sort(key=lambda x: x[0], reverse=True)

    if threshold is not None:
        qualified = [item for item in results if item[0] >= threshold]
        if qualified:
            return qualified[:top_k]

    return results[:top_k]


def find_best_match(source_embedding, queryset, threshold=None):
    """
    Find the single best matching face from a queryset.

    Returns the top result even if the score is low.
    """
    matches = find_top_matches(source_embedding, queryset, top_k=1, threshold=threshold)

    if matches:
        similarity_score, matched_obj, confidence_info = matches[0]
        return {
            'found': True,
            'match': matched_obj,
            'similarity': float(similarity_score),
            'confidence': confidence_info,
            'message': f"Best match found with {confidence_info['level']} confidence",
        }

    return {
        'found': False,
        'match': None,
        'similarity': 0.0,
        'confidence': {
            'level': 'LOW',
            'percentage': 0,
            'description': 'No matches available',
        },
        'message': 'No matching face found in database',
    }


def find_best_match_from_image(uploaded_image_path, queryset, threshold=None):
    """
    Extract embedding from an uploaded image path and return the best match.

    This helper ensures the matching pipeline can work directly from an image file.
    """
    embedding = extract_embedding(uploaded_image_path)
    return find_best_match(embedding, queryset, threshold=threshold)


def batch_compare_faces(source_embedding, target_embeddings):
    source_embedding = np.asarray(source_embedding, dtype="float32")
    similarity_scores = []
    for target in target_embeddings:
        target = np.asarray(target, dtype="float32")
        score = 1 - cosine(source_embedding, target)
        similarity_scores.append(score)
    return np.array(similarity_scores)


def _ensure_array(vec):
    if vec is None:
        return None
    if isinstance(vec, (bytes, memoryview)):
        return deserialize_embedding(vec)
    return np.asarray(vec, dtype="float32")
