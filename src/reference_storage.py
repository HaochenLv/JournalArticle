"""Optional storage-only instrumentation for pinned HELIX (no scheduling changes).

Upstream event archives are read only for duplicate-ID membership; log archives
are not read by the active fixed-pipeline simulator path. Retain duplicate-ID
checks while discarding unused event objects and textual logs. Query/request
histories used for metrics are retained intact. See validation.json before use.
"""
from contextlib import contextmanager
from research import ref

class DiscardAppend:
 def append(self,value):pass
class EventIDs(dict):
 def __setitem__(self,key,value):super().__setitem__(key,None)

def minimize_archives(sim):
 sim.previous_events_list=DiscardAppend()
 sim.previous_events_dict=EventIDs.fromkeys(sim.previous_events_dict)
 def add_log(log_time,entity_name,activity,description,is_empty=False):
  assert log_time>=sim.logger.last_log_time
 sim.logger.add_log=add_log
 sim.logger.log_history.clear();sim.logger.entity_log_history.clear()
 return sim

@contextmanager
def compact_reference_storage():
 original=ref._build_helix_simulator
 def build(**kwargs):
  sim,mini,mapping=original(**kwargs);minimize_archives(sim);return sim,mini,mapping
 ref._build_helix_simulator=build
 try:yield
 finally:ref._build_helix_simulator=original
