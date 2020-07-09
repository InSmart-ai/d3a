"""
Copyright 2018 Grid Singularity
This file is part of D3A.

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see <http://www.gnu.org/licenses/>.
"""
from d3a.models.strategy.infinite_bus import InfiniteBusStrategy
from d3a.d3a_core.util import if_not_in_list_append
from d3a.d3a_core.sim_results.area_statistics import _is_load_node, _is_prosumer_node, \
    _is_producer_node


class KPIState:
    def __init__(self):
        self.producer_list = list()
        self.consumer_list = list()
        self.areas_to_trace_list = list()
        self.ess_list = list()
        self.buffer_list = list()
        self.total_energy_demanded_wh = 0
        self.demanded_buffer_wh = 0
        self.total_energy_produced_wh = 0
        self.total_self_consumption_wh = 0
        self.self_consumption_buffer_wh = 0
        self.accounted_markets = {}

    def accumulate_devices(self, area):
        for child in area.children:
            if _is_producer_node(child) and type(child.strategy) is not InfiniteBusStrategy:
                if_not_in_list_append(self.producer_list, child.name)
                if_not_in_list_append(self.areas_to_trace_list, child.parent)
            elif _is_load_node(child):
                if_not_in_list_append(self.consumer_list, child.name)
                if_not_in_list_append(self.areas_to_trace_list, child.parent)
            elif _is_prosumer_node(child):
                if_not_in_list_append(self.ess_list, child.name)
            elif isinstance(child.strategy, InfiniteBusStrategy):
                if_not_in_list_append(self.buffer_list, child.name)
            if child.children:
                self.accumulate_devices(child)

    def _accumulate_total_energy_demanded(self, area):
        for child in area.children:
            if _is_load_node(child):
                self.total_energy_demanded_wh += child.strategy.state.total_energy_demanded_wh
            if child.children:
                self._accumulate_total_energy_demanded(child)

    def _accumulate_self_production(self, trade):
        # Trade seller origin should be equal to the trade seller in order to
        # not double count trades in higher hierarchies
        if trade.seller_origin in self.producer_list and trade.seller_origin == trade.seller:
            self.total_energy_produced_wh += trade.offer.energy * 1000

    def _accumulate_self_consumption(self, trade):
        # Trade buyer origin should be equal to the trade buyer in order to
        # not double count trades in higher hierarchies
        if trade.seller_origin in self.producer_list and \
                trade.buyer_origin in self.consumer_list and \
                trade.buyer_origin == trade.buyer:
            self.total_self_consumption_wh += trade.offer.energy * 1000

    def _accumulate_self_consumption_buffer(self, trade):
        if trade.seller_origin in self.producer_list and trade.buyer_origin in self.ess_list:
            self.self_consumption_buffer_wh += trade.offer.energy * 1000

    def _dissipate_self_consumption_buffer(self, trade):
        if trade.seller_origin in self.ess_list:
            # self_consumption_buffer needs to be exhausted to total_self_consumption
            # if sold to internal consumer
            if trade.buyer_origin in self.consumer_list and \
                    trade.buyer_origin == trade.buyer and \
                    self.self_consumption_buffer_wh > 0:
                if (self.self_consumption_buffer_wh - trade.offer.energy * 1000) > 0:
                    self.self_consumption_buffer_wh -= trade.offer.energy * 1000
                    self.total_self_consumption_wh += trade.offer.energy * 1000
                else:
                    self.total_self_consumption_wh += self.self_consumption_buffer_wh
                    self.self_consumption_buffer_wh = 0
            # self_consumption_buffer needs to be exhausted if sold to any external agent
            elif trade.buyer_origin not in [*self.ess_list, *self.consumer_list] and \
                    trade.buyer_origin == trade.buyer and \
                    self.self_consumption_buffer_wh > 0:
                if (self.self_consumption_buffer_wh - trade.offer.energy * 1000) > 0:
                    self.self_consumption_buffer_wh -= trade.offer.energy * 1000
                else:
                    self.self_consumption_buffer_wh = 0

    def _accumulate_infinite_consumption(self, trade):
        """
        If the InfiniteBus is a seller of the trade when below the referenced area and bought
        by any of child devices.
        * total_self_consumption_wh needs to accumulated.
        * total_energy_produced_wh also needs to accumulated accounting of what
        the InfiniteBus has produced.
        """
        if trade.seller_origin in self.buffer_list and \
                trade.buyer_origin in self.consumer_list and \
                trade.buyer_origin == trade.buyer:
            self.total_self_consumption_wh += trade.offer.energy * 1000
            self.total_energy_produced_wh += trade.offer.energy * 1000

    def _dissipate_infinite_consumption(self, trade):
        """
        If the InfiniteBus is a buyer of the trade when below the referenced area
        and sold by any of child devices.
        total_self_consumption_wh needs to accumulated.
        demanded_buffer_wh also needs to accumulated accounting of what
        the InfiniteBus has consumed/demanded.
        """
        if trade.buyer_origin in self.buffer_list and trade.seller_origin in self.producer_list:
            self.total_self_consumption_wh += trade.offer.energy * 1000
            self.demanded_buffer_wh += trade.offer.energy * 1000

    def _accumulate_energy_trace(self):
        for c_area in self.areas_to_trace_list:
            if c_area not in self.accounted_markets:
                self.accounted_markets[c_area] = []
            for market in c_area.past_markets:
                if market.time_slot_str in self.accounted_markets[c_area]:
                    continue
                self.accounted_markets[c_area].append(market.time_slot_str)
                for trade in market.trades:
                    self._accumulate_self_consumption(trade)
                    self._accumulate_self_production(trade)
                    self._accumulate_self_consumption_buffer(trade)
                    self._dissipate_self_consumption_buffer(trade)
                    self._accumulate_infinite_consumption(trade)
                    self._dissipate_infinite_consumption(trade)

    def update_area_kpi(self, area):
        self.total_energy_demanded_wh = 0
        self._accumulate_total_energy_demanded(area)
        self._accumulate_energy_trace()


class KPI:
    def __init__(self):
        self.performance_indices = dict()
        self.performance_indices_redis = dict()
        self.state = {}

    def __repr__(self):
        return f"KPI: {self.performance_indices}"

    def area_performance_indices(self, area):
        if area.name not in self.state:
            self.state[area.name] = KPIState()
        self.state[area.name].accumulate_devices(area)

        self.state[area.name].update_area_kpi(area)
        self.state[area.name].total_demand = \
            self.state[area.name].total_energy_demanded_wh + \
            self.state[area.name].demanded_buffer_wh

        # in case when the area doesn't have any load demand
        if self.state[area.name].total_demand <= 0:
            self_sufficiency = None
        elif self.state[area.name].total_self_consumption_wh >= \
                self.state[area.name].total_demand:
            self_sufficiency = 1.0
        else:
            self_sufficiency = self.state[area.name].total_self_consumption_wh / \
                               self.state[area.name].total_demand

        if self.state[area.name].total_energy_produced_wh <= 0:
            self_consumption = None
        elif self.state[area.name].total_self_consumption_wh >= \
                self.state[area.name].total_energy_produced_wh:
            self_consumption = 1.0
        else:
            self_consumption = self.state[area.name].total_self_consumption_wh / \
                               self.state[area.name].total_energy_produced_wh
        return {"self_sufficiency": self_sufficiency, "self_consumption": self_consumption,
                "total_energy_demanded_wh": self.state[area.name].total_demand,
                "total_energy_produced_wh": self.state[area.name].total_energy_produced_wh,
                "total_self_consumption_wh": self.state[area.name].total_self_consumption_wh}

    def _kpi_ratio_to_percentage(self, area_name):
        area_kpis = self.performance_indices[area_name]
        if area_kpis["self_sufficiency"] is not None:
            self_sufficiency_percentage = \
                area_kpis["self_sufficiency"] * 100
        else:
            self_sufficiency_percentage = 0.0
        if area_kpis["self_consumption"] is not None:
            self_consumption_percentage = \
                area_kpis["self_consumption"] * 100
        else:
            self_consumption_percentage = 0.0

        return {"self_sufficiency": self_sufficiency_percentage,
                "self_consumption": self_consumption_percentage,
                "total_energy_demanded_wh": area_kpis["total_energy_demanded_wh"],
                "total_energy_produced_wh": area_kpis["total_energy_produced_wh"],
                "total_self_consumption_wh": area_kpis["total_self_consumption_wh"]
                }

    def update_kpis_from_area(self, area):
        self.performance_indices[area.name] = \
            self.area_performance_indices(area)
        self.performance_indices_redis[area.uuid] = self._kpi_ratio_to_percentage(area.name)

        for child in area.children:
            if len(child.children) > 0:
                self.update_kpis_from_area(child)
