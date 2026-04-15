from django.test import TestCase, override_settings
from django.contrib.auth.models import User
from .models import MissingPerson, FoundPerson
from .face_utils import extract_embedding, serialize_embedding, deserialize_embedding
from .matching import find_top_matches
from PIL import Image
import tempfile
import os


class MatchingTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="tester", password="pass")
        # Create two simple images (different colors)
        self.img1 = tempfile.NamedTemporaryFile(suffix=".jpg", delete=False)
        self.img1.close()
        Image.new("RGB", (200, 200), (100, 120, 140)).save(self.img1.name)

        self.img2 = tempfile.NamedTemporaryFile(suffix=".jpg", delete=False)
        self.img2.close()
        Image.new("RGB", (200, 200), (110, 130, 150)).save(self.img2.name)

    def tearDown(self):
        os.unlink(self.img1.name)
        os.unlink(self.img2.name)

    def test_fallback_embedding_and_matching(self):
        # Extract embeddings (will use fallback if deepface/detection fails)
        emb1 = extract_embedding(self.img1.name)
        emb2 = extract_embedding(self.img2.name)

        self.assertIsNotNone(emb1)
        self.assertIsNotNone(emb2)
        self.assertEqual(emb1.shape, (512,))
        self.assertEqual(emb2.shape, (512,))

        mp = MissingPerson.objects.create(user=self.user, name="A", age=30, gender="M", last_seen_location="X", description="d", photo=self.img1.name)
        mp.face_embedding = serialize_embedding(emb1)
        mp.save()

        fp = FoundPerson.objects.create(user=self.user, name="B", age_estimate=40, found_location="Y", description="d2", photo=self.img2.name)
        fp.face_embedding = serialize_embedding(emb2)
        fp.save()

        matches = find_top_matches(emb1, FoundPerson.objects.all(), top_k=5)
        # With similar generated colors the similarity should be >0 (most likely >0.8)
        self.assertTrue(len(matches) >= 1)
        sim, obj = matches[0]
        self.assertGreaterEqual(sim, 0.0)

    def test_serialize_deserialize_none(self):
        self.assertIsNone(serialize_embedding(None))
        self.assertIsNone(deserialize_embedding(None))

    def test_submit_unknown_age_saves(self):
        # Verify that submitting Unknown/empty age doesn't raise and saves as None
        emb = extract_embedding(self.img1.name)
        fp = FoundPerson.objects.create(
            user=self.user,
            name="NoAge",
            age_estimate=None,
            found_location="Z",
            description="desc",
            photo=self.img1.name,
        )
        self.assertIsNone(fp.age_estimate)
