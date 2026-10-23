@cloudinary
Feature: Uploading songs with audio
  As a logged-in user
  I want to upload songs with audio files
  So that I can store and play my music

  Background:
    Given a user "alice" with password "Sup3r-Secret-Pass!"

  Scenario: Upload a song with an audio file
    Given "alice" is logged in
    When "alice" uploads a song titled "Take Five" with an audio file
    Then the song "Take Five" exists for "alice"
    And the song "Take Five" belongs to "alice"
    And the song "Take Five" is stored on Cloudinary

  Scenario: Uploaded songs are private to the uploader
    Given a user "bob" with password "Sup3r-Secret-Pass!"
    And "alice" is logged in
    And "alice" uploads a song titled "Take Five" with an audio file
    When "bob" is logged in
    And "bob" views the song list
    Then the song list does not show "Take Five"