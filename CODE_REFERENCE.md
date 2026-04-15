# Code Reference - New Face Recognition Functions

## Module: `accounts/face_utils.py`

### Configuration Constants
```python
FACE_MODEL = "Facenet"              # Model used for embedding extraction
DETECTOR_BACKEND = "mtcnn"          # Face detection backend
MIN_CONFIDENCE_SCORE = 0.6          # Minimum similarity threshold
MAX_RESPONSE_TIME = 3.0             # Target response time in seconds
```

---

## Function: `extract_embedding(image_path)`

Extracts facial embedding from an image using DeepFace FaceNet model.

**Signature**:
```python
def extract_embedding(image_path: str) -> Optional[np.ndarray]:
    """Extract facial embedding from an image using DeepFace with FaceNet model."""
```

**Parameters**:
- `image_path` (str): Path to the image file

**Returns**:
- `np.ndarray`: Embedding vector of shape (128,) with dtype float32
- `None`: If extraction fails or no face detected

**Example Usage**:
```python
from accounts.face_utils import extract_embedding

# Extract embedding from uploaded image
embedding = extract_embedding('/media/missing_photos/person1.jpg')

if embedding is not None:
    print(f"Success! Shape: {embedding.shape}, dtype: {embedding.dtype}")
else:
    print("Failed! Check warnings for details")
```

**What It Does**:
1. ✓ Validates image exists and has valid format
2. ✓ Checks image size (>50KB) and dimensions (>100x100)
3. ✓ Detects faces using MTCNN
4. ✓ Warns about 0, 1, or multiple faces
5. ✓ Extracts FaceNet embeddings
6. ✓ Returns numpy array ready for storage

**Edge Cases Handled**:
```python
# Case 1: Image file missing
embedding = extract_embedding('/path/to/nonexistent.jpg')
# Warning: "Image file does not exist"
# Returns: None

# Case 2: Image too small
embedding = extract_embedding('/path/to/tiny_30x40.jpg')
# Warning: "Image is too small (30x40). Minimum required: 100x100 pixels."
# Returns: None

# Case 3: No face detected
embedding = extract_embedding('/path/to/landscape.jpg')
# Warning: "No face detected in image."
# Returns: None

# Case 4: Multiple faces detected
embedding = extract_embedding('/path/to/group_photo.jpg')
# Warning: "Multiple faces detected (3). Using the first/largest face."
# Returns: Embedding (usable, but note the caveat)

# Case 5: DeepFace not installed
embedding = extract_embedding('/path/to/face.jpg')
# Warning: "DeepFace is not available. Cannot extract embeddings."
# Returns: None
```

---

## Function: `compare_faces(embedding1, embedding2)`

Compares two face embeddings using cosine similarity.

**Signature**:
```python
def compare_faces(embedding1: np.ndarray, embedding2: Union[np.ndarray, bytes]) -> float:
    """Compare two face embeddings using cosine similarity."""
```

**Parameters**:
- `embedding1`: numpy array or bytes (first faces)
- `embedding2`: numpy array or bytes (second face)

**Returns**:
- `float`: Similarity score between 0 and 1 (1 = identical)

**Example Usage**:
```python
from accounts.face_utils import compare_faces, deserialize_embedding
from accounts.models import MissingPerson

# Compare two embeddings directly
person1 = MissingPerson.objects.first()
person2 = MissingPerson.objects.last()

# Method 1: Compare deserialized embeddings
emb1 = deserialize_embedding(person1.face_embedding)
emb2 = deserialize_embedding(person2.face_embedding)
score = compare_faces(emb1, emb2)
print(f"Similarity: {score:.2f}")  # Output: "Similarity: 0.65"

# Method 2: Compare directly from database (auto-deserializes)
score = compare_faces(person1.face_embedding, person2.face_embedding)
print(f"Similarity: {score:.2f}")
```

---

## Function: `get_confidence_level(similarity_score)`

Converts a similarity score (0-1) into human-readable confidence information.

**Signature**:
```python
def get_confidence_level(similarity_score: float) -> dict:
    """Convert similarity score to confidence level."""
```

**Parameters**:
- `similarity_score` (float): Score between 0 and 1

**Returns**:
```python
{
    'level': str,           # 'HIGH', 'MEDIUM', 'LOW', or 'NO_MATCH'
    'percentage': int,      # 0-100
    'description': str      # Human-readable description
}
```

**Example Usage**:
```python
from accounts.face_utils import get_confidence_level

# Score 0.82
conf = get_confidence_level(0.82)
print(conf)
# Output:
# {
#     'level': 'HIGH',
#     'percentage': 82,
#     'description': 'Very likely the same person'
# }

# Score 0.68
conf = get_confidence_level(0.68)
print(conf)
# Output:
# {
#     'level': 'MEDIUM',
#     'percentage': 68,
#     'description': 'Possibly the same person'
# }

# Score 0.45
conf = get_confidence_level(0.45)
print(conf)
# Output:
# {
#     'level': 'NO_MATCH',
#     'percentage': 45,
#     'description': 'Not the same person'
# }
```

**Confidence Bands**:
| Score | Level | Meaning |
|-------|-------|---------|
| ≥ 0.75 | HIGH | Very likely same person → Auto-match possible |
| 0.65-0.74 | MEDIUM | Possibly same person → Manual review recommended |
| 0.60-0.64 | LOW | Weak match → Verify manually, high error rate |
| < 0.60 | NO_MATCH | Different people → Reject |

---

## Function: `serialize_embedding(embedding)`

Converts numpy array to bytes for database storage.

**Signature**:
```python
def serialize_embedding(embedding: Optional[np.ndarray]) -> Optional[bytes]:
    """Convert a numpy embedding array to bytes for database storage."""
```

**Parameters**:
- `embedding`: numpy array or None

**Returns**:
- `bytes`: Pickled embedding
- `None`: If input is None

**Used In Django Models**:
```python
from accounts.face_utils import extract_embedding, serialize_embedding
from accounts.models import MissingPerson

# When creating a new report
embedding = extract_embedding('/path/to/photo.jpg')
if embedding is not None:
    person = MissingPerson(name="John", age=30)
    person.face_embedding = serialize_embedding(embedding)
    person.save()
```

---

## Function: `deserialize_embedding(binary)`

Restores numpy array from database bytes.

**Signature**:
```python
def deserialize_embedding(binary: Union[bytes, memoryview, None]) -> Optional[np.ndarray]:
    """Restore a numpy embedding array from its binary representation."""
```

**Parameters**:
- `binary`: Bytes or memoryview from database

**Returns**:
- `np.ndarray`: Shape (128,), dtype float32
- `None`: If input is None

**Used For Matching**:
```python
from accounts.face_utils import deserialize_embedding
from accounts.models import MissingPerson

person = MissingPerson.objects.first()
embedding = deserialize_embedding(person.face_embedding)
# Now use for comparison
```

---

---

## Module: `accounts/matching.py`

### Configuration Constants
```python
CONFIDENCE_THRESHOLD = 0.6              # Minimum threshold (was 0.4)
HIGH_CONFIDENCE_THRESHOLD = 0.75        # High confidence cutoff
MEDIUM_CONFIDENCE_THRESHOLD = 0.65      # Medium confidence cutoff
```

---

## Function: `find_top_matches(source_embedding, queryset, top_k=5, threshold=None)`

Find top N matching faces from a queryset with confidence levels.

**Signature**:
```python
def find_top_matches(
    source_embedding: np.ndarray,
    queryset: QuerySet,
    top_k: int = 5,
    threshold: Optional[float] = None
) -> List[Tuple[float, Model, dict]]:
    """Find top matching faces in a queryset using improved thresholds."""
```

**Parameters**:
- `source_embedding` (np.ndarray): Quality embedding to match against
- `queryset` (QuerySet): Django queryset (MissingPerson, FoundPerson, etc.)
- `top_k` (int): Number of results to return (default: 5)
- `threshold` (float): Minimum score (default: CONFIDENCE_THRESHOLD = 0.6)

**Returns**:
- `list` of tuples: `[(score, obj, confidence_dict), ...]`
  - `score` (float): Similarity 0-1
  - `obj`: Database model instance
  - `confidence_dict`: {'level', 'percentage', 'description'}

**Example Usage**:
```python
from accounts.matching import find_top_matches
from accounts.models import FoundPerson
from accounts.face_utils import deserialize_embedding

# Find matches
source = deserialize_embedding(uploaded_embedding)
matches = find_top_matches(source, FoundPerson.objects.all(), top_k=10)

print(f"Found {len(matches)} matches:")
for score, person, conf in matches:
    print(f"  {person.name:20} | {score:.2f} | {conf['level']:6} ({conf['percentage']}%)")

# Output:
#   John Doe             | 0.82 | HIGH   (82%)
#   Jane Smith           | 0.68 | MEDIUM (68%)
#   Bob Johnson          | 0.55 | NO_MATCH (55%)
```

**Usage in Views**:
```python
# From views.py
matches = find_top_matches(embedding, found_people)

# Format for template
formatted_matches = [
    (score, obj, confidence) 
    for score, obj, confidence in matches
]

# Use in template
for score, obj, confidence in formatted_matches:
    if confidence['level'] == 'HIGH':
        # Auto-action possible
        pass
    elif confidence['level'] in ['MEDIUM', 'LOW']:
        # Show to user for manual review
        pass
```

---

## Function: `find_best_match(source_embedding, queryset, threshold=None)`

Find the single best match with detailed result information.

**Signature**:
```python
def find_best_match(
    source_embedding: np.ndarray,
    queryset: QuerySet,
    threshold: Optional[float] = None
) -> dict:
    """Find the single best matching face in a queryset."""
```

**Parameters**:
- `source_embedding` (np.ndarray): Embedding to search for
- `queryset` (QuerySet): Database query
- `threshold` (float): Minimum match threshold

**Returns**:
```python
{
    'found': bool,                  # True if match above threshold
    'match': Optional[Model],       # Database object if found
    'similarity': float,            # Score 0-1
    'confidence': dict,             # {level, percentage, description}
    'message': str                  # Human-readable message
}
```

**Example Usage**:
```python
from accounts.matching import find_best_match
from accounts.models import MissingPerson

# Search for best match
result = find_best_match(embedding, MissingPerson.objects.all())

if result['found']:
    print(f"✓ Match found:")
    print(f"  Person: {result['match'].name}")
    print(f"  Similarity: {result['similarity']:.2f}")
    print(f"  Confidence: {result['confidence']['level']}")
    print(f"  Message: {result['message']}")
else:
    print(f"✗ {result['message']}")
```

**Real-world Pattern**:
```python
# In a view or API endpoint
result = find_best_match(uploaded_embedding, database_queryset)

# Take action based on result
if result['found']:
    if result['confidence']['level'] == 'HIGH':
        # Auto-create match
        create_match(result['match'])
    else:
        # Notify user for review
        notify_user_for_review(result['match'], result['confidence'])
else:
    # New person, no match found
    create_new_report()
```

---

## Function: `batch_compare_faces(source_embedding, target_embeddings)`

Vectorized comparison of one embedding against many (for future optimization).

**Signature**:
```python
def batch_compare_faces(
    source_embedding: np.ndarray,
    target_embeddings: Union[List, np.ndarray]
) -> np.ndarray:
    """Efficiently compare one source embedding against multiple targets."""
```

**Parameters**:
- `source_embedding`: Single 128-D vector
- `target_embeddings`: List/array of vectors

**Returns**:
- `np.ndarray`: Array of similarity scores (same length as targets)

**Example Usage**:
```python
from accounts.matching import batch_compare_faces
from accounts.models import MissingPerson
from accounts.face_utils import deserialize_embedding

# Batch comparison (useful for large searches)
source = deserialize_embedding(uploaded_embedding)

# Get all embeddings
targets = [
    deserialize_embedding(p.face_embedding)
    for p in MissingPerson.objects.filter(face_embedding__isnull=False)
]

# Compare all at once
scores = batch_compare_faces(source, targets)

print(f"Compared against {len(scores)} people")
print(f"Highest match: {scores.max():.2f}")
print(f"Average similarity: {scores.mean():.2f}")
```

---

## Complete Example: Report a Missing Person

```python
from accounts.models import UserProfile, MissingPerson, FoundPerson
from accounts.face_utils import extract_embedding, serialize_embedding
from accounts.matching import find_top_matches, find_best_match

# Step 1: User uploads image with missing person form
uploaded_image_path = '/media/missing_photos/new_person.jpg'

# Step 2: Extract embedding
embedding = extract_embedding(uploaded_image_path)
if embedding is None:
    return error("Could not detect face in image")

# Step 3: Create missing person record
missing_person = MissingPerson(
    user=request.user,
    name="John Doe",
    age=35,
    gender="M",
    last_seen_location="Downtown Station",
    description="Last seen wearing blue jacket",
    photo_path=uploaded_image_path,
)
missing_person.face_embedding = serialize_embedding(embedding)
missing_person.save()

# Step 4: Search for matches in found people
found_people = FoundPerson.objects.filter(
    face_embedding__isnull=False,
    status="open"
)
matches = find_top_matches(embedding, found_people, top_k=5)

# Step 5: Process results
if matches:
    best_score, best_match, confidence = matches[0]
    
    if confidence['level'] == 'HIGH':
        # Auto-close both records - high confidence match
        missing_person.status = "closed"
        best_match.status = "closed"
        both.save()
        notify_user("Match found with high confidence!")
    else:
        # Show to user for manual review
        show_matches(missing_person, matches)
else:
    notify_user("No matches found. We'll keep searching.")
    
# Step 6: Render results to template with confidence info
return render(request, 'match_results.html', {
    'source': missing_person,
    'matches': matches,  # Now contains: (score, obj, confidence)
})
```

---

## Error Handling Best Practices

```python
from accounts.face_utils import extract_embedding
from accounts.matching import find_top_matches
import warnings

# Capture all warnings
warnings.filterwarnings('always')

try:
    # Extraction with error handling
    embedding = extract_embedding(image_path)
    if embedding is None:
        # Check what went wrong via logs
        return JsonResponse({
            'status': 'error',
            'message': 'Could not extract face from image. Is it a clear face photo?'
        }, status=400)
    
    # Matching with error handling
    matches = find_top_matches(embedding, queryset)
    if not matches:
        return JsonResponse({
            'status': 'success',
            'message': 'No matches found',
            'matches': []
        })
    
    return JsonResponse({
        'status': 'success',
        'matches': [
            {
                'id': obj.id,
                'name': obj.name,
                'score': float(score),
                'confidence': confidence
            }
            for score, obj, confidence in matches
        ]
    })

except Exception as e:
    # Log unexpected errors
    print(f"Unexpected error: {str(e)}")
    return JsonResponse({
        'status': 'error',
        'message': 'An unexpected error occurred. Please try again.'
    }, status=500)
```

---

**Last Updated**: April 15, 2026  
**Version**: 2.0  
**Status**: Complete and tested ✓
