from typing import Dict
from d3a.constants import TIME_FORMAT
from d3a.models.strategy.pv import PVStrategy
from d3a.models.strategy.storage import StorageStrategy
from d3a.models.strategy.load_hours import LoadHoursStrategy
from d3a.models.strategy.finite_power_plant import FinitePowerPlant
from d3a.models.strategy.infinite_bus import InfiniteBusStrategy
from d3a.models.area import Area
from d3a import limit_float_precision

FILL_VALUE = None


def _create_or_append_dict(dict, key, subdict):
    if key not in dict.keys():
        dict[key] = {}
    dict[key].update(subdict)


class DeviceStatistics:

    def __init__(self):
        self.device_stats_dict = {}
        self.current_stats_dict = {}
        self.current_stats_time_str = {}

    @staticmethod
    def _calc_min_max_from_sim_dict(subdict: Dict, key: str):

        min_trade_stats_daily = {}
        max_trade_stats_daily = {}
        indict = subdict[key]

        trade_stats_daily = dict((k.format(TIME_FORMAT), []) for k, v in indict.items())
        for time, value in indict.items():
            value = [] if value is None else value
            value = [value] if not isinstance(value, list) else value
            trade_stats_daily[time.format(TIME_FORMAT)] += value

        for time_str, value in trade_stats_daily.items():
            min_trade_stats_daily[time_str] = limit_float_precision(min(value)) \
                if len(value) > 0 else FILL_VALUE
            max_trade_stats_daily[time_str] = limit_float_precision(max(value)) \
                if len(value) > 0 else FILL_VALUE

        min_trade_stats = dict((time, min_trade_stats_daily[time.format(TIME_FORMAT)])
                               for time in indict.keys())
        max_trade_stats = dict((time, max_trade_stats_daily[time.format(TIME_FORMAT)])
                               for time in indict.keys())

        _create_or_append_dict(subdict, f"min_{key}",
                               min_trade_stats)
        _create_or_append_dict(subdict, f"max_{key}",
                               max_trade_stats)

    @classmethod
    def _device_price_stats(cls, area: Area, subdict: Dict):
        key_name = "trade_price_eur"
        market = list(area.parent.past_markets)[-1]
        trade_price_list = []
        for t in market.trades:
            if t.seller == area.name or t.buyer == area.name:
                trade_price_list.append(t.offer.energy_rate / 100.0)

        if trade_price_list:
            _create_or_append_dict(subdict, key_name,
                                   {market.time_slot: trade_price_list})
        else:
            _create_or_append_dict(subdict, key_name, {market.time_slot: FILL_VALUE})

        cls._calc_min_max_from_sim_dict(subdict, key_name)

    @classmethod
    def _device_energy_stats(cls, area: Area, subdict: Dict):
        market = list(area.parent.past_markets)[-1]
        if type(area.strategy) == InfiniteBusStrategy:
            cls.calculate_stats_for_infinite_bus(area, market, subdict)
        else:
            cls.calculate_stats_for_device(area, market, subdict)

    @classmethod
    def calculate_stats_for_device(cls, area, market, subdict):
        key_name = "trade_energy_kWh"
        traded_energy = 0
        for t in market.trades:
            if t.seller == area.name:
                traded_energy -= t.offer.energy
            if t.buyer == area.name:
                traded_energy += t.offer.energy

        _create_or_append_dict(subdict, key_name, {market.time_slot: traded_energy})
        cls._calc_min_max_from_sim_dict(subdict, key_name)

    @classmethod
    def calculate_stats_for_infinite_bus(cls, area, market, subdict):
        sold_key_name = "sold_trade_energy_kWh"
        bought_key_name = "bought_trade_energy_kWh"
        sold_traded_energy = 0
        bought_traded_energy = 0

        for t in market.trades:
            if t.seller == area.name:
                sold_traded_energy += t.offer.energy
            if t.buyer == area.name:
                bought_traded_energy += t.offer.energy

        _create_or_append_dict(subdict, sold_key_name, {market.time_slot: sold_traded_energy})
        cls._calc_min_max_from_sim_dict(subdict, sold_key_name)
        _create_or_append_dict(subdict, bought_key_name,
                               {market.time_slot: bought_traded_energy})
        cls._calc_min_max_from_sim_dict(subdict, bought_key_name)

    @classmethod
    def _pv_production_stats(cls, area: Area, subdict: Dict):
        key_name = "pv_production_kWh"
        market = list(area.parent.past_markets)[-1]

        _create_or_append_dict(
            subdict, key_name,
            {market.time_slot:
                area.strategy.energy_production_forecast_kWh.get(market.time_slot, 0)})

        cls._calc_min_max_from_sim_dict(subdict, key_name)

    @classmethod
    def _soc_stats(cls, area: Area, subdict: Dict):
        key_name = "soc_history_%"
        market = list(area.parent.past_markets)[-1]
        _create_or_append_dict(subdict, key_name,
                               {market.time_slot:
                                area.strategy.state.charge_history[market.time_slot]})

        cls._calc_min_max_from_sim_dict(subdict, key_name)

    @classmethod
    def _load_profile_stats(cls, area: Area, subdict: Dict):
        key_name = "load_profile_kWh"
        market = list(area.parent.past_markets)[-1]
        if market.time_slot in area.strategy.state.desired_energy_Wh:
            _create_or_append_dict(subdict, key_name, {
                market.time_slot:
                    area.strategy.state.desired_energy_Wh.get(market.time_slot, 0) / 1000.})
        else:
            _create_or_append_dict(subdict, key_name, {market.time_slot: 0})

        cls._calc_min_max_from_sim_dict(subdict, key_name)

    def update(self, area):
        self.gather_device_statistics(area, self.device_stats_dict, {})
        # TODO: only calculate this if redis is enabled:
        self.gather_device_statistics(area, {}, self.current_stats_dict)

    @classmethod
    def gather_device_statistics(cls, area: Area, subdict: Dict, flat_result_dict: Dict):
        for child in area.children:
            if child.name not in subdict.keys():
                subdict.update({child.name: {}})
            if child.children == []:
                cls._gather_device_statistics(child, subdict[child.name], flat_result_dict)
            else:
                cls.gather_device_statistics(child, subdict[child.name], flat_result_dict)

    @classmethod
    def _gather_device_statistics(cls, area: Area, subdict: Dict, flat_result_dict: Dict):
        if not hasattr(area.parent, "past_markets") or len(area.parent.past_markets) == 0:
            return None

        if area.strategy is not None:
            cls._device_price_stats(area, subdict)
            cls._device_energy_stats(area, subdict)

        if isinstance(area.strategy, PVStrategy):
            cls._pv_production_stats(area, subdict)

        elif isinstance(area.strategy, StorageStrategy):
            cls._soc_stats(area, subdict)

        elif isinstance(area.strategy, LoadHoursStrategy):
            cls._load_profile_stats(area, subdict)

        elif type(area.strategy) == FinitePowerPlant:
            market = list(area.parent.past_markets)[-1]
            _create_or_append_dict(subdict, "production_kWh",
                                   {market.time_slot: area.strategy.energy_per_slot_kWh})
            cls._calc_min_max_from_sim_dict(subdict, "production_kWh")

        flat_result_dict[area.uuid] = subdict.copy()
