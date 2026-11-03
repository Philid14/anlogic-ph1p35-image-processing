"""Executable MAIN integration proposal, NOT synthesizable hardware.

Extends the existing contract vocabulary with bounded slot ownership, complete
frame disposition, immutable scan leases and first-display accounting. Times
are caller-supplied reference ticks. No clocks, CDC or pixel DDR are simulated.
"""
from dataclasses import dataclass, replace
from .integration_contract import Key, Bundle, ContractViolation, require_atomic


@dataclass(frozen=True)
class FrameRef:
    slot: int
    generation: int
    key: Key
    captured_at: int


@dataclass(frozen=True)
class FrameRecord:
    ref: FrameRef
    disposition: str = 'open'
    annotation: Bundle | None = None
    result_seen: bool = False
    displayed: bool = False


@dataclass(frozen=True)
class Scan:
    token: int
    ref: FrameRef
    selected_at: int
    first_pixel_at: int | None
    deadline: int | None
    annotation: Bundle | None
    reason: str
    first_display: bool | None
    latency: int | None
    image_age: int | None


class FrameTransactions:
    def __init__(self, *, slots, max_age, scan_bound):
        if min(slots, max_age, scan_bound) < 1:
            raise ContractViolation('explicit_positive_limits_required')
        self.capacity, self.max_age, self.scan_bound = slots, max_age, scan_bound
        self.records = {}
        self.generations = [-1] * slots
        self.session = None
        self.used_sessions = set()  # test authority, not a proposed RTL table
        self.high_water = -1
        self.clock = 0
        self.trusted = False
        self.active = None
        self.token = 0
        self.events = []
        self.first_count = self.repeat_count = 0

    def event(self, reason, ref=None):
        self.events.append((reason, ref))
        return reason

    def tick(self, now):
        if now < self.clock:
            self.trusted = False
            raise ContractViolation('clock_moved_backwards_requires_session')
        self.clock = now

    def start_session(self, session, now, *, old_io_drained=False):
        Key(session, 0)
        if session in self.used_sessions:
            raise ContractViolation('session_reuse')
        if not old_io_drained:
            # Changing a metadata epoch does not cancel real prefetched reads,
            # pending DDR writes, FIFO packets or the current scan lease.
            self.trusted = False
            return self.event('waiting_for_io_drain')
        self.used_sessions.add(session)
        self.session, self.clock, self.high_water = session, now, -1
        self.records.clear()
        self.active = None
        self.trusted = True
        self.token += 1  # old release/packet cannot affect a new lease
        return self.event('session_barrier')

    def begin(self, slot, generation, key, captured_at):
        self.tick(captured_at)
        if not self.trusted or key.session != self.session:
            return self.event('untrusted_session')
        if key.frame <= self.high_water:
            return self.event('duplicate_or_reordered_capture')
        self.high_water = key.frame  # a dropped capture is still retired
        if not 0 <= slot < self.capacity or generation <= self.generations[slot]:
            return self.event('bad_slot_or_generation')
        if self.active and self.active.ref.slot == slot:
            # MAIN must choose another slot/drop this capture; never stall pixels.
            return self.event('capture_dropped_reader_lease',FrameRef(slot,generation,key,captured_at))
        self.generations[slot] = generation
        ref = FrameRef(slot, generation, key, captured_at)
        self.records[slot] = FrameRecord(ref)
        self.event('capture_started', ref)
        return ref

    def record(self, ref):
        record = self.records.get(ref.slot)
        return record if record and record.ref == ref else None

    def finish(self, ref, *, complete, beats, expected_beats, errors=()):
        record = self.record(ref)
        if record is None:
            return self.event('retired_generation', ref)
        if record.disposition != 'open':
            return self.event('duplicate_disposition', ref)
        okay = complete and beats == expected_beats and not errors
        disposition = 'complete' if okay else 'cancelled'
        self.records[ref.slot] = replace(record, disposition=disposition,
            annotation=record.annotation if okay else None)
        return self.event(disposition, ref)

    def publish(self, ref, bundle, *, now):
        self.tick(now)
        record = self.record(ref)
        if not self.trusted or ref.key.session != self.session or record is None:
            return self.event('retired_generation', ref)
        if record.disposition == 'cancelled':
            return self.event('cancelled_result', ref)
        if record.result_seen:
            return self.event('duplicate_result', ref)
        # One terminal result attempt; a rejected bundle cannot be replayed fixed.
        record = replace(record, result_seen=True)
        self.records[ref.slot] = record
        try:
            require_atomic(ref.key, bundle)
        except ContractViolation:
            return self.event('mixed_observation', ref)
        if bundle.captured_at != ref.captured_at:
            return self.event('capture_time_mismatch', ref)
        if bundle.ready_at < ref.captured_at:
            return self.event('text_ready_before_capture', ref)
        self.records[ref.slot] = replace(record, annotation=bundle)
        return self.event('result_staged' if record.disposition == 'open' else 'result_cached', ref)

    def select(self, slot, *, now):
        self.tick(now)
        if self.active:
            raise ContractViolation('scan_already_active')
        record = self.records.get(slot)
        if record is None or record.disposition != 'complete':
            return self.event('pixel_frame_unavailable')
        bundle, reason = record.annotation, 'visible'
        if not self.trusted:
            bundle, reason = None, 'transport_or_time_untrusted'
        elif bundle is None:
            reason = 'result_missing'
        elif bundle.ready_at > now:
            bundle, reason = None, 'text_not_ready'
        elif now + self.scan_bound - record.ref.captured_at > self.max_age:
            bundle, reason = None, 'whole_scan_age_exceeded'
        self.token += 1
        self.active = Scan(self.token, record.ref, now, None, None,
            bundle, reason, None, None, None)
        return self.active

    def first_pixel(self, token, *, now):
        self.tick(now)
        if self.active is None or token != self.active.token:
            return self.event('retired_scan_token')
        if self.active.first_pixel_at is not None:
            return self.event('duplicate_hdmi_first_pixel')
        record = self.record(self.active.ref)
        if record is None or record.disposition != 'complete':
            raise ContractViolation('pixel_lease_violated')
        first = not record.displayed
        age = now-record.ref.captured_at
        bundle, reason = self.active.annotation, self.active.reason
        if not self.trusted:
            bundle, reason = None, 'transport_or_time_untrusted'
        elif bundle is not None and age+self.scan_bound>self.max_age:
            bundle, reason = None, 'whole_scan_age_exceeded'
        self.first_count += int(first and self.trusted)
        self.repeat_count += int(not first and self.trusted)
        self.records[record.ref.slot] = replace(record, displayed=True)
        self.active = replace(self.active, first_pixel_at=now,
            deadline=now+self.scan_bound, annotation=bundle, reason=reason,
            first_display=first, latency=age if first and self.trusted else None,
            image_age=age if self.trusted else None)
        return self.active

    def scan(self, now):
        self.tick(now)
        if self.active is None:
            raise ContractViolation('no_active_scan')
        if self.active.first_pixel_at is None:
            raise ContractViolation('hdmi_output_not_started')
        if not self.trusted:
            return None, 'transport_or_time_untrusted'
        if now > self.active.deadline:
            return None, 'scan_bound_overrun'
        record = self.record(self.active.ref)
        if record is None or record.disposition != 'complete':
            raise ContractViolation('pixel_lease_violated')
        return self.active.annotation, self.active.reason

    def end(self, token):
        if self.active is None or token != self.active.token:
            return self.event('retired_scan_token')
        started=self.active.first_pixel_at is not None
        self.active = None
        return self.event('scan_released' if started else 'selection_released_before_output')

    def invalidate_transport(self):
        # Metadata loss masks the whole annotation; video has no ready handshake.
        self.trusted = False
        return self.event('transport_loss_requires_session')
