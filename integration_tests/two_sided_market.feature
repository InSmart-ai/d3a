Feature: Two sided market tests

  Scenario: One storage, one load
     Given we have a scenario named two_sided_market/one_load_one_storage
     And d3a is installed
     When we run the simulation with setup file two_sided_market.one_load_one_storage and parameters [24, 60, 60, 1]
     Then the storage is never buying energy and is always selling energy
     And the storage final SOC is 10%
     And all the trade rates are between load device buying boundaries
     And Energy producer is H1 Storage & consumer is H2 General Load

  Scenario: One pv, one load
     Given we have a scenario named two_sided_market/one_pv_one_load
     And d3a is installed
     When we run the simulation with setup file two_sided_market.one_pv_one_load and parameters [24, 60, 60, 4]
     Then the load has no unmatched loads
     And the PV always provides constant power according to load demand
     And Energy producer is H2 PV & consumer is H1 General Load

  Scenario: One storage, one pv
     Given we have a scenario named two_sided_market/one_pv_one_storage
     And d3a is installed
     When we run the simulation with setup file two_sided_market.one_pv_one_storage and parameters [24, 60, 60, 4]
     Then the storage is never selling energy
     And the storage final SOC is 100%
     And the energy rate for all trades are in between initial and final buying rate of storage
     And Energy producer is H2 PV & consumer is H1 Storage

  Scenario: 5 pv, one load
     Given we have a scenario named two_sided_market/one_load_5_pv_partial
     And d3a is installed
     When we run the simulation with setup file two_sided_market.one_load_5_pv_partial and parameters [24, 60, 60, 4]
     Then the load has unmatched loads
     And the load bid is partially fulfilled by the PV offers

  Scenario: 5 pv, one storage
     Given we have a scenario named two_sided_market/one_storage_5_pv_partial
     And d3a is installed
     When we run the simulation with setup file two_sided_market.one_storage_5_pv_partial and parameters [24, 30, 30, 4]
     Then the storage bid is partially fulfilled by the PV offers

  Scenario: LoadHoursStrategy buys energy in the min rate range provided by the user as dict profile
    Given we have a scenario named two_sided_market/user_min_rate_profile_load_dict
    And d3a is installed
    When we run the simulation with setup file two_sided_market.user_min_rate_profile_load_dict and parameters [24, 60, 60, 4]
    Then LoadHoursStrategy buys energy with rates equal to the initial buying rate profile

  Scenario: LoadHoursStrategy buys energy in the min energy rate
    Given we have a scenario named two_sided_market/one_cep_one_load
    And d3a is installed
    When we run the simulation with setup file two_sided_market.one_cep_one_load and parameters [24, 60, 60, 4]
    Then LoadHoursStrategy buys energy at the final_buying_rate
    And Energy producer is Commercial Energy Producer & consumer is H1 General Load

  Scenario: Residual Offer always reposted at the old rate
    Given we have a scenario named two_sided_market/offer_reposted_at_old_offer_rate
    And d3a is installed
    When we run the simulation with setup file two_sided_market.offer_reposted_at_old_offer_rate and parameters [24, 60, 60, 1]
    Then CEP posted the residual offer at the old rate

  Scenario Outline: Trades will always clear in the middle if min offer age == min bid age
     Given we have a scenario named two_sided_market/one_cep_one_load_immediate_match
     And d3a is installed
     And the min offer age is set to <min_bid_age> tick
     And the min bid age is set to <min_bid_age> ticks
     When we run the simulation with setup file two_sided_market.one_cep_one_load_immediate_match and parameters [24, 60, 60, 1]
     Then the load has no unmatched loads
     And trades are matched only on the Grid market
  Examples: Min Bid Age
     | min_bid_age |
     |      1      |
     |      2      |
     |      5      |
     |      9      |

  Scenario Outline: Trades will always clear in the demand side if min offer age < min bid age
     Given we have a scenario named two_sided_market/one_cep_one_load_immediate_match
     And d3a is installed
     And the min offer age is set to 0 tick
     And the min bid age is set to <min_bid_age> ticks
     When we run the simulation with setup file two_sided_market.one_cep_one_load_immediate_match and parameters [24, 60, 60, 1]
     Then the load has no unmatched loads
     And trades are matched only on the House 1 market
  Examples: Min Bid Age
     | min_bid_age |
     |      2      |
     |      5      |
     |      9      |

  Scenario Outline: Trades will always clear in the supply side if min offer age > min bid age
     Given we have a scenario named two_sided_market/one_cep_one_load_immediate_match
     And d3a is installed
     And the min offer age is set to 10 tick
     And the min bid age is set to <min_bid_age> ticks
     When we run the simulation with setup file two_sided_market.one_cep_one_load_immediate_match and parameters [24, 60, 60, 1]
     Then the load has no unmatched loads
     And trades are matched only on the House 2 market
  Examples: Min Bid Age
     | min_bid_age |
     |      0      |
     |      1      |
     |      4      |