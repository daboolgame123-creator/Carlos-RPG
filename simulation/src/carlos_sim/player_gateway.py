"""01-W: trusted offline gateway for one human-controlled player character.

This is NOT an HTTP authentication boundary. Only a trusted local process
may construct the object and hold a SQLiteEventStore capability.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .domain import DomainEvent, _thaw
from .player_perception import recall_player_events
from .player_activity_scene import visible_player_activities
from .living_world import LivingWorldEngine
from .movement import player_travel_signal, _in_transit
from .social import NPCSocialService, KINDS
from .store import SQLiteEventStore, RevisionConflict, DuplicateCommand
from .time_engine import TimeEngine


@dataclass(frozen=True)
class PlayerCommandResult:
    """No WorldState or hidden NPC information crosses the player boundary."""
    world_id: str
    time: int
    revision: int
    status: str
    details: dict[str, Any]


class PlayerGateway:
    """Trusted local commands. Player actions are NEVER chosen by NPC policy."""

    def __init__(self, store: SQLiteEventStore, clock: TimeEngine, *,
                 world_id: str, player_id: str,
                 engine: LivingWorldEngine | None = None):
        if clock.store is not store:
            raise ValueError('player gateway and clock must share the same store')
        if (not isinstance(world_id, str) or not world_id
                or not isinstance(player_id, str) or not 0 < len(player_id) <= 80):
            raise ValueError('world and player IDs are required')
        if engine is not None and (engine.store is not store or engine.clock is not clock):
            raise ValueError('injected world engine must share store and clock')
        self.store, self.clock = store, clock
        self.world_id, self.player_id = world_id, player_id
        self.engine = engine if engine is not None else LivingWorldEngine(store, clock)

    def _state(self, expected_revision: int | None = None):
        self.clock._require_session(self.world_id)
        state = self.store.load(self.world_id)
        character = state.entities.get(self.player_id)
        if character is None or character['controller'] != 'player':
            raise PermissionError('gateway must be bound to a player-controlled entity')
        if expected_revision is not None and (
                type(expected_revision) is not int or expected_revision != state.revision):
            raise RevisionConflict('stale player command revision')
        return state

    @staticmethod
    def _command_id(command_id: str) -> str:
        if (not isinstance(command_id, str) or not 1 <= len(command_id) <= 64
                or not command_id[0].isascii()
                or not command_id[0].isalnum()
                or not all(ch.isascii() and (ch.isalnum() or ch in '._-')
                           for ch in command_id)):
            raise ValueError('command ID must be 1..64 ASCII letters/digits/._-')
        return command_id

    def inspect(self) -> PlayerCommandResult:
        """Reveal co-located presence and adjacent roads only, no remote truth."""
        state = self._state()
        transit = player_travel_signal(state, self.player_id)
        if transit is not None:
            _, schedule, trip = transit
            return PlayerCommandResult(state.world_id, state.time, state.revision,
                                       'traveling', {
                'route_id': trip['route_id'],
                'remaining_seconds': schedule['due'] - state.time,
            })
        place = state.entities[self.player_id]['location_id']
        # Use one detached state projection to check presence; do not
        # materialize the entire world repeatedly for each visible entity.
        projected = state.to_dict()
        present = tuple(
            {'id': ident, 'name': data['name']}
            for ident, data in sorted(state.entities.items())
            if data['location_id'] == place
            and not _in_transit(projected, ident)
        )
        exits = tuple(
            {'route_id': rid, 'destination': r['b'] if r['a'] == place else r['a'],
             'seconds': r['seconds']}
            for rid, r in sorted(state.routes.items())
            if place in (r['a'], r['b'])
        )
        return PlayerCommandResult(state.world_id, state.time, state.revision,
                                   'present', {
            'location_id': place, 'location_name': state.locations[place]['name'],
            'occupants': present, 'exits': exits,
            # Present-only, qualitative behavior: never NPC intentions or
            # hidden medical facts. This is not a persistent player sighting.
            'activities': visible_player_activities(state, self.player_id),
        })

    def observe(self, *, command_id: str,
                expected_revision: int) -> PlayerCommandResult:
        """Record explicitly chosen local sight; inspect stays read-only."""
        cid = self._command_id(command_id)
        state = self._state(expected_revision)
        if player_travel_signal(state, self.player_id) is not None:
            raise ValueError('cannot observe while travelling')
        from .movement import _visible
        location = state.entities[self.player_id]['location_id']
        occupants = _visible(state.to_dict(), location)
        event = DomainEvent('PlayerObserved', self.player_id,
                            'player deliberately looked around locally',
                            state.time, {
            'location_id': location, 'occupants': occupants,
        })
        self.store.append(self.world_id, 'player-observe:' + cid,
                          expected_revision, [event], movement_authorized=True)
        return self.inspect()

    def recall(self) -> PlayerCommandResult:
        """Only player's verified past sightings and addressed unverified speech."""
        state = self._state()
        memories = recall_player_events(self.store, state, self.player_id)
        return PlayerCommandResult(state.world_id, state.time, state.revision,
                                   'memory', memories)

    def status(self) -> PlayerCommandResult:
        """The player's own opt-in RPG record, never another entity's state."""
        state = self._state()
        profile = state.rpg_profiles.get(self.player_id)
        if profile is None:
            return PlayerCommandResult(state.world_id, state.time, state.revision,
                                       'rpg_uninitialized', {'configured': False})
        # Thaw a detached safe record; do not send the WorldState to a client.
        return PlayerCommandResult(state.world_id, state.time, state.revision,
                                   'rpg_status', {'configured': True,
                                                  'profile': _thaw(profile)})

    def supplies(self) -> PlayerCommandResult:
        """Show only initialized, entity-owned goods/money of this player.

        The resource ledger is NOT the unimplemented RPG equipment/inventory
        system. Missing owned quantities are unknown, not fabricated zero.
        """
        state = self._state()
        own = state.resources.get(self.player_id, {})
        return PlayerCommandResult(state.world_id, state.time, state.revision,
                                   'supplies', {
            'balances': {name: qty for name, qty in sorted(own.items())
                         if type(qty) is int and qty >= 0},
        })

    def purchases(self, limit: int = 20) -> PlayerCommandResult:
        """Return a bounded history of this player's own executed purchases.

        Completed receipts remain known after leaving a market; present-only
        offers do not. This is deliberately not the NPC trade ledger: private
        balances, other buyers and individual resource before/after values
        must never cross the player boundary.
        """
        if type(limit) is not int or not 1 <= limit <= 20:
            raise ValueError('purchase history limit must be an integer from 1 to 20')
        state = self._state()
        own = [(trade['executed_at'], ident, trade)
               for ident, trade in state.market_trades.items()
               if trade['buyer_id'] == self.player_id]
        # Use only persistent fields; equal-tick tie-breaking by ID is stable
        # after JSON snapshots and replay, not a claim of intra-tick order.
        own.sort(key=lambda item: (item[0], item[1]), reverse=True)
        recent = tuple({
            'trade_id': ident, 'offer_id': trade['offer_id'],
            'seller_id': trade['seller_id'], 'site_id': trade['site_id'],
            'resource': trade['resource'], 'quantity': trade['quantity'],
            'unit_price': trade['unit_price'],
            'payment_resource': trade['payment_resource'],
            'total_paid': trade['total_paid'],
            'executed_at': tick,
        } for tick, ident, trade in own[:limit])
        return PlayerCommandResult(state.world_id, state.time, state.revision,
                                   'purchases', {'total': len(own),
                                                 'recent': recent})

    def offers(self) -> PlayerCommandResult:
        """Show only physically actionable, posted, local public quotes."""
        state = self._state()
        from .market import _balance, _present
        from .movement import _in_transit
        quotes = []
        if player_travel_signal(state, self.player_id) is None:
            site = state.entities[self.player_id]['location_id']
            raw = state.to_dict()
            for ident, o in sorted(state.market_offers.items()):
                if (o['site_id'] != site or o['status'] != 'open'
                        or not _present(raw, o['seller_id'], site)):
                    continue
                stock = state.resources.get(o['stock_owner_id'], {}).get(o['resource'])
                available = min(o['remaining'], stock) if _balance(stock) else 0
                if available > 0:
                    quotes.append({
                        'offer_id': ident, 'seller_id': o['seller_id'],
                        'resource': o['resource'], 'available': available,
                        'payment_resource': o['payment_resource'],
                        'unit_price': o['unit_price'],
                    })
        return PlayerCommandResult(state.world_id, state.time, state.revision,
                                   'offers', {'offers': tuple(quotes)})

    def buy(self, offer_id: str, quantity: int, expected_unit_price: int, *,
            command_id: str, expected_revision: int) -> PlayerCommandResult:
        """Player-authorized, local, finite transfer from one posted NPC offer.

        Require a genuine human-bound command and exact observed quote terms.
        The event reducer enforces stock, coins, seller presence and conservation.
        """
        cid = self._command_id(command_id)
        state = self._state(expected_revision)
        if player_travel_signal(state, self.player_id) is not None:
            raise ValueError('cannot purchase while travelling')
        from .market import MAX_QUANTITY, MAX_PRICE, _id
        from hashlib import sha256
        if (not _id(offer_id) or type(quantity) is not int
                or not 1 <= quantity <= MAX_QUANTITY
                or type(expected_unit_price) is not int
                or not 1 <= expected_unit_price <= MAX_PRICE):
            raise ValueError('valid offer, positive quantity and exact unit price required')
        trade_id = 'player-' + sha256(
            (self.player_id + ':' + cid).encode('utf-8')
        ).hexdigest()[:40]
        committed = self.store.append(
            self.world_id, 'player-buy:' + cid, expected_revision,
            [DomainEvent(
                'MarketTradeExecuted', self.player_id,
                'human player accepted a known local posted market offer',
                state.time, {'id': trade_id, 'buyer_id': self.player_id,
                             'offer_id': offer_id, 'quantity': quantity,
                             'expected_unit_price': expected_unit_price},
            )], market_authorized=True)
        receipt = committed.market_trades[trade_id]
        return PlayerCommandResult(committed.world_id, committed.time,
                                   committed.revision, 'purchased', {
            'trade_id': trade_id,
            'offer_id': offer_id,
            'resource': receipt['resource'],
            'quantity': receipt['quantity'],
            'payment_resource': receipt['payment_resource'],
            'total_paid': receipt['total_paid'],
        })

    def move(self, route_id: str, *, command_id: str,
             expected_revision: int) -> PlayerCommandResult:
        """Start an adjacent journey; arrival occurs only when its due event fires."""
        cid = self._command_id(command_id)
        state = self._state(expected_revision)
        if player_travel_signal(state, self.player_id) is not None:
            raise ValueError('player already travelling')
        if not isinstance(route_id, str) or route_id not in state.routes:
            raise ValueError('route is not known at current location')
        route = state.routes[route_id]
        here = state.entities[self.player_id]['location_id']
        if here not in (route['a'], route['b']):
            raise ValueError('player cannot move along a nonadjacent route')
        there = route['b'] if route['a'] == here else route['a']
        trip_id = 'player-travel:' + self.player_id + ':' + cid
        due = state.time + route['seconds']
        event = DomainEvent('ScheduledEventCreated', None,
                            'human player chose an adjacent journey',
                            state.time, {
            'id': trip_id, 'due': due, 'order': state.next_schedule_order,
            'kind': 'signal', 'interrupt': False,
            'payload': {'__player_travel': {
                'player_id': self.player_id, 'route_id': route_id,
                'origin': here, 'destination': there,
                'started_at': state.time,
            }},
        })
        # Local-only trusted capability; never expose store.append to clients.
        committed = self.store.append(
            self.world_id, 'player-move:' + cid, expected_revision,
            [event], movement_authorized=True)
        return PlayerCommandResult(committed.world_id, committed.time,
                                   committed.revision, 'traveling',
                                   {'route_id': route_id, 'remaining_seconds': route['seconds']})

    def wait(self, seconds: int, *, command_id: str,
             expected_revision: int) -> PlayerCommandResult:
        """Advance NPC events and scheduled player arrival without an auto-player AI."""
        cid = self._command_id(command_id)
        self._state(expected_revision)
        if type(seconds) is not int or seconds <= 0:
            raise ValueError('wait seconds must be a positive integer')
        result = self.engine.advance(
            self.world_id, seconds=seconds, command_id='player-wait:' + cid,
            expected_revision=expected_revision)
        now = result.state
        transit = player_travel_signal(now, self.player_id)
        return PlayerCommandResult(now.world_id, now.time, now.revision,
                                   'traveling' if transit is not None else 'ready', {
            'elapsed': result.elapsed_seconds, 'remaining': result.remaining_seconds,
            'interrupted': result.interrupted,
        })

    def interact(self, recipient_id: str, *, kind: str, text: str,
                 command_id: str, expected_revision: int) -> PlayerCommandResult:
        """Deliver only an explicit player speech act; NPC chooses its reaction."""
        cid = self._command_id(command_id)
        state = self._state(expected_revision)
        if player_travel_signal(state, self.player_id) is not None:
            raise ValueError('cannot interact while travelling')
        if (not isinstance(recipient_id, str)
                or recipient_id not in state.npcs or recipient_id == self.player_id):
            raise ValueError('recipient must be an existing NPC')
        if kind not in KINDS or not isinstance(text, str) or not 1 <= len(text) <= 500:
            raise ValueError('invalid social kind or message')
        response = NPCSocialService(self.store, self.clock).interact(
            self.world_id, self.player_id, recipient_id,
            kind=kind, text=text, message_id='player-' + cid,
            expected_revision=expected_revision)
        return PlayerCommandResult(response.state.world_id, response.state.time,
                                   response.state.revision, 'interacted', {
            'recipient_id': recipient_id, 'kind': kind,
            'reaction': response.reaction,
        })
