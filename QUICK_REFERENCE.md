# Quick Reference - Template Update Example

## Current Match Template Structure

If your `match_results.html` looks like this:

```html
{% for score, obj in matches %}
    <div class="match-item">
        <h3>{{ obj.name }}</h3>
        <p>Score: {{ score }}</p>
    </div>
{% endfor %}
```

### Update it to:

```html
{% for score, obj, confidence in matches %}
    <div class="match-item">
        <h3>{{ obj.name }}</h3>
        <p>Score: {{ score|floatformat:2 }}</p>
        
        <!-- NEW: Add confidence level display -->
        <div class="confidence-badge confidence-{{ confidence.level|lower }}">
            <strong>{{ confidence.level }}</strong>
            <span class="percentage">({{ confidence.percentage }}%)</span>
        </div>
        <p class="description">{{ confidence.description }}</p>
    </div>
{% endfor %}
```

### Add CSS styling:

```css
.confidence-badge {
    padding: 8px 12px;
    border-radius: 4px;
    margin: 10px 0;
    font-weight: bold;
}

.confidence-high {
    background-color: #d4edda;
    color: #155724;
    border: 1px solid #28a745;
}

.confidence-medium {
    background-color: #fff3cd;
    color: #856404;
    border: 1px solid #ffc107;
}

.confidence-low {
    background-color: #d1ecf1;
    color: #0c5460;
    border: 1px solid #17a2b8;
}

.confidence-no_match {
    background-color: #f8d7da;
    color: #721c24;
    border: 1px solid #dc3545;
}

.confidence-badge .percentage {
    font-size: 0.9em;
    margin-left: 5px;
}

.description {
    font-size: 0.9em;
    margin-top: 5px;
    font-style: italic;
}
```

---

## Testing Checklist

### ✓ Test 1: Face Extraction with Edge Cases
```bash
python manage.py shell

from accounts.face_utils import extract_embedding
import warnings

# Test with good image
warnings.filterwarnings('always')
emb = extract_embedding('path/to/good/face.jpg')
print(f"Good image: {'✓ Success' if emb is not None else '✗ Failed'}")

# Test with no face
emb = extract_embedding('path/to/landscape.jpg')
print(f"No face: {'✓ Handled' if emb is None else '✗ Should have failed'}")

# Test with multiple faces
emb = extract_embedding('path/to/group.jpg')
print(f"Multiple faces: {'✓ Handled' if emb is not None else '✗ Should succeed'}")

# Test with poor quality
emb = extract_embedding('path/to/tiny_50x50.jpg')
print(f"Poor quality: {'✓ Rejected' if emb is None else '✗ Should reject'}")
```

### ✓ Test 2: Matching with Confidence
```bash
from accounts.models import MissingPerson, FoundPerson
from accounts.matching import find_top_matches
from accounts.face_utils import deserialize_embedding

# Get a source embedding
source = MissingPerson.objects.first()
if source.face_embedding:
    emb = deserialize_embedding(source.face_embedding)
    
    # Find matches
    matches = find_top_matches(emb, FoundPerson.objects.all())
    
    print(f"Found {len(matches)} matches:")
    for score, obj, confidence in matches:
        print(f"  {obj.name}: {confidence['level']} ({score:.2f})")
```

### ✓ Test 3: Auto-Close Logic
```bash
# Manually trigger a found posting and verify auto-close happens
# Only when confidence level is HIGH, not just score > 0.7
```

### ✓ Test 4: Web UI Testing
1. Register a new account
2. Report a missing person with a clear face photo
3. Verify embedding extraction succeeds
4. Report a found person matched to the missing person
5. Check that matches show confidence levels (HIGH/MEDIUM/LOW)
6. Verify auto-close only happens for HIGH confidence matches

---

## Troubleshooting

### Issue: "DeepFace is not available"
```bash
pip install deepface
# If it still fails, check Python version (must be 3.8+)
python --version
```

### Issue: Embeddings are None
- Check image file exists: `os.path.exists(path)`
- Check image size: file should be > 50KB
- Check image dimensions: should be > 100x100
- Check face is clear and frontal

### Issue: Thresholds seem wrong
Edit in `accounts/matching.py`:
```python
CONFIDENCE_THRESHOLD = 0.5  # Lower for more sensitivity
HIGH_CONFIDENCE_THRESHOLD = 0.70  # Adjust as needed
```

### Issue: Performance is slow
- First request will be slow (model loading)
- Subsequent requests should be ~500ms
- For production, use async task queue (Celery)

---

## Deployment Checklist

- [ ] Test all 4 test cases above
- [ ] Update `match_results.html` template
- [ ] Add CSS styling to stylesheet
- [ ] Verify `requirements.txt` has deepface (it does)
- [ ] Run `python manage.py runserver` and test web UI
- [ ] Check admin panel that embeddings are being saved
- [ ] Test with real face images from your database
- [ ] Monitor performance (should be < 3 seconds per request)
- [ ] Commit changes to git

---

## Rollback Plan (if needed)

If something goes wrong, the old code is still available in comments/git history:

```bash
# View git history
git log --oneline accounts/face_utils.py
git log --oneline accounts/matching.py
git log --oneline accounts/views.py

# Revert a single file
git checkout HEAD~1 accounts/face_utils.py
```

But the changes are backward compatible! The new return format from find_top_matches() is a superset, so it should work with most templates.
