"""Literal contract tests for the bounded frame/annotation ledger proposal.

No physical CDC/DDR/HDMI claim. Outputs must be new; expected values are fixed
per scenario rather than obtained from a second run of the ledger.
"""
import argparse
from dataclasses import replace
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import subprocess
from model.integration_contract import Key, Bundle, ContractViolation
from model.frame_transactions import FrameTransactions

HERE = Path(__file__).resolve().parent


def exercise():
    rows = []

    def check(name, inputs, expected, observed, invariant):
        rows.append(dict(name=name, input=inputs, expected=expected,
            observed=observed, invariant=invariant,
            failure_condition='observed differs from literal expected',
            passed=observed == expected))

    def fixture(max_age=200):
        ledger = FrameTransactions(slots=4, max_age=max_age, scan_bound=20)
        ledger.start_session(1, 0,old_io_drained=True)
        return ledger

    def capture(ledger, slot, fid, at, generation=1, finish=True):
        ref = ledger.begin(slot, generation, Key(1, fid), at)
        if finish:
            ledger.finish(ref, complete=True, beats=4, expected_beats=4)
        return ref

    def annotation(ref, ready=None, payload=('A',)):
        return Bundle(ref.key, ref.key, ref.key, ref.captured_at,
            ref.captured_at if ready is None else ready, payload)

    def display(ledger,slot,*,now):
        scan=ledger.select(slot,now=now)
        return ledger.first_pixel(scan.token,now=now) if not isinstance(scan,str) else scan

    def contents(ledger, at):
        bundle, reason = ledger.scan(at)
        return [reason, list(bundle.payload) if bundle else None]

    def raises(call):
        try:
            call()
        except ContractViolation as exc:
            return str(exc)
        return 'NOT_REJECTED'

    g=fixture();a=capture(g,0,1,1)
    check('duplicate_reorder_and_wrap', {'frames':[1,1,0,4294967295,0]},
        ['duplicate_or_reordered_capture','duplicate_or_reordered_capture',4294967295,'duplicate_or_reordered_capture'],
        [g.begin(1,1,Key(1,1),2),g.begin(1,1,Key(1,0),3),
         g.begin(1,1,Key(1,4294967295),4).key.frame,g.begin(2,1,Key(1,0),5)],
        'Each session frame identity is unique and increasing; no in-session wrap')

    g=fixture();a=capture(g,0,1,1);g.publish(a,annotation(a),now=2)
    s=display(g,0,now=10);before=contents(g,11)
    dropped=g.begin(0,2,Key(1,2),12)
    check('reader_lease_prevents_pixel_overwrite', {'active':[0,1,1],'write':[0,2,2]},
        [['visible',['A']],'capture_dropped_reader_lease',['visible',['A']],1],
        [before,dropped,contents(g,13),g.records[0].ref.generation],
        'In-flight pixels retain the exact selected generation; incoming video is never stalled')
    g.end(s.token);b=capture(g,0,3,14,generation=2)
    check('reuse_after_release_retires_old_result', {'old_key':[1,1],'new_key':[1,3]},
        ['retired_generation','result_missing'],
        [g.publish(a,annotation(a),now=15),display(g,0,now=16).reason],
        'A stale result cannot attach to a reused slot, even after reader release')

    g=fixture();a=capture(g,0,1,1,finish=False)
    staged=g.publish(a,annotation(a),now=2);not_yet=display(g,0,now=3)
    committed=g.finish(a,complete=True,beats=4,expected_beats=4)
    check('result_before_ddr_commit_is_staged', {'result_at':2,'commit_after':3},
        ['result_staged','pixel_frame_unavailable','complete','visible'],
        [staged,not_yet,committed,display(g,0,now=4).reason],
        'Detection completion does not imply DDR pixel completion')

    for name,complete,beats,errors in [('early_sof_cancel',False,2,('early_sof',)),
        ('wrong_eol_cancel',True,4,('wrong_eol',)),('missing_eof_cancel',False,4,()),
        ('partial_tail_cancel',True,4,('source_lanes=2',)),('last_beat_abort',True,4,('abort',))]:
        g=fixture();a=capture(g,0,1,1,finish=False)
        g.publish(a,annotation(a),now=2)
        check(name,dict(complete=complete,beats=beats,errors=errors),
            ['cancelled','pixel_frame_unavailable','cancelled_result'],
            [g.finish(a,complete=complete,beats=beats,expected_beats=4,errors=errors),
             display(g,0,now=3),g.publish(a,annotation(a),now=4)],
            'Cancelled or malformed frames never become a valid absence or displayable annotation')

    g=fixture();a=capture(g,0,1,1);s=display(g,0,now=10)
    p=g.publish(a,annotation(a,ready=15),now=11)
    stable=contents(g,16);g.end(s.token);again=display(g,0,now=17)
    check('late_result_waits_for_next_display_boundary', {'select':10,'result':11,'ready':15,'repeat':17},
        ['result_cached',['result_missing',None],'visible',False,None,16,1,1],
        [p,stable,again.reason,again.first_display,again.latency,again.image_age,g.first_count,g.repeat_count],
        'Late results never alter an active frame; repeated display is age, not another latency sample')

    g=fixture();a=capture(g,0,1,1);g.publish(a,annotation(a,ready=20),now=2)
    s=display(g,0,now=10);first=s.reason;still=contents(g,21);g.end(s.token)
    check('text_completion_is_not_mid_frame_commit', {'text_ready':20,'display_start':10},
        ['text_not_ready',['text_not_ready',None],'visible'],
        [first,still,display(g,0,now=22).reason],
        'Box and text commit together; completing text mid-scan cannot reveal only half a bundle')

    g=fixture();a=capture(g,0,1,1);g.publish(a,annotation(a),now=2);s=display(g,0,now=10)
    b=capture(g,1,2,11);g.publish(b,annotation(b,payload=('B',)),now=12)
    check('newer_observation_cannot_change_active_frame', {'active':'A','new_result':'B'},
        [['visible',['A']], 'duplicate_result', ['visible',['A']]],
        [contents(g,13),g.publish(a,annotation(a,payload=('corrupt',)),now=14),contents(g,15)],
        'Published data and the scan snapshot are immutable even when newer observations arrive')

    for field in ('box_key','text_key','key'):
        g=fixture();a=capture(g,0,1,1);bad=replace(annotation(a),**{field:Key(1,2)})
        check('mixed_'+field, {'pixel':[1,1],field:[1,2]},
            ['mixed_observation','result_missing'],
            [g.publish(a,bad,now=2),display(g,0,now=3).reason],
            'Pixel, box and text must carry exactly the same observation identity')

    g=fixture();a=capture(g,0,1,1)
    check('cannot_refresh_old_capture_timestamp', {'capture_tick':1,'forged_tick':2},
        'capture_time_mismatch',g.publish(a,replace(annotation(a),captured_at=2),now=3),
        'Result arrival and text preparation must not make the underlying image younger')
    g=fixture();a=capture(g,0,1,1)
    check('text_cannot_be_ready_before_capture', {'capture':1,'text_ready':0},
        'text_ready_before_capture',g.publish(a,annotation(a,ready=0),now=2),
        'Text preparation cannot precede the image observation it describes')

    for at,expected in [(181,'visible'),(182,'whole_scan_age_exceeded')]:
        g=fixture();a=capture(g,0,1,1);g.publish(a,annotation(a),now=2)
        check('whole_scan_age_'+str(at), {'capture':1,'start':at,'scan_bound':20,'age_limit':200},
            expected,display(g,0,now=at).reason,
            'The whole permitted scan, not merely its first pixel, must fit the age budget')

    g=fixture();a=capture(g,0,1,1);g.publish(a,annotation(a),now=2);display(g,0,now=10)
    check('scan_overrun_masks_annotation', {'start':10,'bound':20,'query':31},
        [None,'scan_bound_overrun'],list(g.scan(31)),
        'An exceeded scan-duration contract cannot keep an annotation valid')

    g=fixture();a=capture(g,0,1,1);g.publish(a,annotation(a),now=2);old=display(g,0,now=10)
    g.start_session(2,11,old_io_drained=True);b=g.begin(0,2,Key(2,0),12);g.finish(b,complete=True,beats=4,expected_beats=4)
    new=display(g,0,now=13)
    check('restart_rejects_inflight_packet_and_old_release', {'old_sid':1,'new_sid':2},
        ['retired_generation','retired_scan_token',2,4],
        [g.publish(a,annotation(a),now=14),g.end(old.token),g.active.ref.key.session,g.active.token],
        'A prior epoch packet or release cannot revalidate or unlock a new scan')
    check('session_reuse_is_rejected', {'reuse_sid':1},'session_reuse',
        raises(lambda:g.start_session(1,15,old_io_drained=True)),'Session tokens cannot alias surviving old observations')

    g=fixture();a=capture(g,0,1,1);g.publish(a,annotation(a),now=2);old=display(g,0,now=10)
    blocked=g.start_session(2,11)
    check('session_request_does_not_release_real_reader', {'old_reader':'active','io_drained':False},
        ['waiting_for_io_drain',[None,'transport_or_time_untrusted'],'untrusted_session',1],
        [blocked,list(g.scan(12)),g.begin(0,2,Key(2,0),13),g.active.ref.key.session],
        'A session request masks metadata but cannot make old DDR/scan transactions disappear')
    g.end(old.token);recovered=g.start_session(2,14,old_io_drained=True)
    check('verified_drain_allows_new_session', {'old_reader_released':True,'io_drained':True},
        ['session_barrier',2,True],[recovered,g.session,g.trusted],
        'Only a trusted completed I/O drain barrier permits slot/epoch reuse')

    g=fixture();a=capture(g,0,1,1);g.publish(a,annotation(a),now=2);display(g,0,now=10)
    g.invalidate_transport()
    check('cdc_loss_masks_all_annotation', {'fault':'event_loss'},
        [None,'transport_or_time_untrusted'],list(g.scan(11)),
        'A loss/reset barrier removes all annotation eligibility without a video ready signal')
    g.end(g.active.token);untrusted=display(g,0,now=12)
    check('metadata_loss_cannot_emit_valid_latency', {'fault':'event_loss','repeat_at':12},
        [None,None,1,0],
        [untrusted.latency,untrusted.image_age,g.first_count,g.repeat_count],
        'Untrusted metadata cannot increase reliable statistics or emit a valid age')
    check('clock_rollback_requires_new_session', {'now':[12,3]},
        'clock_moved_backwards_requires_session',raises(lambda:g.tick(3)),
        'A wrapping/invalid clock cannot make stale observations appear fresh')
    g.start_session(2,0,old_io_drained=True)
    check('new_session_can_rebase_time', {'new_sid':2,'now':0},[True,0],[g.trusted,g.clock],
        'Time recovery requires an explicit new session and cancels previous associations')

    g=fixture();a=capture(g,0,1,1);b=capture(g,1,2,2);c=capture(g,2,3,3)
    g.publish(c,annotation(c),now=4);s=display(g,2,now=13);g.end(s.token)
    again=display(g,2,now=15)
    check('skip_ab_display_c_only', {'capture_ticks':[1,2,3],'display_c':[13,15]},
        [10,False,None,12,1,1],
        [s.latency,again.first_display,again.latency,again.image_age,g.first_count,g.repeat_count],
        'Skipping A/B must not turn C latency into the age of the first queued capture')

    g=fixture();a=capture(g,0,1,1);g.publish(a,annotation(a),now=2)
    armed=g.select(0,now=3)
    before=[g.first_count,armed.latency,raises(lambda:g.scan(4))]
    started=g.first_pixel(armed.token,now=10)
    check('selection_is_not_actual_hdmi_output', {'selected':3,'first_pixel':10,'capture':1},
        [[0,None,'hdmi_output_not_started'],9,1],
        [before,started.latency,g.first_count],
        'Read selection/prefetch cannot be counted or timestamped as actual HDMI first pixel')
    duplicate=g.first_pixel(armed.token,now=11)
    check('duplicate_hdmi_event_is_not_new_display', {'first_pixel_events':[10,11]},
        ['duplicate_hdmi_first_pixel',1,0],[duplicate,g.first_count,g.repeat_count],
        'A duplicate first-pixel pulse cannot become a repeat refresh or another latency sample')

    g=fixture();a=capture(g,0,1,1);g.publish(a,annotation(a),now=2)
    armed=g.select(0,now=3);released=g.end(armed.token);started=display(g,0,now=10)
    check('cancelled_prefetch_never_counts_display', {'select_cancel':3,'actual_first':10},
        ['selection_released_before_output',True,9,1,0],
        [released,started.first_display,started.latency,g.first_count,g.repeat_count],
        'Cancelling prefetch must not consume the frame first-display qualification')

    g=fixture();a=capture(g,0,1,1);g.publish(a,annotation(a),now=2)
    armed=g.select(0,now=170);started=g.first_pixel(armed.token,now=182)
    check('age_rechecked_at_actual_hdmi_start', {'select':170,'first_pixel':182,'bound':20,'capture':1,'limit':200},
        ['visible','whole_scan_age_exceeded',181],
        [armed.reason,started.reason,started.latency],
        'A prefetch delay can exhaust the annotation age budget before actual output starts')

    return rows


def main():
    ap=argparse.ArgumentParser();ap.add_argument('--out',type=Path,required=True)
    args=ap.parse_args();args.out.mkdir(parents=True,exist_ok=False)
    sources=[Path(__file__),HERE/'model/frame_transactions.py',HERE/'model/integration_contract.py']
    hashes=lambda:{str(p.relative_to(HERE)):hashlib.sha256(p.read_bytes().replace(b'\r\n',b'\n')).hexdigest() for p in sources}
    before=hashes();rows=exercise();unchanged=before==hashes()
    report=dict(schema=1,created_utc=datetime.now(timezone.utc).isoformat(),
        scope='MODEL PROPOSAL; no physical CDC/DDR/HDMI, RTL implementation or board claim',
        source_sha256_lf=before,source_unchanged=unchanged,fixtures=dict(slots=4,max_age=200,scan_bound=20),
        head=subprocess.check_output(['git','rev-parse','HEAD'],cwd=HERE,text=True).strip(),
        cases=rows,passed=unchanged and all(x['passed'] for x in rows),integration_ready=False)
    (args.out/'summary.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    for x in rows:print(('PASS ' if x['passed'] else 'FAIL ')+x['name'])
    print(f"FRAME_TRANSACTIONS_COMPLETE cases={len(rows)} failed={sum(not r['passed'] for r in rows)}")
    return 0 if report['passed'] else 1


if __name__=='__main__':raise SystemExit(main())
