"""Run a reproducible five-person demo with zero network/API dependencies."""
import json
from pathlib import Path
from tempfile import TemporaryDirectory

from carlos_sim import DomainEvent, NPCService, SQLiteEventStore, TimeEngine


def run() -> list[tuple[str, str, int]]:
    fixture = json.loads(Path(__file__).with_name('characters.json').read_text(encoding='utf-8'))
    with TemporaryDirectory() as directory, SQLiteEventStore(Path(directory) / 'demo.sqlite') as db:
        db.create_world('five-npc-demo')
        events = [DomainEvent('LocationCreated', None, 'demo setup', 0, fixture['location'])]
        for npc in fixture['npcs']:
            events.append(DomainEvent('EntityCreated', None, 'demo setup', 0,
                                      {'id':npc['id'], 'name':npc['name'], 'controller':'npc', 'location_id':'village'}))
            events.append(DomainEvent('NPCConfigured', None, 'demo setup', 0,
                                      {k:npc[k] for k in ('role','needs','goals')} | {'npc_id':npc['id']}))
        db.append('five-npc-demo', 'seed', 0, events, bootstrap=True)
        clock = TimeEngine(db)
        clock.open_session('five-npc-demo')
        service = NPCService(db, clock)
        decisions = []
        for npc in fixture['npcs']:
            state = db.load('five-npc-demo')
            result = service.decide('five-npc-demo', npc['id'], command_id=f"choose:{npc['id']}", expected_revision=state.revision)
            decisions.append((npc['id'], result.action, result.score))
        assert db.verify('five-npc-demo').to_dict() == db.load('five-npc-demo').to_dict()
        return decisions


if __name__ == '__main__':
    for npc_id, action, score in run():
        print(f'{npc_id}: {action} (utility={score})')
