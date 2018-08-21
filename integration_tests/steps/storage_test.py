from behave import then


@then('the storage devices buy and sell energy respecting the break even prices')
def check_storage_prices(context):
    house1 = list(filter(lambda x: x.name == "House 1", context.simulation.area.children))[0]
    storage = list(filter(lambda x: x.name == "H1 Storage1", house1.children))[0]
    trades_sold = []
    trades_bought = []
    for slot, market in house1.past_markets.items():
        for trade in market.trades:
            if trade.seller in ["H1 Storage1"]:
                trades_sold.append(trade)
            elif trade.buyer in ["H1 Storage1"]:
                trades_bought.append(trade)
    assert all([trade.offer.price / trade.offer.energy >=
                storage.strategy.break_even[0][1] for trade in trades_sold])
    assert all([trade.offer.price / trade.offer.energy <=
                storage.strategy.break_even[0][0] for trade in trades_bought])
    assert len(trades_sold) > 0
    assert len(trades_bought) > 0


@then('the storage devices buy and sell energy respecting the hourly break even prices')
def step_impl(context):
    from d3a.setup.strategy_tests.storage_strategy_break_even_hourly import \
        break_even_profile, break_even_profile_2
    house1 = list(filter(lambda x: x.name == "House 1", context.simulation.area.children))[0]
    for name, profile in [("H1 Storage1", break_even_profile),
                          ("H1 Storage2", break_even_profile_2)]:
        trades_sold = []
        trades_bought = []
        for slot, market in house1.past_markets.items():
            for trade in market.trades:
                if trade.seller == name:
                    trades_sold.append(trade)
                elif trade.buyer == name:
                    trades_bought.append(trade)

        assert all([round((trade.offer.price / trade.offer.energy), 2) >=
                    round(profile[trade.time.hour][1], 2) for trade in trades_sold])
        assert all([round((trade.offer.price / trade.offer.energy), 2) <=
                    round(profile[trade.time.hour][0], 2) for trade in trades_bought])
        assert len(trades_sold) > 0
        assert len(trades_bought) > 0


@then('the storage devices sell energy respecting the break even prices')
def check_storage_sell_prices(context):
    house1 = list(filter(lambda x: x.name == "House 1", context.simulation.area.children))[0]
    storage = list(filter(lambda x: x.name == "H1 Storage1", house1.children))[0]
    trades_sold = []
    trades_bought = []
    for slot, market in house1.past_markets.items():
        for trade in market.trades:
            if trade.seller in ["H1 Storage1"]:
                trades_sold.append(trade)
            elif trade.buyer in ["H1 Storage1"]:
                trades_bought.append(trade)
    assert all([trade.offer.price / trade.offer.energy >=
                storage.strategy.break_even[0][1] for trade in trades_sold])
    assert len(trades_sold) > 0


@then('the storage devices sell offer rate is based on it SOC')
def check_capacity_dependant_sell_rate(context):
    house1 = list(filter(lambda x: x.name == "House 1", context.simulation.area.children))[0]
    storage = list(filter(lambda x: x.name == "H1 Storage1", house1.children))[0]
    trades_sold = []
    for slot, market in house1.past_markets.items():
        for trade in market.trades:
            if trade.seller in ["H1 Storage1"]:
                trades_sold.append(trade)
                trade_rate = round((trade.offer.price / trade.offer.energy), 2)
                break_even_sell = round(storage.strategy.break_even[slot.hour][1], 2)
                market_maker_rate = \
                    round(context.simulation.area.config.market_maker_rate[slot.hour], 2)
                assert trade_rate >= break_even_sell
                assert trade_rate <= market_maker_rate
    assert len(trades_sold) > 0