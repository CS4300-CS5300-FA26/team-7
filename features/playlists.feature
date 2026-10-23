Feature: Creating and organizing playlists
  As a logged-in user
  I want to group my songs into playlists
  So that I can organize my music

  Background:
    Given a user "alice" with password "Sup3r-Secret-Pass!"
    And "alice" has a song titled "So What"
    And "alice" has a song titled "Blue in Green"

  Scenario: Create a playlist containing a chosen song
    Given "alice" is logged in
    When "alice" creates a playlist named "Jazz Night" containing "So What"
    Then the playlist "Jazz Night" exists for "alice"
    And the playlist "Jazz Night" contains "So What"
    And the playlist "Jazz Night" does not contain "Blue in Green"

  Scenario: Playlists are private to their owner
    Given a user "bob" with password "Sup3r-Secret-Pass!"
    And "alice" is logged in
    And "alice" creates a playlist named "Jazz Night" containing "So What"
    When "bob" is logged in
    And "bob" views the playlists page
    Then the playlists page does not list "Jazz Night"

  Scenario: A blank playlist name creates nothing
    Given "alice" is logged in
    When "alice" submits the create-playlist form with a blank name
    Then "alice" has no playlists