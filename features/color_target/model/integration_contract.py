"""Executable integration PROPOSAL, not production RTL or a CDC simulator.

All time/queue/confirmation limits must be supplied by the caller. Test values
are fixtures, not camera settings. Strict same-frame display is a proposal.
"""
from dataclasses import dataclass


class ContractViolation(ValueError):
    pass


@dataclass(frozen=True, order=True)
class Key:
    session: int
    frame: int

    def __post_init__(self):
        if not (0 <= self.session < 2**32 and 0 <= self.frame < 2**32):
            raise ContractViolation('identity_not_uint32')


class ObservationAdmission:
    def __init__(self, *, age_limit, acquire, lose):
        if min(age_limit, acquire, lose) <= 0:
            raise ContractViolation('explicit_positive_limits_required')
        self.age_limit, self.acquire, self.lose = age_limit, acquire, lose
        self.sessions = set()
        self.session = None
        self.clock = 0
        self.last_frame = -1
        self.observations = self.streak = self.misses = 0
        self.last_positive = None
        self.last_valid = None
        self.confirmed = self.show = False

    def start_session(self, session, now):
        Key(session, 0)
        if session in self.sessions:
            raise ContractViolation('session_reuse_without_retirement')
        self.tick(now)
        self.sessions.add(session)
        self.session, self.last_frame = session, -1
        self.observations = self.streak = self.misses = 0
        self.last_positive = self.last_valid = None
        self.confirmed = self.show = False

    def tick(self, now):
        if now < self.clock:
            raise ContractViolation('clock_moved_backwards')
        self.clock = now
        if self.last_positive is not None and now-self.last_positive > self.age_limit:
            self.confirmed = self.show = False
            self.streak = 0

    def result(self, key, *, valid, present, captured_at, now):
        self.tick(now)
        if key.session != self.session:
            return 'wrong_session'
        if key.frame <= self.last_frame:
            return 'duplicate' if key.frame == self.last_frame else 'out_of_order'
        self.last_frame = key.frame  # One disposition per identity, including invalid.
        if captured_at > now:
            return 'future_time'
        if not valid:
            return 'invalid'  # Does not mean absence; never refreshes target age.
        if now-captured_at > self.age_limit:
            return 'stale_result'
        self.observations += 1
        self.last_valid = captured_at
        if present:
            self.streak += 1
            self.misses = 0
            self.last_positive = captured_at
            self.confirmed = self.confirmed or self.streak >= self.acquire
            self.show = self.confirmed
            return 'positive'
        self.streak = 0
        self.misses += 1
        if self.misses >= self.lose:
            self.confirmed = self.show = False
        return 'no_target'

    def snapshot(self, status):
        return [status, self.observations, self.streak, self.misses, self.show]


class RasterAdmission:
    """Pre-adapter validation: source_lanes is NOT an existing TARGET port."""
    def __init__(self, width, height):
        if width < 4 or width % 4 or height < 1:
            raise ContractViolation('unsupported_geometry')
        self.positions = [(x,y) for y in range(height) for x in range(0,width,4)]
        self.width = width
        self.reset()

    def reset(self):
        self.index = 0
        self.key = None
        self.bad = self.quarantine = False

    def beat(self, key, *, x, y, sof, eol, eof, source_lanes=4, abort=False):
        if self.quarantine:
            return 'needs_reset'
        if source_lanes != 4:
            self.quarantine = True
            return 'partial_tail_requires_abort'
        if sof and self.key is not None:
            self.quarantine = True
            return 'early_sof_requires_reset'
        if self.key is None:
            if not sof:
                self.quarantine = True
                return 'missing_sof'
            self.key = key
        at_x, at_y = self.positions[self.index]
        last = self.index == len(self.positions)-1
        self.bad |= key != self.key or (x,y) != (at_x,at_y) or eol != (at_x==self.width-4) or abort
        if eof != last:
            self.quarantine = True
            return 'missing_eof_requires_reset' if last else 'early_eof_requires_reset'
        self.index += 1
        if last:
            disposition = 'invalid_frame' if self.bad else 'complete_frame'
            self.index, self.key, self.bad = 0, None, False
            return disposition
        return 'beat'


class PendingResults:
    def __init__(self):
        self.open = set()
        self.due = {}

    def begin(self, key):
        self.open.add(key)

    def eof(self, key, at, latency):
        self.open.remove(key)
        self.due[key] = at+latency

    def deliver(self, at):
        ready = sorted(k for k,t in self.due.items() if t <= at)
        for key in ready:
            del self.due[key]
        return ready

    def reset(self):
        cancelled = sorted(self.open | self.due.keys())
        self.open.clear()
        self.due.clear()
        return cancelled


@dataclass(frozen=True)
class Bundle:
    key: Key
    box_key: Key
    text_key: Key
    captured_at: int
    ready_at: int
    payload: tuple = ()


def require_atomic(frame_key, bundle):
    if not (frame_key == bundle.key == bundle.box_key == bundle.text_key):
        raise ContractViolation('mixed_observation')


class DisplayAssociation:
    def __init__(self):
        self.slots = {}
        self.results = {}
        self.active = None

    def write(self, slot, generation, key, *, complete):
        old = self.slots.get(slot)
        if old and generation <= old[0]:
            raise ContractViolation('generation_not_increasing')
        # Reference table is bounded by live slots; old results are retired.
        if old:
            self.results.pop((old[1],old[0]),None)
        self.slots[slot] = generation,key,complete

    def result(self, slot, generation, bundle):
        if self.slots.get(slot) != (generation,bundle.key,True):
            return 'retired_or_incomplete'
        self.results[bundle.key,generation] = bundle
        return 'cached'

    def select(self, slot, *, now, age_limit, frame_duration_bound):
        generation,key,complete = self.slots[slot]
        bundle = self.results.get((key,generation)) if complete else None
        reason = 'visible'
        if bundle is None:
            reason = 'missing'
        elif bundle.ready_at > now:
            reason,bundle = 'late',None
        elif bundle.captured_at > now or now+frame_duration_bound-bundle.captured_at > age_limit:
            reason,bundle = 'age_budget',None
        else:
            try:
                require_atomic(key,bundle)
            except ContractViolation:
                reason,bundle = 'mixed_observation',None
        self.active = slot,generation,key,bundle,reason
        return reason

    def scan(self):
        slot,generation,key,bundle,reason = self.active
        if self.slots.get(slot) != (generation,key,True):
            raise ContractViolation('slot_overwritten_during_scan')
        return reason, bundle.payload if bundle else None


@dataclass(frozen=True)
class Packet:
    source_epoch: int
    destination_epoch: int
    bundle: Bundle


class AbstractPacketChannel:
    """Atomic queue/epoch contract only; no synchronizers or metastability."""
    def __init__(self, capacity):
        if capacity < 1:
            raise ContractViolation('capacity_required')
        self.capacity = capacity
        self.source_epoch = self.destination_epoch = 0
        self.queue = []
        self.dropped = []

    def send(self,bundle):
        if len(self.queue) == self.capacity:
            self.dropped.append(bundle.key)
            return 'overflow_reported'
        self.queue.append(Packet(self.source_epoch,self.destination_epoch,bundle))
        return 'queued'

    def receive(self,packet=None):
        packet = self.queue.pop(0) if packet is None else packet
        if (packet.source_epoch,packet.destination_epoch) != (self.source_epoch,self.destination_epoch):
            return None
        return packet.bundle

    def reset(self,side):
        if side == 'source':self.source_epoch += 1
        elif side == 'destination':self.destination_epoch += 1
        else:raise ContractViolation('unknown_reset_side')
        cancelled = [p.bundle.key for p in self.queue]
        self.queue.clear()
        return cancelled
