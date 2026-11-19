@web_search
Feature: Searching songs across the library and the web
  As a logged-in user
  I want search to include results from the web
  So that I can find songs even if they aren't in my library

  Scenario: Web results appear and play royalty-free music
    Given I am a logged-in user
    When I search for "radiohead"
    Then the web results include "Creep"
    And the web results include "Karma Police"
    And the web results play royalty-free music

  Scenario: A song I own is not duplicated as a web result
    Given I am a logged-in user
    And I own the song "Creep" by "Radiohead"
    When I search for "radiohead"
    Then my library results include "Creep"
    And the web results do not include "Creep"
    And the web results include "Karma Police"