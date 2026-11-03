"""Browser tests: pressing shuffle reorders the queue."""

import json
import unittest
from flaky import flaky
from django.contrib.auth import get_user_model
from django.test import LiveServerTestCase
from django.urls import reverse

try:
    from selenium import webdriver
    from selenium.webdriver.common.by import By
    from selenium.webdriver.chrome.options import Options
    from selenium.webdriver.support.ui import WebDriverWait
    SELENIUM = True
except ImportError:
    SELENIUM = False

# Tiny valid WAV so the <audio> element doesn't fire an error and skip tracks.
SILENT_WAV = "data:audio/wav;base64,UklGRiQAAABXQVZFZm10IBAAAAABAAEAQB8AAEAfAAABAAgAZGF0YQAAAAA="


@unittest.skipUnless(SELENIUM, "selenium is not installed")
class ShuffleQueueBrowserTests(LiveServerTestCase):


    ##########################
    # The Setup
    ##########################
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        options = Options()
        options.add_argument("--headless=new")
        options.add_argument("--window-size=1280,900")
        cls.driver = webdriver.Chrome(options=options)

    @classmethod
    def tearDownClass(cls):
        cls.driver.quit()
        super().tearDownClass()

    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username="shuffler", password="pass12345"
        )
        self.client.force_login(self.user)
        session = self.client.cookies["sessionid"].value

        # Seed on the admin login page: it has no player script, so nothing
        # clears localStorage when we navigate away.
        self.driver.get(self.live_server_url + "/admin/login/")
        self.driver.add_cookie({"name": "sessionid", "value": session})

    def open_with_queue(self, count, index=0):
        items = [
            {"id": str(n), "title": f"Song {n}", "artist": "Artist", "url": SILENT_WAV}
            for n in range(1, count + 1)
        ]
        payload = json.dumps({"items": items, "index": index, "time": 0, "playing": False})
        self.driver.execute_script(
            "localStorage.setItem(arguments[0], arguments[1]);",
            f"crate-queue-{self.user.pk}",
            payload,
        )
        self.driver.get(self.live_server_url + reverse("song_list"))
        self.driver.find_element(By.ID, "player-queue-toggle").click()
        WebDriverWait(self.driver, 5).until(
            lambda d: len(d.find_elements(By.CSS_SELECTOR, "#queue-list li")) == count
        )

    def titles(self):
        spans = self.driver.find_elements(
            By.CSS_SELECTOR, '#queue-list button[data-action="jump"] span'
        )
        return [s.text for s in spans]

    ##########################
    # The Tests
    ##########################

    # loads 8 songs, presses shuffle, checks that order is changed
    @flaky(max_runs=3,min_passes=1)
    def test_shuffle_changes_queue_order(self):
        self.open_with_queue(count=8)
        before = self.titles()

        self.driver.find_element(By.ID, "player-shuffle").click()

        after = self.titles()
        self.assertNotEqual(before, after)             # order changed
        self.assertEqual(sorted(before), sorted(after))  # same songs, none lost
        self.assertEqual(before[0], after[0])          # current song untouched

    # loads 2 songs, and checks if button is disabled
    def test_shuffle_button_disabled_with_fewer_than_two_upcoming(self):
        self.open_with_queue(count=2)  # 1 current + 1 upcoming
        button = self.driver.find_element(By.ID, "player-shuffle")
        self.assertFalse(button.is_enabled())

    # loads 3 songs, and checks that the button is enabled
    def test_shuffle_button_enabled_with_two_or_more_upcoming(self):
        self.open_with_queue(count=3)  # 1 current + 2 upcoming
        button = self.driver.find_element(By.ID, "player-shuffle")
        self.assertTrue(button.is_enabled())