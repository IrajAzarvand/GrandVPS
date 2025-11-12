from django.test import TestCase
from django.contrib.auth.models import User
from accounts.models import UserProfile


class UserProfileTest(TestCase):

    def test_user_profile_creation(self):
        user = User.objects.create_user(username='testuser', password='password123')
        profile = UserProfile.objects.get(user=user)
        self.assertEqual(profile.user, user)
        self.assertEqual(profile.timezone, 'Asia/Tehran')
        self.assertIsNone(profile.phone)

    def test_user_profile_str(self):
        user = User.objects.create_user(username='testuser', password='password123')
        profile = UserProfile.objects.get(user=user)
        self.assertEqual(str(profile), 'testuser')

    def test_user_profile_with_phone(self):
        user = User.objects.create_user(username='testuser', password='password123')
        profile = UserProfile.objects.get(user=user)
        profile.phone = '1234567890'
        profile.save()
        profile.refresh_from_db()
        self.assertEqual(profile.phone, '1234567890')

    def test_signal_creates_profile_on_user_creation(self):
        user = User.objects.create_user(username='testuser', password='password123')
        self.assertTrue(UserProfile.objects.filter(user=user).exists())
        profile = UserProfile.objects.get(user=user)
        self.assertEqual(profile.timezone, 'Asia/Tehran')

    def test_signal_saves_profile_on_user_save(self):
        user = User.objects.create_user(username='testuser', password='password123')
        profile = UserProfile.objects.get(user=user)
        profile.phone = '0987654321'
        profile.save()
        user.email = 'test@example.com'
        user.save()
        profile.refresh_from_db()
        self.assertEqual(profile.phone, '0987654321')

    def test_user_profile_phone_blank(self):
        user = User.objects.create_user(username='testuser', password='password123')
        profile = UserProfile.objects.get(user=user)
        profile.phone = ''
        profile.save()
        profile.refresh_from_db()
        self.assertEqual(profile.phone, '')

    def test_user_profile_timezone_custom(self):
        user = User.objects.create_user(username='testuser', password='password123')
        profile = UserProfile.objects.get(user=user)
        profile.timezone = 'UTC'
        profile.save()
        profile.refresh_from_db()
        self.assertEqual(profile.timezone, 'UTC')


# Since views.py is empty, no view tests are included
# No forms exist in the accounts app
